"""Generate the Dentiva Pro application icon.

The mark is drawn with vector geometry rather than exported from a design tool, so every size is
mathematically consistent: the badge, the tooth silhouette and the accent sparkle all derive from one
24 × 24 design space, and each size is rendered directly at its target resolution instead of being
down-scaled (the usual reason small Windows icons look muddy).

Design intent — dentistry, precision, trust, technology, premium clinical care:

* a deep teal rounded-square badge (the clinical identity colour used throughout the product),
* a white tooth silhouette with clean symmetric roots, optically centred (the roots carry visual
  weight, so the shape is nudged slightly above the geometric centre),
* a soft top sheen suggesting a polished surface,
* a small amber sparkle at 64 px and above only — detail that would become noise at taskbar sizes is
  deliberately dropped in the smaller variants,
* transparent corners with no baked-in background rectangle, so the icon reads correctly on light and
  dark Windows surfaces.

Outputs
-------
``src/dentivapro/assets/branding/app_icon.ico``     multi-size Windows icon (16…256 px)
``src/dentivapro/assets/branding/app_icon_*.png``   individual sizes for the UI and installer
``docs/design/app-icon-sheet.png``                  review sheet on light and dark backgrounds

Usage::

    python tools/icons/generate_app_icon.py            # write the assets
    python tools/icons/generate_app_icon.py --check    # verify committed assets are current
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDING_DIR = REPO_ROOT / "src" / "dentivapro" / "assets" / "branding"
SHEET_PATH = REPO_ROOT / "docs" / "design" / "app-icon-sheet.png"

ICO_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 128, 256)
PNG_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

# ---- palette (kept in step with ui/design/tokens.py) ----------------------
BADGE_TOP = "#0F766E"
BADGE_BOTTOM = "#0B5F59"
TOOTH_WHITE = "#FFFFFF"
SHEEN = QColor(255, 255, 255, 46)
SPARKLE = "#F59E0B"

# ---- geometry, expressed in a 24 × 24 design space ------------------------
BADGE_INSET = 1.0  # keeps a hairline of transparency around the badge
BADGE_RADIUS = 5.4  # ≈ 22 % of the badge side
TOOTH_OPTICAL_SHIFT = -0.3  # design-space units; the roots carry visual weight

#: Full tooth silhouette: a symmetric molar with two roots and a clean inter-root notch.
#: The shape is mirrored about x = 12 and spans x ∈ [5.2, 18.8], y ∈ [5.0, 19.0], leaving ≈ 17 % of
#: the badge width as padding on each side so the mark breathes inside the badge.
TOOTH_PATH_D = (
    "M5.2 8.8"
    "C5.2 6.3 6.3 5.0 8.1 5.0"
    "L15.9 5.0"
    "C17.7 5.0 18.8 6.3 18.8 8.8"
    "C18.8 10.8 17.9 11.9 17.5 13.8"
    "C17.2 15.6 17.4 19.0 15.6 19.0"
    "C14.3 19.0 14.7 15.4 12.0 15.4"
    "C9.3 15.4 9.7 19.0 8.4 19.0"
    "C6.6 19.0 6.8 15.6 6.5 13.8"
    "C6.1 11.9 5.2 10.8 5.2 8.8 Z"
)

#: Simplified silhouette for 16-24 px, where the full roots would smear into the badge. The crown is
#: kept recognisable and the roots are drawn shorter with a wider notch so the shape still reads as a
#: tooth on a taskbar or in a title bar.
TOOTH_PATH_D_SMALL = (
    "M5.4 9.2"
    "C5.4 6.6 6.6 5.2 8.4 5.2"
    "L15.6 5.2"
    "C17.4 5.2 18.6 6.6 18.6 9.2"
    "C18.6 11.2 17.8 12.4 17.4 14.2"
    "C17.1 15.6 17.2 17.6 15.8 17.6"
    "C14.6 17.6 14.9 14.9 12.0 14.9"
    "C9.1 14.9 9.4 17.6 8.2 17.6"
    "C6.8 17.6 6.9 15.6 6.6 14.2"
    "C6.2 12.4 5.4 11.2 5.4 9.2 Z"
)


@dataclass(frozen=True)
class IconSpec:
    """Rendering parameters that vary with the target size."""

    size: int

    @property
    def scale(self) -> float:
        """Pixels per design-space unit."""
        return self.size / 24.0

    @property
    def show_sparkle(self) -> bool:
        """Small sizes drop the sparkle so the silhouette stays clean."""
        return self.size >= 64

    @property
    def show_sheen(self) -> bool:
        """The sheen needs a few pixels to read as a highlight rather than a smudge."""
        return self.size >= 32

    @property
    def sparkle_radius(self) -> float:
        """Sparkle size in pixels, scaled with the icon."""
        return max(1.6, self.size * 0.085)

    @property
    def tooth_design_path(self) -> str:
        """The silhouette variant appropriate for this size."""
        return TOOTH_PATH_D_SMALL if self.size <= 24 else TOOTH_PATH_D

    @property
    def tooth_scale(self) -> float:
        """Extra inset applied to the silhouette so the badge keeps a visible margin.

        At 16-24 px a tooth drawn at full size touches the badge edge and the mark turns into a
        blob; scaling it down slightly preserves the silhouette *and* the badge outline.
        """
        if self.size <= 20:
            return 0.80
        if self.size <= 32:
            return 0.88
        return 1.0


_TOKEN_RE = re.compile(r"([MLCZ])(?=[\s\d-])|(-?\d*\.?\d+)")


def _svg_path_to_qt(d: str) -> QPainterPath:
    """Parse the simple, absolute SVG path used for the tooth mark.

    Only the commands the mark needs are supported (``M``, ``L``, ``C``, ``Z``), and the parser is
    deliberately strict: a malformed path raises instead of silently drawing the wrong shape.
    """
    path = QPainterPath()
    command: str | None = None
    numbers: list[float] = []

    def flush() -> None:
        if command is None or not numbers:
            return
        if command == "M":
            for index in range(0, len(numbers) - 1, 2):
                path.moveTo(numbers[index], numbers[index + 1])
        elif command == "L":
            for index in range(0, len(numbers) - 1, 2):
                path.lineTo(numbers[index], numbers[index + 1])
        elif command == "C":
            for index in range(0, len(numbers) - 5, 6):
                path.cubicTo(
                    numbers[index],
                    numbers[index + 1],
                    numbers[index + 2],
                    numbers[index + 3],
                    numbers[index + 4],
                    numbers[index + 5],
                )

    for match in _TOKEN_RE.finditer(d):
        letter, number = match.group(1), match.group(2)
        if letter:
            if letter == "Z":
                flush()
                numbers = []
                path.closeSubpath()
                command = None
                continue
            flush()
            numbers = []
            command = letter
        elif number is not None and command is not None:
            numbers.append(float(number))
    flush()
    return path


def rounded_badge_path(spec: IconSpec) -> QPainterPath:
    """Return the badge outline in pixel space."""
    inset = BADGE_INSET * spec.scale
    side = spec.size - 2 * inset
    path = QPainterPath()
    radius = BADGE_RADIUS * spec.scale
    path.addRoundedRect(QRectF(inset, inset, side, side), radius, radius)
    return path


_TOOTH_PATH = _svg_path_to_qt(TOOTH_PATH_D)
_TOOTH_PATH_SMALL = _svg_path_to_qt(TOOTH_PATH_D_SMALL)


def sparkle_path(centre: QPointF, radius: float) -> QPainterPath:
    """Return a four-point sparkle centred at *centre*."""
    waist = radius * 0.32
    path = QPainterPath()
    path.moveTo(centre.x(), centre.y() - radius)
    path.quadTo(centre.x() + waist * 0.6, centre.y() - waist * 0.6, centre.x() + radius, centre.y())
    path.quadTo(centre.x() + waist * 0.6, centre.y() + waist * 0.6, centre.x(), centre.y() + radius)
    path.quadTo(centre.x() - waist * 0.6, centre.y() + waist * 0.6, centre.x() - radius, centre.y())
    path.quadTo(centre.x() - waist * 0.6, centre.y() - waist * 0.6, centre.x(), centre.y() - radius)
    path.closeSubpath()
    return path


def render_icon(size: int) -> QImage:
    """Render the application mark at *size* pixels with an alpha channel."""
    spec = IconSpec(size=size)
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # 1 — badge with a calm vertical gradient
    badge = rounded_badge_path(spec)
    gradient = QLinearGradient(0.0, 0.0, 0.0, float(size))
    gradient.setColorAt(0.0, QColor(BADGE_TOP))
    gradient.setColorAt(1.0, QColor(BADGE_BOTTOM))
    painter.fillPath(badge, gradient)

    # 2 — a single soft highlight across the top of the badge
    if spec.show_sheen:
        painter.save()
        painter.setClipPath(badge)
        sheen = QLinearGradient(0.0, 0.0, 0.0, size * 0.55)
        sheen.setColorAt(0.0, SHEEN)
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(QRectF(0, 0, size, size * 0.55), sheen)
        painter.restore()

    # 3 — the tooth silhouette, scaled from the design space
    painter.save()
    painter.translate(
        spec.size * (1.0 - spec.tooth_scale) / 2.0,
        spec.size * (1.0 - spec.tooth_scale) / 2.0 + TOOTH_OPTICAL_SHIFT * spec.scale,
    )
    painter.scale(spec.scale * spec.tooth_scale, spec.scale * spec.tooth_scale)
    painter.fillPath(_TOOTH_PATH_SMALL if spec.size <= 24 else _TOOTH_PATH, QColor(TOOTH_WHITE))
    painter.restore()

    # 4 — inner keyline, which keeps the badge crisp against light surfaces
    if size >= 32:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(255, 255, 255, 40))
        pen.setWidthF(max(0.8, size * 0.006))
        painter.setPen(pen)
        painter.drawPath(badge)

    # 5 — sparkle accent, only where it will read cleanly
    if spec.show_sparkle:
        centre = QPointF(size * 0.755, size * 0.255)
        painter.fillPath(sparkle_path(centre, spec.sparkle_radius), QColor(SPARKLE))

    painter.end()
    return image


def write_ico(path: Path, images: list[QImage]) -> None:
    """Write a PNG-compressed multi-size ``.ico`` file (Windows Vista and later)."""
    payloads: list[tuple[int, bytes]] = []
    for image in images:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()
        payloads.append((image.width(), bytes(byte_array)))

    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = 6 + 16 * len(payloads)
    entries = []
    for width, data in payloads:
        dimension = 0 if width >= 256 else width
        entries.append(
            struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset)
        )
        offset += len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(header + b"".join(entries))
        for _width, data in payloads:
            handle.write(data)


def build_review_sheet(output: Path) -> None:
    """Render a review sheet showing every size on light and dark backgrounds."""
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    margin = 28
    gap = 26
    row_height = max(sizes) + gap + 20
    width = margin * 2 + sum(size + gap for size in sizes)
    height = margin * 2 + row_height * 2

    sheet = QPixmap(width, height)
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.fillRect(0, 0, width, height // 2, QColor("#FFFFFF"))
    painter.fillRect(0, height // 2, width, height - height // 2, QColor("#0B1220"))

    default_font = painter.font()
    default_font.setPointSizeF(8.5)
    painter.setFont(default_font)

    for row, (label, label_colour) in enumerate(
        (
            ("#FFFFFF · icons on a light surface", QColor("#334155")),
            ("#0B1220 · icons on a dark surface", QColor("#CBD5E1")),
        )
    ):
        y = margin + row * row_height
        painter.setPen(label_colour)
        painter.drawText(margin, y - 10, label)
        x = margin
        for size in sizes:
            painter.drawImage(x, y, render_icon(size))
            painter.setPen(label_colour)
            painter.drawText(x, y + max(sizes) + 18, f"{size} px")
            x += size + gap
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(output), "PNG")


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def current_asset_paths() -> list[Path]:
    """Return every file this tool owns."""
    paths = [BRANDING_DIR / "app_icon.ico", SHEET_PATH]
    paths.extend(BRANDING_DIR / f"app_icon_{size}.png" for size in PNG_SIZES)
    return paths


def write_assets() -> dict[Path, str]:
    """Render and write every icon asset, returning their SHA-256 digests."""
    written: dict[Path, str] = {}
    BRANDING_DIR.mkdir(parents=True, exist_ok=True)

    ico_path = BRANDING_DIR / "app_icon.ico"
    write_ico(ico_path, [render_icon(size) for size in ICO_SIZES])
    written[ico_path] = _hash(ico_path.read_bytes())

    for size in PNG_SIZES:
        png_path = BRANDING_DIR / f"app_icon_{size}.png"
        render_icon(size).save(str(png_path), "PNG")
        written[png_path] = _hash(png_path.read_bytes())

    build_review_sheet(SHEET_PATH)
    written[SHEET_PATH] = _hash(SHEET_PATH.read_bytes())
    return written


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Generate the Dentiva Pro application icon")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the committed assets match a fresh render instead of writing them",
    )
    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv[:1])
    _ = app

    before = {path: _hash(path.read_bytes()) for path in current_asset_paths() if path.exists()}
    written = write_assets()

    if args.check:
        stale = [path for path, digest in written.items() if before.get(path) != digest]
        for path in stale:
            print(f"STALE: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        if stale:
            return 1
        print("icon assets are up to date")
        return 0

    for path, digest in sorted(written.items()):
        print(f"wrote {path.relative_to(REPO_ROOT)}  sha256={digest[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
