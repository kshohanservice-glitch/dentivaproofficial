"""SVG icon rendering.

Icons are vector files shipped in ``assets/icons`` (a curated subset of Lucide, ISC licence, plus
purpose-drawn dental glyphs). They are tinted at request time, rendered at exact pixel sizes for the
current device pixel ratio and cached, so the interface stays crisp at every Windows scaling factor
without shipping raster assets for each size.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from dentivapro.core.logging import get_logger, log_event
from dentivapro.ui.design.tokens import tokens

logger = get_logger(__name__)

ICONS_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "assets" / "icons"

#: Icons referenced by code. Declaring them here means a missing file fails a test rather than
#: silently rendering an empty button in front of a user.
REQUIRED_ICONS: Final[frozenset[str]] = frozenset(
    {
        "layout-dashboard",
        "users",
        "calendar-days",
        "list-ordered",
        "stethoscope",
        "pill",
        "receipt-text",
        "banknote",
        "package",
        "calculator",
        "user-cog",
        "database-backup",
        "settings",
        "info",
        "bell",
        "search",
        "chevron-left",
        "chevron-right",
        "chevron-down",
        "chevron-up",
        "panel-left-close",
        "panel-left-open",
        "x",
        "check",
        "circle-alert",
        "triangle-alert",
        "circle-check",
        "lock",
        "log-out",
        "printer",
        "file-text",
        "paperclip",
        "trash",
        "square-pen",
        "plus",
        "funnel",
        "download",
        "upload",
        "refresh-cw",
        "clock",
        "phone",
        "map-pin",
        "shield-check",
        "rotate-ccw",
        "forward",
        "clipboard-list",
        "calendar-check",
        "chart-column",
        "sparkles",
        "circle-question-mark",
        "arrow-left",
        "arrow-right",
        "zoom-in",
        "zoom-out",
        "eye",
        "pencil",
        "circle-x",
        "folder-open",
        "hard-drive",
        "user-round",
        "calendar-clock",
        "tooth",
    }
)

#: Fallback drawn when an icon file is missing: a neutral rounded square outline, so a layout defect
#: is visible in review instead of an invisible gap.
FALLBACK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 12h6"/></svg>'
)


class IconRegistry:
    """Loads, tints, caches and renders application icons."""

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or ICONS_DIR
        self._svg_cache: dict[str, str] = {}
        self._pixmap_cache: dict[tuple[str, int, str, float], QPixmap] = {}
        self._missing: set[str] = set()

    # ---- sources ---------------------------------------------------------
    def svg(self, name: str) -> str:
        """Return the raw SVG markup for *name*, substituting currentColor for *color*."""
        if name in self._svg_cache:
            return self._svg_cache[name]
        path = self._dir / f"{name}.svg"
        try:
            markup = path.read_text(encoding="utf-8")
        except OSError:
            self._missing.add(name)
            log_event(logger, 30, "icons.missing", icon=name, path=str(path))
            markup = FALLBACK_SVG
        self._svg_cache[name] = markup
        return markup

    def available(self) -> list[str]:
        """Return the names of every icon file on disk."""
        return sorted(path.stem for path in self._dir.glob("*.svg"))

    @property
    def missing(self) -> frozenset[str]:
        """Icons that were requested but not found."""
        return frozenset(self._missing)

    # ---- rendering --------------------------------------------------------
    def pixmap(
        self,
        name: str,
        size: int,
        color: str,
        *,
        device_pixel_ratio: float = 1.0,
        stroke_width: float | None = None,
    ) -> QPixmap:
        """Render *name* as a tinted pixmap of exactly *size* logical pixels."""
        key = (name, size, color, round(device_pixel_ratio, 2))
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            return cached

        markup = self.svg(name).replace("currentColor", color)
        if stroke_width is not None:
            markup = markup.replace('stroke-width="2"', f'stroke-width="{stroke_width:g}"')
        renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))

        physical = max(1, int(round(size * device_pixel_ratio)))
        pixmap = QPixmap(physical, physical)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter, QRectF(0, 0, physical, physical))
        painter.end()
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        self._pixmap_cache[key] = pixmap
        return pixmap

    def icon(self, name: str, size: int | None = None, color: str | None = None) -> QIcon:
        """Return a themed :class:`QIcon` for *name*."""
        tokens_value = tokens()
        resolved_size = size or tokens_value.metrics.icon_md
        resolved_color = color or tokens_value.palette.ink_600
        icon = QIcon()
        for ratio in (1.0, 1.5, 2.0, 3.0):
            icon.addPixmap(
                self.pixmap(name, resolved_size, resolved_color, device_pixel_ratio=ratio)
            )
        return icon

    def clear_cache(self) -> None:
        """Drop cached pixmaps (used when the theme or scaling changes)."""
        self._pixmap_cache.clear()


_registry = IconRegistry()


def icons() -> IconRegistry:
    """Return the process-wide icon registry."""
    return _registry


def icon(name: str, size: int | None = None, color: str | None = None) -> QIcon:
    """Convenience wrapper for :meth:`IconRegistry.icon`."""
    return _registry.icon(name, size, color)


def icon_pixmap(name: str, size: int, color: str, *, device_pixel_ratio: float = 1.0) -> QPixmap:
    """Convenience wrapper for :meth:`IconRegistry.pixmap`."""
    return _registry.pixmap(name, size, color, device_pixel_ratio=device_pixel_ratio)


def missing_icons() -> frozenset[str]:
    """Return icons that failed to load (checked by the test suite)."""
    return _registry.missing


def check_required_icons() -> list[str]:
    """Return required icons that are absent from the asset folder."""
    return sorted(REQUIRED_ICONS.difference(path.stem for path in ICONS_DIR.glob("*.svg")))


def icon_size(hint: str) -> QSize:
    """Return a QSize for a named metric (``sm``, ``md``, ``lg``, ``xl``)."""
    metrics = tokens().metrics
    mapping = {
        "sm": metrics.icon_sm,
        "md": metrics.icon_md,
        "lg": metrics.icon_lg,
        "xl": metrics.icon_xl,
    }
    size = mapping.get(hint, metrics.icon_md)
    return QSize(size, size)


def tinted_icon_colors() -> dict[str, str]:
    """Return the semantic colours icons use, so screens never invent their own."""
    palette = tokens().palette
    return {
        "default": palette.ink_600,
        "muted": palette.ink_400,
        "accent": palette.accent_600,
        "on_accent": "#FFFFFF",
        "danger": palette.danger_fg,
        "success": palette.success_fg,
        "warning": palette.warning_fg,
        "info": palette.info_fg,
    }


#: Number of channels in an ``rgba(...)`` token (red, green, blue, alpha).
_RGBA_CHANNELS: Final[int] = 4


def parse_color(value: str) -> QColor:
    """Parse a ``#rrggbb`` or ``rgba(...)`` token value into a QColor."""
    if value.startswith("rgba"):
        parts = value[value.index("(") + 1 : value.rindex(")")].split(",")
        red, green, blue = (int(float(part.strip())) for part in parts[: _RGBA_CHANNELS - 1])
        alpha = (
            int(float(parts[_RGBA_CHANNELS - 1].strip()) * 255)
            if len(parts) >= _RGBA_CHANNELS
            else 255
        )
        return QColor(red, green, blue, alpha)
    return QColor(value)
