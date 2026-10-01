#!/usr/bin/env python3
"""Static hygiene gate: no unfinished markers, debug prints, silent exception handlers, hard-coded
colours or placeholder content in the product source.

Development mode (default) enforces the rules that must hold from the first commit:

* ``unfinished-marker``  — ``TODO``/``FIXME``/``XXX``/``HACK`` in shipped code.
* ``debug-print``        — ``print()`` outside the diagnostic CLI entry point.
* ``silent-except``      — ``except``/``except Exception``/``except BaseException`` that only ``pass``es.
* ``hardcoded-colour``   — hex colours outside ``ui/design/`` (the design system owns colour).

Release mode (``--release``) additionally enforces that the development scaffolding is gone:

* ``placeholder-content``   — ``placeholder``/``coming soon``/``mock``/``dummy``/``lorem``/``fake``
                              wording, which at release would mean a screen that pretends to work.
* ``development-scaffold``  — the "not implemented yet" screen must not exist, and no navigation
                              entry may still be marked as unimplemented.

Usage::

    python tools/qa/check_no_placeholders.py
    python tools/qa/check_no_placeholders.py --release
"""

from __future__ import annotations

import ast
import re
import sys

from _common import SRC_ROOT, Gate, parse_args, python_files, rel, waived, waived_range

#: The only file allowed to write to stdout: ``python -m dentivapro --check`` is a command whose
#: output *is* its interface (the CI bundle smoke test parses it). Everything else logs.
PRINT_ALLOWED_FILES = {SRC_ROOT / "__main__.py"}

#: Marker words are matched on word boundaries to avoid false positives such as "mockingbird".
PLACEHOLDER_WORDS = ("placeholder", "coming soon", "mock", "dummy", "lorem", "fake")

UNFINISHED_MARKERS = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
HEX_COLOUR = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
PLACEHOLDER = re.compile(
    r"\b(" + "|".join(word.replace(" ", r"\s+") for word in PLACEHOLDER_WORDS) + r")\b",
    re.IGNORECASE,
)

DESIGN_DIR = SRC_ROOT / "ui" / "design"
PENDING_SCREEN = SRC_ROOT / "ui" / "screens" / "pending_screen.py"
NAVIGATION = SRC_ROOT / "ui" / "shell" / "navigation.py"

#: Silence is only a defect when the handler is broad. Narrow, typed handlers such as
#: ``except OSError`` around a best-effort cleanup are normal Python and are not flagged.
BROAD_EXCEPTIONS = {"Exception", "BaseException"}


def _silent_broad_handlers(tree: ast.AST) -> list[int]:
    """Line numbers of ``except``/``except Exception``/``except BaseException`` bodies that only pass."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = [
            item
            for item in node.body
            if not (
                isinstance(item, ast.Expr)
                and isinstance(item.value, ast.Constant)
                and isinstance(item.value.value, str)
            )
        ]
        if len(body) != 1:
            continue
        only = body[0]
        silent = isinstance(only, ast.Pass) or (
            isinstance(only, ast.Expr)
            and isinstance(only.value, ast.Constant)
            and only.value.value is Ellipsis
        )
        if not silent:
            continue
        is_broad = node.type is None or (
            isinstance(node.type, ast.Name) and node.type.id in BROAD_EXCEPTIONS
        )
        if is_broad:
            lines.append(node.lineno)
    return lines


def _print_calls(tree: ast.AST) -> list[tuple[int, int]]:
    """``(first_line, last_line)`` of every ``print(...)`` call, so multi-line calls stay waivable."""
    return [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]


def _check_lines(gate: Gate, path: object, lines: list[str]) -> None:
    """Line-oriented rules: markers, hard-coded colours and (at release) placeholder wording."""
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("#"):
            continue  # a comment that mentions a marker is not unfinished code
        if UNFINISHED_MARKERS.search(line) and not waived(lines, number, "unfinished-marker"):
            gate.add(
                "unfinished-marker", f"unfinished marker in {line.strip()[:60]!r}", path, number
            )  # type: ignore[arg-type]
        if (
            DESIGN_DIR not in (path, path.parent)
            and HEX_COLOUR.search(line)
            and not waived(lines, number, "hardcoded-colour")
        ):
            gate.add(
                "hardcoded-colour",
                "hex colour outside ui/design (use a design token)",
                path,
                number,
            )  # type: ignore[arg-type]
        if (
            gate.release
            and PLACEHOLDER.search(line)
            and not waived(lines, number, "placeholder-content")
        ):
            found = PLACEHOLDER.search(line)
            assert found is not None
            gate.add("placeholder-content", f"placeholder wording {found.group(0)!r}", path, number)  # type: ignore[arg-type]


def check_sources(gate: Gate) -> None:
    """Walk every product source file once and apply both the line and the AST rules."""
    for path in python_files():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        gate.checked += 1
        _check_lines(gate, path, lines)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue  # the test suite reports syntax errors first
        for lineno in _silent_broad_handlers(tree):
            if not waived(lines, lineno, "silent-except"):
                gate.add(
                    "silent-except",
                    "exception swallowed silently (narrow the type or log it)",
                    path,
                    lineno,
                )
        if path not in PRINT_ALLOWED_FILES:
            for first, last in _print_calls(tree):
                if not waived_range(lines, first, last, "debug-print"):
                    gate.add(
                        "debug-print", "print() call in product code (use the logger)", path, first
                    )


def check_release_scaffolding(gate: Gate) -> None:
    """At release there must be no screen or navigation entry that only pretends to work."""
    if PENDING_SCREEN.exists():
        gate.add(
            "development-scaffold",
            "the development screen must be removed before release",
            PENDING_SCREEN,
        )
    if NAVIGATION.exists():
        text = NAVIGATION.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if re.search(r"implemented\s*=\s*False", line) or re.search(r'phase=""', line):
                gate.add(
                    "development-scaffold",
                    "navigation entry is still unimplemented",
                    NAVIGATION,
                    number,
                )


def main(argv: list[str]) -> int:
    release, extras = parse_args(argv)
    if extras:
        print(f"unexpected argument(s): {' '.join(extras)}")
        return 2
    gate = Gate(
        name="static hygiene",
        purpose="no unfinished markers, debug prints, silent handlers, hard-coded colours or placeholders",
        release=release,
    )
    check_sources(gate)
    if release:
        check_release_scaffolding(gate)
    else:
        gate.note(
            "release-only rules (placeholder wording, development scaffolding) were not applied"
        )
    allowed = ", ".join(sorted(rel(path) for path in PRINT_ALLOWED_FILES))
    gate.note(f"print() allowed in {allowed} (diagnostic CLI whose stdout is its interface)")
    return gate.report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
