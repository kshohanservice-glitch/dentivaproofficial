"""Font loading and text helpers.

Brand and Bengali fonts are bundled with the application and registered explicitly, so typography and
Bangla shaping are identical on every Windows machine — no dependency on which fonts happen to be
installed, and no risk of Bengali text silently turning into boxes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF

from dentivapro.core.logging import get_logger, log_event
from dentivapro.ui.design.tokens import tokens

logger = get_logger(__name__)

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

#: Font files shipped with the product (SIL Open Font License 1.1, see assets/notices).
BUNDLED_FONTS: tuple[str, ...] = ("Inter.ttf", "NotoSansBengali.ttf")

#: Characters used to detect whether Bengali shaping is available.
BENGALI_PROBE = "ডেন্টিভা প্রো"


class FontRegistry:
    """Loads the bundled fonts once and reports what is available."""

    def __init__(self) -> None:
        self._loaded = False
        self._available: dict[str, str] = {}
        self._missing: list[str] = []

    def load(self) -> None:
        """Register every bundled font file with Qt."""
        if self._loaded:
            return
        for filename in BUNDLED_FONTS:
            path = FONTS_DIR / filename
            if not path.exists():
                self._missing.append(filename)
                log_event(logger, 40, "fonts.missing_file", font=filename, path=str(path))
                continue
            font_id = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            if families:
                self._available[Path(filename).stem] = families[0]
            else:  # pragma: no cover - corrupt font file
                self._missing.append(filename)
                log_event(logger, 40, "fonts.load_failed", font=filename)
        self._loaded = True
        log_event(
            logger,
            20,
            "fonts.loaded",
            families=sorted(self._available.values()),
            missing=self._missing,
        )

    @property
    def missing(self) -> tuple[str, ...]:
        """Font files that could not be loaded."""
        return tuple(self._missing)

    @property
    def ui_family(self) -> str:
        """The family used for interface text (falls back to the system font if unavailable)."""
        return self._available.get("Inter", "Inter")

    @property
    def bengali_family(self) -> str:
        """The family used for Bengali content."""
        return self._available.get("NotoSansBengali", "Noto Sans Bengali")

    def ui_font(self, size_pt: float | None = None, weight: int | None = None) -> QFont:
        """Return a validated UI font at the requested point size and weight."""
        token_typography = tokens().typography
        font = QFont(self.ui_family)
        font.setPointSizeF(size_pt if size_pt is not None else token_typography.size_body)
        font.setWeight(
            QFont.Weight(weight if weight is not None else token_typography.weight_regular)
        )
        font.setFamilies([self.ui_family, self.bengali_family, *token_typography.fallback])
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        return font

    def bengali_font(self, size_pt: float | None = None, weight: int | None = None) -> QFont:
        """Return a font that renders Bengali correctly, with a slightly larger size for legibility."""
        token_typography = tokens().typography
        base = size_pt if size_pt is not None else token_typography.size_body
        font = QFont(self.bengali_family)
        font.setPointSizeF(base + token_typography.bengali_size_bonus)
        font.setWeight(
            QFont.Weight(weight if weight is not None else token_typography.weight_regular)
        )
        font.setFamilies([self.bengali_family, self.ui_family, *token_typography.fallback])
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        return font

    def mono_font(self, size_pt: float | None = None) -> QFont:
        """Return the monospaced font used for codes, amounts and reference numbers."""
        token_typography = tokens().typography
        font = QFont(token_typography.family_mono)
        font.setPointSizeF(size_pt if size_pt is not None else token_typography.size_body)
        font.setFamilies([token_typography.family_mono, "Consolas", "Courier New", "monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font


_registry = FontRegistry()


def ensure_fonts_loaded() -> FontRegistry:
    """Load the bundled fonts (idempotent) and return the registry."""
    _registry.load()
    return _registry


def fonts() -> FontRegistry:
    """Return the font registry (loading fonts on first use)."""
    return ensure_fonts_loaded()


@lru_cache(maxsize=256)
def text_width(text: str, size_pt: float, weight: int = 400, *, bengali: bool = False) -> float:
    """Measure rendered text width in pixels (cached; used by layout calculations)."""
    registry = ensure_fonts_loaded()
    font = (
        registry.bengali_font(size_pt, weight)
        if bengali or contains_bengali(text)
        else registry.ui_font(size_pt, weight)
    )
    return QFontMetricsF(font).horizontalAdvance(text)


def contains_bengali(text: str) -> bool:
    """Return True when *text* contains Bengali script characters."""
    return any("\u0980" <= char <= "\u09ff" for char in text)


def font_for_text(text: str, size_pt: float, weight: int = 400) -> QFont:
    """Return the right font for mixed content: Bengali text gets the Bengali family."""
    registry = ensure_fonts_loaded()
    return (
        registry.bengali_font(size_pt, weight)
        if contains_bengali(text)
        else registry.ui_font(size_pt, weight)
    )


def fonts_healthy() -> bool:
    """Return True when every bundled font loaded (printing is blocked otherwise)."""
    registry = ensure_fonts_loaded()
    return not registry.missing
