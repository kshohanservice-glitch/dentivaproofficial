"""Shared helpers for the Dentiva Pro static quality gates.

Every gate in this folder follows the same contract: it walks the repository, records findings and
exits non-zero when the run is not acceptable for the mode it was given (``--release`` tightens the
rules for the production release). They are ordinary scripts with no third-party dependency so they can
run in CI before the test suite is even installed.

A finding can be waived at the code site with a pragma on the same line or the line above::

    value = float(raw)  # qa-allow: float-in-finance - converting a legacy CSV value at the import edge

Waivers are deliberate and visible in review; a gate that cannot be waived would force developers to
work around it instead of documenting why the exception is correct.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "dentivapro"
SCHEMA_DIR = SRC_ROOT / "data" / "db" / "schema"
TESTS_ROOT = REPO_ROOT / "tests"

PYTHON_SUFFIXES = (".py",)
TEXT_SUFFIXES = (".py", ".sql", ".toml", ".ini", ".cfg", ".nsi", ".spec", ".yml", ".yaml", ".md")

#: Rule names may contain hyphens (``debug-print``), so the waiver is parsed as text: everything
#: after ``qa-allow:`` is the rule list, optionally followed by `` - reason`` explaining the waiver.
_PRAGMA_MARKER = "qa-allow:"
_PRAGMA_SEPARATORS = (" - ", " \u2014 ", " -- ", " \u2013 ")


def _rules_from(line: str) -> set[str]:
    """Rule names waived by a pragma on *line* (empty when there is no pragma)."""
    index = line.lower().find(_PRAGMA_MARKER)
    if index < 0:
        return set()
    body = line[index + len(_PRAGMA_MARKER) :].strip()
    for separator in _PRAGMA_SEPARATORS:
        cut = body.find(separator)
        if cut >= 0:
            body = body[:cut]
            break
    return {part.strip().lower() for part in body.split(",") if part.strip()}


@dataclass(frozen=True, slots=True)
class Finding:
    """One rule violation."""

    rule: str
    message: str
    path: Path
    line: int = 0

    def render(self) -> str:
        try:
            relative = self.path.relative_to(REPO_ROOT)
        except ValueError:  # pragma: no cover - defensive: paths outside the repository
            relative = self.path
        location = f"{relative}:{self.line}" if self.line else str(relative)
        return f"  {self.rule}: {location}: {self.message}"


@dataclass
class Gate:
    """A single check with its findings, notes and exit-code rules."""

    name: str
    purpose: str
    release: bool = False
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    checked: int = 0

    def add(self, rule: str, message: str, path: Path, line: int = 0) -> None:
        self.findings.append(Finding(rule=rule, message=message, path=path, line=line))

    def note(self, message: str) -> None:
        self.notes.append(message)

    def report(self) -> int:
        """Print the outcome and return the process exit code."""
        mode = "release" if self.release else "development"
        try:
            if self.findings:
                print(f"FAIL {self.name} ({mode} mode): {len(self.findings)} finding(s)")
                for finding in self.findings:
                    print(finding.render())
                return 1
            print(f"PASS {self.name} ({mode} mode): {self.checked} item(s) inspected")
            for note in self.notes:
                print(f"  note: {note}")
        except BrokenPipeError:  # pragma: no cover - the caller closed the pipe (e.g. `| head`)
            return 1 if self.findings else 0
        return 0

    @property
    def failed(self) -> bool:
        return bool(self.findings)


def parse_args(argv: list[str]) -> tuple[bool, list[str]]:
    """Return ``(release, extra_args)`` from a gate's command line."""
    release = "--release" in argv
    extras = [arg for arg in argv if arg != "--release"]
    return release, extras


def python_files(root: Path = SRC_ROOT) -> list[Path]:
    """Every Python file under *root* (sorted, deterministic)."""
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def schema_files() -> list[Path]:
    """Every schema migration, in version order."""
    return sorted(SCHEMA_DIR.glob("*.sql")) if SCHEMA_DIR.is_dir() else []


def waived(source_lines: list[str], line_number: int, rule: str) -> bool:
    """True when *rule* is waived by a pragma on this line or the line above (1-based numbers)."""
    if line_number < 1:
        return False
    for candidate in (line_number, line_number - 1):
        if 1 <= candidate <= len(source_lines):
            rules = _rules_from(source_lines[candidate - 1])
            if rule.lower() in rules or "all" in rules:
                return True
    return False


def waived_range(source_lines: list[str], first: int, last: int, rule: str) -> bool:
    """Like :func:`waived`, but for a statement that spans *first*…*last* (1-based, inclusive).

    A formatter may split a call over several lines, so the pragma can legitimately sit on the closing
    line. Only lines belonging to the statement (plus the line above it) are considered.
    """
    for candidate in range(first - 1, last + 1):
        if 1 <= candidate <= len(source_lines) and waived(source_lines, candidate, rule):
            return True
    return False


def rel(path: Path) -> str:
    """Repository-relative path for messages."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:  # pragma: no cover - defensive
        return str(path)


def main_wrapper(
    gate_fn: object, name: str
) -> int:  # pragma: no cover - convenience for simple gates
    """Run *gate_fn* (a callable returning a Gate) and print its report."""
    del name
    gate = gate_fn()
    assert isinstance(gate, Gate)
    return gate.report()


if __name__ == "__main__":  # pragma: no cover - helper module, not a gate
    print("This module provides helpers for the Dentiva Pro static quality gates.")
    sys.exit(0)
