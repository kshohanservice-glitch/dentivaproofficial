#!/usr/bin/env python3
"""Promote reviewed UI renders to the committed golden baseline.

Usage (after running the UI tests, which write the renders)::

    python -m pytest tests/ui -q
    python tools/promote_goldens.py                # promote everything reviewed
    python tools/promote_goldens.py --only shell-  # promote a subset
    python tools/promote_goldens.py --list         # show what would change

The tests render each state into ``tests/ui/artifacts/screens/`` (git-ignored) together with a
fingerprint JSON. This command copies those files into ``tests/ui/goldens/<platform>/`` so the next test
run compares against them. Review the PNGs before promoting: promoting is how a deliberate visual change
becomes the new expected picture.

A baseline may only be promoted for the platform that produced the renders — Windows goldens must come
from Windows (CI ``windows-latest``), because they are the authoritative baseline for the product.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests" / "ui"))

from golden_store import ARTIFACTS_DIR, GOLDENS_DIR, platform_key  # noqa: E402


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _promote(name: str, platform: str, *, dry_run: bool) -> str:
    """Copy one render's PNG + fingerprint into the baseline folder; returns what happened."""
    target_dir = GOLDENS_DIR / platform
    source_png = ARTIFACTS_DIR / f"{name}.png"
    source_json = ARTIFACTS_DIR / f"{name}.json"
    target_png = target_dir / f"{name}.png"
    target_json = target_dir / f"{name}.json"

    if target_png.exists() and target_json.exists():
        if _digest(target_png) == _digest(source_png) and _digest(target_json) == _digest(
            source_json
        ):
            return "unchanged"
        action = "updated"
    else:
        action = "added"

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_png, target_png)
        shutil.copyfile(source_json, target_json)
    return action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--platform",
        default=platform_key(),
        choices=["linux", "windows", "macos"],
        help="baseline folder to write (default: the running platform)",
    )
    parser.add_argument("--only", help="promote only renders whose name contains this text")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--list", action="store_true", help="list renders and exit")
    args = parser.parse_args(argv)

    if not ARTIFACTS_DIR.exists():
        print(f"No renders found in {ARTIFACTS_DIR}.")
        print("Run the UI tests first:  python -m pytest tests/ui -q")
        return 1

    renders = sorted(
        path.stem
        for path in ARTIFACTS_DIR.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("golden", False)
    )
    if not renders:
        print(f"{ARTIFACTS_DIR} holds no golden renders; run:  python -m pytest tests/ui -q")
        return 1

    if args.list:
        for name in renders:
            print(
                (
                    "has baseline"
                    if (GOLDENS_DIR / args.platform / f"{name}.png").exists()
                    else "no baseline"
                )
                + f"  {name}"
            )
        return 0

    if args.platform != platform_key():
        print(
            f"Refusing to promote {args.platform} goldens from a {platform_key()} render: the Windows "
            "baseline must be produced on Windows (CI windows-latest). Run this command on that platform, "
            "or from a checkout of the CI artifacts.",
            file=sys.stderr,
        )
        return 2

    names = [name for name in renders if not args.only or args.only in name]
    if not names:
        print(f"Nothing matched --only {args.only!r}.")
        return 1

    counts = {"added": 0, "updated": 0, "unchanged": 0}
    for name in names:
        action = _promote(name, args.platform, dry_run=args.dry_run)
        counts[action] += 1
        if action != "unchanged":
            print(f"{'would ' if args.dry_run else ''}{action}: {name}")

    print(
        f"{counts['added']} added, {counts['updated']} updated, {counts['unchanged']} unchanged "
        f"→ tests/ui/goldens/{args.platform}/"
    )
    if not args.dry_run and (counts["added"] or counts["updated"]):
        print("Review the diff of tests/ui/goldens/ before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
