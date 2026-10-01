#!/usr/bin/env python3
"""Financial-precision gate: accounting values are never binary floating point.

Rules
-----
* ``float-in-finance``   — no ``float(`` conversion in the money module, the data layer or the service
                           layer. Persistence uses integer paisa; arithmetic uses ``Decimal``.
* ``float-column``       — no ``REAL``/``FLOAT``/``DOUBLE``/``NUMERIC`` column in a schema migration.
* ``money-column-type``  — a column whose name ends in ``_paisa`` or ``_minor`` must be ``INTEGER``.
* ``money-representation`` — ``core/money.py`` must keep using ``Decimal`` and reject floats, so the
                           single source of truth cannot be quietly replaced.

Usage::

    python tools/qa/check_money.py
    python tools/qa/check_money.py --release
"""

from __future__ import annotations

import re
import sys

from _common import SRC_ROOT, Gate, parse_args, python_files, schema_files, waived

MONEY_MODULE = SRC_ROOT / "core" / "money.py"
FINANCE_DIRS = (SRC_ROOT / "data", SRC_ROOT / "services", SRC_ROOT / "core")

FLOAT_CALL = re.compile(r"\bfloat\s*\(")
FLOAT_COLUMN = re.compile(r"\b(REAL|FLOAT|DOUBLE|NUMERIC|DECIMAL)\b", re.IGNORECASE)
COLUMN_DEFINITION = re.compile(
    r"^\s*(?P<name>[a-z_][a-z0-9_]*)\s+(?P<type>[A-Za-z]+)", re.IGNORECASE
)
MONEY_COLUMN = re.compile(r"_(paisa|minor)$", re.IGNORECASE)


def check_python(gate: Gate) -> None:
    for path in python_files():
        if not any(path.is_relative_to(directory) for directory in FINANCE_DIRS):
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        gate.checked += 1
        for number, line in enumerate(lines, start=1):
            if FLOAT_CALL.search(line) and not waived(lines, number, "float-in-finance"):
                gate.add(
                    "float-in-finance",
                    "float() in a financial path (use Decimal or integer paisa)",
                    path,
                    number,
                )


def check_money_module(gate: Gate) -> None:
    if not MONEY_MODULE.exists():  # pragma: no cover - guarded by an earlier phase
        gate.add("money-representation", "core/money.py is missing", MONEY_MODULE)
        return
    text = MONEY_MODULE.read_text(encoding="utf-8")
    if "from decimal import" not in text or "Decimal" not in text:
        gate.add("money-representation", "money module no longer uses Decimal", MONEY_MODULE)
    if not re.search(r"isinstance\(\s*value\s*,\s*float\s*\)", text):
        gate.add("money-representation", "money module no longer rejects float input", MONEY_MODULE)
    gate.note("money.py uses Decimal and rejects float input")


def check_schema(gate: Gate) -> None:
    for path in schema_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        gate.checked += 1
        for number, line in enumerate(lines, start=1):
            if line.lstrip().startswith("--"):
                continue
            if FLOAT_COLUMN.search(line) and not waived(lines, number, "float-column"):
                gate.add(
                    "float-column",
                    "floating-point/numeric column type in a migration",
                    path,
                    number,
                )
            definition = COLUMN_DEFINITION.match(line)
            if definition and MONEY_COLUMN.search(definition.group("name")):
                declared = definition.group("type").upper()
                if not declared.startswith("INTEGER") and not waived(
                    lines, number, "money-column-type"
                ):
                    gate.add(
                        "money-column-type",
                        f"money column '{definition.group('name')}' is {declared}, not INTEGER",
                        path,
                        number,
                    )


def main(argv: list[str]) -> int:
    release, extras = parse_args(argv)
    if extras:
        print(f"unexpected argument(s): {' '.join(extras)}")
        return 2
    gate = Gate(
        name="financial precision",
        purpose="accounting values are integer paisa / Decimal, never binary floats",
        release=release,
    )
    check_python(gate)
    check_money_module(gate)
    check_schema(gate)
    gate.note(f"{len(schema_files())} schema migration(s) inspected")
    return gate.report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
