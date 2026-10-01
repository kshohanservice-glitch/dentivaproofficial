#!/usr/bin/env python3
"""Fail the build when a credential or an activation secret would be committed.

The product ships fully offline, and its one-time activation code must never exist in plaintext anywhere
in the repository (source, tests, CI logs, documentation) — it is verified through derived values only.
This scan is deliberately simple and fast enough for every CI run:

* private-key blocks and common token shapes (GitHub, AWS, Slack, generic ``sk-`` keys),
* long numeric literals (the activation code is a 16-digit decimal value),
* ``password = "…"``-style assignments with a real value,

Findings are reported **redacted** (a hint, never the value) so a CI log cannot leak what it caught.

Usage::

    python tools/secret_scan.py [paths…]        # defaults to every tracked file
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: (name, compiled pattern, redact) — the match is never printed verbatim.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("github fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("openai-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("assigned password", re.compile(r"""(?i)\bpassword\s*[:=]\s*["'][^"'\s]{6,}["']""")),
    ("16-digit literal", re.compile(r"(?<!\d)\d{16}(?!\d)")),
)

#: File types that are never text (skipped) and paths that are generated or third-party.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".ico", ".ttf", ".otf", ".woff", ".woff2", ".pdf", ".zip"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "artifacts"}


def tracked_files() -> list[Path]:
    """Every file git knows about, plus the working tree's untracked-but-not-ignored files."""
    try:
        output = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:  # pragma: no cover - CI uses git
        print(
            f"could not list repository files ({error}); passing an explicit path instead",
            file=sys.stderr,
        )
        return []
    return [REPO_ROOT / line.strip() for line in output.splitlines() if line.strip()]


def scan(path: Path) -> list[str]:
    """Findings for one file, formatted as ``path:line: description`` with the value redacted."""
    findings: list[str] = []
    if path.suffix.lower() in SKIP_SUFFIXES or any(part in SKIP_PARTS for part in path.parts):
        return findings
    if not path.is_file():
        return findings
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings

    for number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            match = pattern.search(line)
            if match:
                hint = (
                    f"{match.group()[:4]}… ({len(match.group())} chars)"
                    if len(match.group()) > 4
                    else "short"
                )
                findings.append(f"{path.relative_to(REPO_ROOT)}:{number}: {name} [{hint}]")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths", nargs="*", type=Path, help="files to scan (default: tracked files)"
    )
    args = parser.parse_args(argv)

    files = args.paths or tracked_files()
    if not files:
        print("nothing to scan", file=sys.stderr)
        return 1

    findings: list[str] = []
    for path in files:
        findings.extend(scan(path))

    if findings:
        print(f"secret scan failed: {len(findings)} finding(s)", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1

    print(f"secret scan clean ({len(files)} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
