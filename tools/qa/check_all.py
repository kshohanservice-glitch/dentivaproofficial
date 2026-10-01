#!/usr/bin/env python3
"""Run every static quality gate and summarise the outcome.

Used by CI (development mode) and by the release checklist (``--release``), so the release cannot be
produced while the matrix is open, the product still talks to the network, money is handled with
floats, or unfinished markers are present.

Usage::

    python tools/qa/check_all.py
    python tools/qa/check_all.py --release
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GATES = (
    "check_no_placeholders.py",
    "check_money.py",
    "check_offline.py",
    "check_traceability.py",
)
HERE = Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    unknown = [arg for arg in argv if arg != "--release"]
    if unknown:
        print(f"unexpected argument(s): {' '.join(unknown)}")
        return 2
    flags = ["--release"] if "--release" in argv else []
    failed: list[str] = []
    for gate in GATES:
        script = HERE / gate
        result = subprocess.run(  # noqa: S603 - fixed interpreter and repository-owned script
            [sys.executable, str(script), *flags],
            check=False,
            text=True,
        )
        if result.returncode != 0:
            failed.append(gate)
    mode = "release" if flags else "development"
    print()
    if failed:
        print(f"GATES FAILED ({mode} mode): {', '.join(failed)}")
        return 1
    print(f"all {len(GATES)} static gates passed ({mode} mode)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
