"""Committed golden images for the shell and its components.

Why fingerprints instead of raw pixels
--------------------------------------
A byte-for-byte image comparison between the Linux development sandbox and the Windows CI runner fails
because the two text rasterisers anti-alias slightly differently, even with the bundled fonts. A test
that fails for reasons unrelated to the product is worse than no test, so a render is reduced to a
deterministic *fingerprint*: the image is smoothly scaled to a small grid and each cell records the
average colour. A layout change (a moved card, a different sidebar width, a missing banner) changes
which colour lands in which cell and is caught, while sub-pixel anti-aliasing noise stays inside the
tolerance.

Baselines are per platform: ``goldens/linux/`` (the sandbox baseline, committed from here) and
``goldens/windows/`` (authoritative — the product is Windows-first; produced and promoted from
``windows-latest`` CI). A platform without an approved baseline skips with an explanation instead of
pretending to have verified something.

Workflow for an intentional UI change::

    python -m pytest tests/ui -q                  # renders + writes tests/ui/artifacts/screens/
    # review the PNGs, then promote them for the current platform:
    python tools/promote_goldens.py

The promoted PNGs are committed next to their JSON fingerprints so a reviewer can see exactly what was
approved.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

#: Directory holding the committed goldens, split per platform.
GOLDENS_DIR = Path(__file__).resolve().parent / "goldens"

#: Directory the tests write rendered PNGs and fingerprints to (git-ignored).
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts" / "screens"

#: Fingerprint resolution: coarse enough to ignore anti-aliasing, fine enough to catch a moved widget.
GRID = (16, 12)

#: A cell may differ from the golden by this much per channel before it counts as changed.
CHANNEL_TOLERANCE = 16

#: Fraction of the grid allowed to differ (a couple of cells cover a stray caret or a focus ring).
MAX_MISMATCHED_RATIO = 0.10

#: Shown to whoever has to approve a new platform baseline.
PROMOTE_COMMAND = "python tools/promote_goldens.py"


def platform_key() -> str:
    """The baseline folder to use for the running platform."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def fingerprint(image: QImage) -> dict[str, Any]:
    """Reduce *image* to a small, comparable summary (size plus averaged colour grid)."""
    flat = image.copy()
    flat.setDevicePixelRatio(1.0)
    columns, rows = GRID
    small = flat.scaled(
        columns,
        rows,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    cells: list[list[int]] = []
    for y in range(rows):
        for x in range(columns):
            colour = small.pixelColor(x, y)
            cells.append([colour.red(), colour.green(), colour.blue()])
    return {"width": image.width(), "height": image.height(), "grid": list(GRID), "cells": cells}


def fingerprint_path(name: str, platform: str | None = None) -> Path:
    return GOLDENS_DIR / (platform or platform_key()) / f"{name}.json"


def image_path(name: str, platform: str | None = None) -> Path:
    return GOLDENS_DIR / (platform or platform_key()) / f"{name}.png"


def load_golden(name: str, platform: str | None = None) -> dict[str, Any] | None:
    """The approved fingerprint for *name*, or ``None`` when this platform has no baseline yet."""
    path = fingerprint_path(name, platform)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compare(current: dict[str, Any], golden: dict[str, Any]) -> list[str]:
    """Human-readable reasons why *current* differs from *golden* (empty list means it matches)."""
    reasons: list[str] = []
    if (current["width"], current["height"]) != (golden["width"], golden["height"]):
        reasons.append(
            f"image size changed from {golden['width']}x{golden['height']} "
            f"to {current['width']}x{current['height']}"
        )
        return reasons
    if list(current["grid"]) != list(golden["grid"]):
        reasons.append(f"fingerprint grid changed from {golden['grid']} to {current['grid']}")
        return reasons

    cells: list[list[int]] = current["cells"]
    reference: list[list[int]] = golden["cells"]
    if len(cells) != len(reference):
        reasons.append(f"fingerprint has {len(cells)} cells, golden has {len(reference)}")
        return reasons

    mismatched = 0
    worst = 0
    for cell, ref in zip(cells, reference, strict=True):
        delta = max(abs(cell[channel] - ref[channel]) for channel in range(3))
        worst = max(worst, delta)
        if delta > CHANNEL_TOLERANCE:
            mismatched += 1

    ratio = mismatched / len(reference)
    if ratio > MAX_MISMATCHED_RATIO:
        reasons.append(
            f"{mismatched}/{len(reference)} fingerprint cells changed by more than "
            f"{CHANNEL_TOLERANCE}/255 (worst {worst}); review the render and, if it is intentional, "
            f"run: {PROMOTE_COMMAND}"
        )
    return reasons


def distinct_colours(rendered: dict[str, Any]) -> int:
    """How many different colours the fingerprint grid holds — a cheap "was anything drawn" check."""
    return len({tuple(cell) for cell in rendered["cells"]})


def save_render(image: QImage, name: str, *, golden: bool = True) -> tuple[Path, Path]:
    """Write the rendered PNG and its fingerprint into the artifacts directory (both git-ignored).

    *golden* marks the renders the suite compares against a committed baseline; renders saved with
    ``golden=False`` are review artifacts only and are not promoted by ``tools/promote_goldens.py``.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    png = ARTIFACTS_DIR / f"{name}.png"
    if not image.save(str(png)):
        raise OSError(f"could not write {png}")
    payload = fingerprint(image)
    payload["golden"] = golden
    json_path = ARTIFACTS_DIR / f"{name}.json"
    json_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return png, json_path
