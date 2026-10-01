"""The design system must be readable, consistent and applied everywhere.

These tests protect the two properties that keep a large interface coherent: the palette keeps
accessible contrast, and no screen styles itself outside the token system.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dentivapro.ui.design.tokens import LIGHT, TEXT_ON_ACCENT, contrast_ratio, tokens

pytestmark = pytest.mark.ui

SRC = Path(__file__).resolve().parents[2] / "src" / "dentivapro"
DESIGN_DIR = SRC / "ui" / "design"

#: Files allowed to contain literal colour values (the design system itself and the icon tool).
COLOUR_ALLOWED = {DESIGN_DIR}


class TestPalette:
    def test_body_text_meets_wcag_aa_on_raised_surfaces(self) -> None:
        palette = LIGHT.palette
        for text_colour in (palette.ink_900, palette.ink_800, palette.ink_700):
            assert contrast_ratio(text_colour, palette.surface_raised) >= 4.5, text_colour
            assert contrast_ratio(text_colour, palette.surface_base) >= 4.5, text_colour

    def test_secondary_text_meets_wcag_aa(self) -> None:
        palette = LIGHT.palette
        assert contrast_ratio(palette.ink_600, palette.surface_raised) >= 4.5

    def test_caption_text_is_legible(self) -> None:
        palette = LIGHT.palette
        # Captions are small, so 4.5:1 is required rather than the 3:1 large-text allowance.
        assert contrast_ratio(palette.ink_500, palette.surface_raised) >= 4.5

    def test_primary_buttons_are_legible(self) -> None:
        palette = LIGHT.palette
        assert contrast_ratio(TEXT_ON_ACCENT, palette.accent_600) >= 4.5
        assert contrast_ratio(TEXT_ON_ACCENT, palette.danger_fg) >= 4.5

    def test_semantic_badges_are_legible(self) -> None:
        palette = LIGHT.palette
        pairs = [
            (palette.success_fg, palette.success_bg),
            (palette.warning_fg, palette.warning_bg),
            (palette.danger_fg, palette.danger_bg),
            (palette.info_fg, palette.info_bg),
            (palette.accent_ink, palette.accent_050),
        ]
        for foreground, background in pairs:
            assert contrast_ratio(foreground, background) >= 4.5, (foreground, background)

    def test_data_colours_are_distinct(self) -> None:
        palette = LIGHT.palette
        series = [
            palette.data_1,
            palette.data_2,
            palette.data_3,
            palette.data_4,
            palette.data_5,
            palette.data_6,
        ]
        assert len(set(series)) == 6


class TestTokens:
    def test_spacing_scale_increases(self) -> None:
        spacing = LIGHT.spacing
        values = [
            spacing.xs,
            spacing.sm,
            spacing.md,
            spacing.lg,
            spacing.xl,
            spacing.xxl,
            spacing.xxxl,
            spacing.huge,
        ]
        assert values == sorted(values)
        assert len(set(values)) == len(values)

    def test_control_heights_are_clickable(self) -> None:
        metrics = LIGHT.metrics
        assert metrics.control_height_xs >= 24
        assert metrics.control_height_sm >= metrics.control_height_xs
        assert metrics.control_height_md >= metrics.control_height_sm
        assert metrics.control_height_lg >= metrics.control_height_md

    def test_table_rows_fit_their_content(self) -> None:
        metrics = LIGHT.metrics
        assert metrics.table_row_compact > metrics.table_header_height - 10
        assert metrics.table_row_comfortable > metrics.table_row_compact

    def test_type_scale_is_ordered_and_readable(self) -> None:
        typography = LIGHT.typography
        assert typography.size_caption >= 8.0
        assert (
            typography.size_micro
            < typography.size_caption
            < typography.size_label
            < typography.size_body
            < typography.size_h3
            < typography.size_h2
            < typography.size_h1
            < typography.size_display
        )

    def test_motion_is_quick_enough_for_clinical_use(self) -> None:
        motion = LIGHT.motion
        assert motion.fast <= 150
        assert motion.base <= 200
        assert motion.slow <= 300

    def test_bengali_needs_more_room_than_latin(self) -> None:
        typography = LIGHT.typography
        assert typography.bengali_size_bonus > 0
        assert typography.bengali_line_height_ratio > typography.line_height_ratio

    def test_breakpoints_are_ordered(self) -> None:
        breakpoints = LIGHT.breakpoints
        assert breakpoints.narrow < breakpoints.compact < breakpoints.standard < breakpoints.wide


class TestStylesheet:
    def test_stylesheet_is_generated_from_tokens(self, qt_app) -> None:
        from dentivapro.ui.design.theme import theme

        stylesheet = theme().stylesheet()
        assert "#0F766E" in stylesheet  # accent from the palette, not a hand-written value
        assert "QPushButton" in stylesheet
        assert "QTableView" in stylesheet

    def test_stylesheet_includes_focus_states(self, qt_app) -> None:
        from dentivapro.ui.design.theme import theme

        stylesheet = theme().stylesheet()
        assert ":focus" in stylesheet
        assert ":disabled" in stylesheet

    def test_stylesheet_styles_required_components(self, qt_app) -> None:
        from dentivapro.ui.design.theme import theme

        stylesheet = theme().stylesheet()
        for selector in (
            "#Header",
            "#Sidebar",
            "#NavButton",
            "#Card",
            "#PrimaryButton",
            "#GhostButton",
            "#DangerButton",
            "#Badge",
            "#Banner",
            "#Toast",
            "#KpiValue",
            "#SearchField",
            "QScrollBar:vertical",
        ):
            assert selector in stylesheet, selector


class TestNoHardCodedStyling:
    """A static gate: screens must not invent colours, so the interface stays coherent."""

    HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
    RGB = re.compile(r"rgba?\(")

    def _ui_files(self) -> list[Path]:
        return [path for path in (SRC / "ui").rglob("*.py") if path.is_file()]

    def test_no_hex_colours_outside_the_design_system(self) -> None:
        offenders: list[str] = []
        for path in self._ui_files():
            if DESIGN_DIR in path.parents:
                continue
            text = path.read_text(encoding="utf-8")
            for match in self.HEX.finditer(text):
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(SRC)}:{line} {match.group(0)}")
        assert not offenders, "colours must come from the design tokens: " + ", ".join(offenders)

    def test_pixel_padding_is_not_hard_coded_in_screens(self) -> None:
        # Zero margins are a deliberate structural reset; any non-zero literal is a spacing defect.
        pattern = re.compile(r"setContentsMargins\(\s*[1-9]\d*\s*,")
        offenders: list[str] = []
        for path in (SRC / "ui" / "screens").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(SRC)}:{line}")
        assert not offenders, "screens must use tokens for spacing: " + ", ".join(offenders)

    def test_font_sizes_come_from_tokens(self) -> None:
        pattern = re.compile(r"setPointSize(F)?\(\s*\d")
        offenders: list[str] = []
        for path in self._ui_files():
            if DESIGN_DIR in path.parents:
                continue
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(SRC)}:{line}")
        assert not offenders, "font sizes must come from the type scale: " + ", ".join(offenders)


class TestBengaliSupport:
    def test_bundled_fonts_load(self, qt_app) -> None:
        from dentivapro.ui.design.fonts import ensure_fonts_loaded, fonts_healthy

        registry = ensure_fonts_loaded()
        assert registry.missing == ()
        assert fonts_healthy() is True
        assert registry.ui_family
        assert registry.bengali_family

    def test_bengali_text_is_detected(self) -> None:
        from dentivapro.ui.design.fonts import contains_bengali

        assert contains_bengali("রহিম উদ্দিন")
        assert contains_bengali("Patient: রহিম")
        assert not contains_bengali("Rahim Uddin")

    def test_bengali_text_gets_a_larger_effective_size(self, qt_app) -> None:
        from dentivapro.ui.design.fonts import ensure_fonts_loaded

        registry = ensure_fonts_loaded()
        latin = registry.ui_font(10.0)
        bengali = registry.bengali_font(10.0)
        assert bengali.pointSizeF() > latin.pointSizeF()

    def test_bengali_conjuncts_render_at_a_measurable_width(self, qt_app) -> None:
        from dentivapro.ui.design.fonts import text_width

        conjuncts = "ক্ষ জ্ঞ ন্ত ষ্ট র্ম ট্র দ্ব প্র ঞ্চ হ্ম"
        assert text_width(conjuncts, 12.0) > 100.0

    def test_currency_symbol_renders(self, qt_app) -> None:
        from dentivapro.ui.design.fonts import text_width

        assert text_width("৳ ১২,৪৫০.৭৫", 12.0) > 40.0


class TestIcons:
    def test_every_required_icon_file_exists(self) -> None:
        from dentivapro.ui.design.icons import check_required_icons

        assert check_required_icons() == []

    def test_icons_render_without_falling_back(self, qt_app) -> None:
        from dentivapro.ui.design.icons import (
            REQUIRED_ICONS,
            icons,
            missing_icons,
            tinted_icon_colors,
        )

        registry = icons()
        colour = tinted_icon_colors()["default"]
        for name in sorted(REQUIRED_ICONS):
            pixmap = registry.pixmap(name, 16, colour)
            assert not pixmap.isNull(), name
            assert pixmap.width() == 16
        assert missing_icons() == frozenset()

    def test_icons_scale_with_the_device_pixel_ratio(self, qt_app) -> None:
        from dentivapro.ui.design.icons import icons, tinted_icon_colors

        registry = icons()
        colour = tinted_icon_colors()["default"]
        for ratio in (1.0, 1.5, 2.0):
            pixmap = registry.pixmap("settings", 16, colour, device_pixel_ratio=ratio)
            assert pixmap.devicePixelRatio() == pytest.approx(ratio)
            assert pixmap.width() == round(16 * ratio)

    def test_icon_colours_come_from_the_palette(self, qt_app) -> None:
        from dentivapro.ui.design.icons import tinted_icon_colors

        colours = tinted_icon_colors()
        assert colours["accent"] == LIGHT.palette.accent_600
        assert colours["danger"] == LIGHT.palette.danger_fg

    def test_unknown_icon_returns_a_visible_placeholder(self, qt_app) -> None:
        from dentivapro.ui.design.icons import icons, tinted_icon_colors

        pixmap = icons().pixmap("__not_an_icon__", 16, tinted_icon_colors()["default"])
        assert not pixmap.isNull()


class TestThemeApplication:
    def test_tokens_singleton_is_used(self) -> None:
        assert tokens() is LIGHT

    def test_application_palette_matches_tokens(self, qt_app) -> None:
        from dentivapro.ui.design.theme import theme

        palette = theme().build_palette()
        assert palette.window().color().name().lower() == LIGHT.palette.surface_base.lower()

    def test_shadow_helper_applies_an_effect(self, qt_app) -> None:
        from PySide6.QtWidgets import QWidget

        from dentivapro.ui.design.theme import theme

        widget = QWidget()
        theme().apply_shadow(widget, "card")
        assert widget.graphicsEffect() is not None
        widget.deleteLater()
