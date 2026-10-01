#!/usr/bin/env python3
"""Traceability gate: the requirement matrix stays complete, well formed and honest.

Structure rules (always enforced)
---------------------------------
* ``matrix-structure``  — every requirement row has the documented columns.
* ``matrix-ids``        — ids are ``R-NN``, unique, zero padded and sequential with no gaps.
* ``matrix-status``     — the status is one of ``planned``, ``in progress``, ``done``, ``blocked``;
                          a ``blocked`` row must state the reason in the same cell.
* ``matrix-phase``      — the phase column refers to phases 1–18, a range of them, or ``all``.

Release rules (``--release``)
-----------------------------
* ``matrix-open``  — no row may still be ``planned``, ``in progress`` or ``blocked``.
* ``matrix-test``  — every ``tests/...`` path quoted in the verification column must exist.

Usage::

    python tools/qa/check_traceability.py
    python tools/qa/check_traceability.py --release
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _common import REPO_ROOT, Gate, parse_args

MATRIX = REPO_ROOT / "docs" / "requirements-traceability.md"
ROW = re.compile(r"^\|\s*(?P<id>R-\d{2,3})\s*\|(?P<body>.*)\|\s*$")
STATUS = re.compile(
    r"^(?P<status>planned|in progress|done|blocked)\b(?P<reason>.*)$", re.IGNORECASE
)
PHASE_TOKEN = re.compile(r"^\d{1,2}(\s*[\u2013-]\s*\d{1,2})?$")
TEST_PATH = re.compile(r"`(tests/[^`]+)`")
FIRST_PHASE, LAST_PHASE = 1, 18


def _rows(text: str) -> list[tuple[str, list[str]]]:
    parsed: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            parsed.append(
                (match.group("id"), [cell.strip() for cell in match.group("body").split("|")])
            )
    return parsed


def _check_identity(
    gate: Gate, identifier: str, cells: list[str], seen: set[str], expected: int
) -> int:
    """Column count, duplicate ids and sequential numbering. Returns the next expected id."""
    if len(cells) != 6:
        gate.add(
            "matrix-structure",
            f"{identifier} has {len(cells)} columns, expected 6 (design, implementation, verification, phase, status)",
            MATRIX,
        )
        return expected
    if identifier in seen:
        gate.add("matrix-ids", f"{identifier} appears more than once", MATRIX)
    seen.add(identifier)
    number = int(identifier.split("-")[1])
    if number != expected:
        gate.add(
            "matrix-ids",
            f"expected R-{expected:02d}, found {identifier} (ids must be sequential)",
            MATRIX,
        )
        return number + 1
    return expected + 1


def _check_status(gate: Gate, identifier: str, status: str) -> None:
    match = STATUS.match(status)
    if not match:
        gate.add("matrix-status", f"{identifier} has unknown status {status!r}", MATRIX)
        return
    value = match.group("status").lower()
    if value == "blocked" and len(match.group("reason").strip(" -\u2013")) < 5:
        gate.add("matrix-status", f"{identifier} is blocked without a documented reason", MATRIX)
    elif gate.release and value != "done":
        gate.add("matrix-open", f"{identifier} is still '{value}' at release", MATRIX)


def _check_phase(gate: Gate, identifier: str, phase: str) -> None:
    if phase == "all":
        return
    for token in phase.split(","):
        if not PHASE_TOKEN.match(token.strip()):
            gate.add(
                "matrix-phase",
                f"{identifier} has phase {phase!r}, expected 1\u201318, a range, or 'all'",
                MATRIX,
            )
            return
        numbers = [int(part) for part in re.split(r"[\u2013-]", token.strip())]
        if any(number < FIRST_PHASE or number > LAST_PHASE for number in numbers):
            gate.add(
                "matrix-phase",
                f"{identifier} refers to a phase outside {FIRST_PHASE}\u2013{LAST_PHASE}",
                MATRIX,
            )
            return


def check_rows(gate: Gate, rows: list[tuple[str, list[str]]]) -> None:
    expected_id = 1
    seen: set[str] = set()
    for identifier, cells in rows:
        gate.checked += 1
        expected_id = _check_identity(gate, identifier, cells, seen, expected_id)
        if len(cells) != 6:
            continue
        design, implementation, verification, phase, status = (
            cells[1],
            cells[2],
            cells[3],
            cells[4],
            cells[5],
        )
        if not design or not implementation or not verification:
            gate.add(
                "matrix-structure",
                f"{identifier} has an empty design/implementation/verification cell",
                MATRIX,
            )
        _check_status(gate, identifier, status)
        _check_phase(gate, identifier, phase)
        if gate.release:
            for referenced in TEST_PATH.findall(verification):
                if not (REPO_ROOT / referenced).exists():
                    gate.add(
                        "matrix-test",
                        f"{identifier} references missing test path {referenced}",
                        MATRIX,
                    )


def summarise(gate: Gate, rows: list[tuple[str, list[str]]]) -> None:
    counts: dict[str, int] = {}
    for _identifier, cells in rows:
        if len(cells) != 6:
            continue
        match = STATUS.match(cells[5]) if cells[5] else None
        status = match.group("status").lower() if match else "unknown"
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(f"{name}: {count}" for name, count in sorted(counts.items()))
    gate.note(f"{len(rows)} requirement rows — {summary}")


def main(argv: list[str]) -> int:
    release, extras = parse_args(argv)
    if extras:
        print(f"unexpected argument(s): {' '.join(extras)}")
        return 2
    gate = Gate(
        name="requirements traceability",
        purpose="the matrix is complete and release-ready",
        release=release,
    )
    if not MATRIX.exists():  # pragma: no cover - guarded by the repository layout
        gate.add("matrix-structure", "the traceability matrix is missing", MATRIX)
        return gate.report()
    rows = _rows(MATRIX.read_text(encoding="utf-8"))
    if not rows:  # pragma: no cover - defensive
        gate.add("matrix-structure", "no requirement rows found", Path(MATRIX))
    check_rows(gate, rows)
    summarise(gate, rows)
    return gate.report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
