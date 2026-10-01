#!/usr/bin/env python3
"""Verify a built Dentiva Pro bundle.

Two levels:

* **Contents audit** (any platform, including this sandbox): the runtime assets an installation needs are
  present and nothing that must not ship is inside the bundle (tests, tooling, sample data, databases).
* **Launch smoke test** (Windows only): the packaged EXE is started offscreen against a temporary data
  root with ``--check``, and its output is required to report an initialised, integrity-checked database.

Usage::

    python packaging/check_bundle.py dist/DentivaPro
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

#: Paths inside the bundle (PyInstaller 6 keeps data under ``_internal``). Relative to the bundle root.
REQUIRED_FILES = (
    "dentivapro/assets/fonts/Inter.ttf",
    "dentivapro/assets/fonts/NotoSansBengali.ttf",
    "dentivapro/data/db/schema/001_base.sql",
    "dentivapro/assets/branding/app_icon.ico",
)

REQUIRED_DIRECTORIES = (
    "dentivapro/assets/icons",
    "dentivapro/assets/notices",
)

#: Path fragments that must never appear inside a shipped bundle.
FORBIDDEN_PARTS = (
    "/tests/",
    "/__pycache__/",
    "/tools/",
    "/packaging/",
    "/.git/",
)

FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".env", ".pdb")

#: Names that indicate development or sample data leaked into the bundle.
FORBIDDEN_NAMES = ("pytest", "sample_data", "demo_data", "seed_data", "conftest.py")

#: The icon set ships 60+ vector icons; fewer means the data files were not collected correctly.
MINIMUM_ICON_COUNT = 50

#: Fields the packaged application must report from its self-check (``DentivaPro.exe --check``).
#: The output is a ``key : value`` list, parsed rather than substring-matched.
EXPECTED_SELF_CHECK = {
    "journal mode": "wal",
    "foreign keys": "on",
    "integrity check": "ok",
    "bundled fonts": "ok",
}


def _candidates(root: Path, relative: str) -> list[Path]:
    """A bundle path, allowing for PyInstaller's ``_internal`` layout."""
    return [root / relative, root / "_internal" / relative]


def check_contents(bundle: Path) -> list[str]:
    """Return the list of problems found in *bundle* (empty means it passed)."""
    problems: list[str] = []

    problems += [
        f"missing required file: {relative}"
        for relative in REQUIRED_FILES
        if not any(candidate.is_file() for candidate in _candidates(bundle, relative))
    ]
    problems += [
        f"missing required directory: {relative}"
        for relative in REQUIRED_DIRECTORIES
        if not any(candidate.is_dir() for candidate in _candidates(bundle, relative))
    ]

    icons_dir = next(
        (c for c in _candidates(bundle, "dentivapro/assets/icons") if c.is_dir()), None
    )
    if icons_dir is not None and len(list(icons_dir.glob("*.svg"))) < MINIMUM_ICON_COUNT:
        problems.append(f"icon set looks incomplete in {icons_dir}")

    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        parts = "/" + path.relative_to(bundle).as_posix() + "/"
        if any(forbidden in parts for forbidden in FORBIDDEN_PARTS):
            problems.append(f"forbidden path in bundle: {path.relative_to(bundle)}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden file type in bundle: {path.relative_to(bundle)}")
        lowered = path.name.lower()
        if any(name in lowered for name in FORBIDDEN_NAMES):
            problems.append(f"development/sample file in bundle: {path.relative_to(bundle)}")

    return problems


def parse_self_check(output: str) -> dict[str, str]:
    """Parse the ``key : value`` lines the packaged application prints for ``--check``."""
    reported: dict[str, str] = {}
    for line in output.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            reported[key.strip()] = value.strip()
    return reported


def check_launch(bundle: Path) -> tuple[list[str], str]:
    """Start the packaged application offscreen and verify it initialises a database.

    Returns the problems found and the captured output (shown when something is wrong, because a
    windowed executable's output is the only diagnostic available in CI).
    """
    problems: list[str] = []
    executable = next(bundle.glob("*.exe"), None)
    if executable is None:
        return [f"no executable found in {bundle} (bundle build did not complete?)"], ""

    with tempfile.TemporaryDirectory(prefix="dentivapro-smoke-") as data_root:
        environment = dict(os.environ)
        environment["DENTIVAPRO_DATA_ROOT"] = data_root
        environment["QT_QPA_PLATFORM"] = "offscreen"
        completed = subprocess.run(  # noqa: S603 - path is the bundle we just built
            [str(executable), "--check"],
            capture_output=True,
            text=True,
            timeout=180,
            env=environment,
            check=False,
        )
        output = completed.stdout + completed.stderr
        if completed.returncode != 0:
            problems.append(f"{executable.name} --check exited with {completed.returncode}")
        reported = parse_self_check(output)

        if not reported.get("schema version"):
            problems.append("the application did not report a schema version")
        tables = reported.get("tables", "")
        if not tables.isdigit() or int(tables) < 1:
            problems.append(f"the application reported tables as {tables!r}")
        problems += [
            f"self-check reported {key!r} as {reported.get(key)!r} (expected {expected!r})"
            for key, expected in EXPECTED_SELF_CHECK.items()
            if reported.get(key) != expected
        ]

        if not (Path(data_root) / "dentivapro.db").exists():
            problems.append("the application did not create its database file")
        else:
            print("bundle self-check:", ", ".join(f"{k}={v}" for k, v in sorted(reported.items())))
    return problems, output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bundle", type=Path, help="bundle directory, e.g. dist/DentivaPro")
    parser.add_argument("--skip-launch", action="store_true", help="contents audit only")
    args = parser.parse_args(argv)

    bundle: Path = args.bundle
    if not bundle.is_dir():
        print(f"{bundle} is not a directory", file=sys.stderr)
        return 2

    problems = check_contents(bundle)
    launch_output = ""
    if not args.skip_launch and sys.platform.startswith("win"):
        launch_problems, launch_output = check_launch(bundle)
        problems += launch_problems
    elif not args.skip_launch:
        print("note: launch smoke test skipped (not running on Windows)")

    if problems:
        print(f"{len(problems)} problem(s) found in {bundle}:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        if launch_output.strip():
            print("--- captured application output ---", file=sys.stderr)
            print(launch_output[-4000:], file=sys.stderr)
        return 1

    print(f"bundle OK: {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
