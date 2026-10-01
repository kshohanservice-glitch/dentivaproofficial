"""The design token system — the single source of colour, type, spacing and motion values.

Nothing in the interface may hard-code a colour, radius, shadow or spacing value: screens and
components read them from here (directly or through :mod:`dentivapro.ui.design.theme`). A static
quality gate fails the build if a UI file outside this package contains a raw hex colour or a magic
padding number, which is what keeps the interface visually coherent as the product grows.

The palette is a restrained clinical system: deep slate ink, a soft neutral canvas, one teal accent
for primary actions, and semantic colours reserved for clinical and financial meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Palette:
    """The complete colour palette for one theme mode."""

    # Brand / accent
    accent_700: str = "#0B5F59"
    accent_600: str = "#0F766E"
    accent_500: str = "#0D9488"
    accent_200: str = "#99F6E4"
    accent_100: str = "#CCFBF1"
    accent_050: str = "#ECFDF5"
    accent_ink: str = "#0B5F59"

    # Ink (foreground text colours)
    ink_900: str = "#0B1220"
    ink_800: str = "#1B2436"
    ink_700: str = "#334155"
    ink_600: str = "#475569"
    ink_500: str = "#64748B"
    ink_400: str = "#94A3B8"
    ink_300: str = "#CBD5E1"

    # Surfaces
    surface_base: str = "#F6F8FA"
    surface_raised: str = "#FFFFFF"
    surface_sunken: str = "#EEF2F6"
    surface_overlay: str = "#FFFFFF"

    # Borders
    border_subtle: str = "#E2E8F0"
    border_strong: str = "#CBD5E1"
    border_focus: str = "#0D9488"

    # Semantic
    success_fg: str = "#065F46"
    success_bg: str = "#DCFCE7"
    success_border: str = "#A7F3D0"
    warning_fg: str = "#92400E"
    warning_bg: str = "#FEF3C7"
    warning_border: str = "#FDE68A"
    danger_fg: str = "#991B1B"
    danger_bg: str = "#FEE2E2"
    danger_border: str = "#FECACA"
    info_fg: str = "#075985"
    info_bg: str = "#E0F2FE"
    info_border: str = "#BAE6FD"

    # Data visualisation (ordered, colour-blind safe)
    data_1: str = "#0F766E"
    data_2: str = "#334155"
    data_3: str = "#B45309"
    data_4: str = "#6D28D9"
    data_5: str = "#0E7490"
    data_6: str = "#BE123C"

    # States
    disabled_fg: str = "#94A3B8"
    disabled_bg: str = "#F1F5F9"
    focus_ring: str = "#5EEAD4"
    scrim: str = "rgba(11, 18, 32, 0.45)"

    # Shadows (used by theme, expressed as rgba strings)
    shadow_soft: str = "rgba(15, 23, 42, 0.06)"
    shadow_medium: str = "rgba(15, 23, 42, 0.12)"
    shadow_strong: str = "rgba(15, 23, 42, 0.20)"


@dataclass(frozen=True, slots=True)
class Typography:
    """Font families and the type scale (point sizes for the default scale factor)."""

    family_ui: str = "Inter"
    family_bengali: str = "Noto Sans Bengali"
    family_mono: str = "Cascadia Mono"
    fallback: tuple[str, ...] = ("Segoe UI", "Noto Sans", "Arial")

    size_display: float = 21.0
    size_h1: float = 16.5
    size_h2: float = 13.5
    size_h3: float = 11.5
    size_body: float = 10.5
    size_label: float = 9.5
    size_caption: float = 8.5
    size_micro: float = 8.0
    size_amount_lg: float = 15.0

    weight_regular: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    weight_bold: int = 700

    line_height_ratio: float = 1.45
    #: Bengali glyphs need slightly more room; applied centrally, never per screen.
    bengali_size_bonus: float = 0.5
    bengali_line_height_ratio: float = 1.62


@dataclass(frozen=True, slots=True)
class Spacing:
    """The spacing scale in device-independent pixels."""

    xs: int = 4
    sm: int = 6
    md: int = 8
    lg: int = 12
    xl: int = 16
    xxl: int = 20
    xxxl: int = 24
    huge: int = 32
    giant: int = 40
    massive: int = 48

    screen_gutter: int = 20
    card_padding: int = 16
    form_row_gap: int = 12
    table_cell_x: int = 10
    table_cell_y: int = 8


@dataclass(frozen=True, slots=True)
class Radii:
    """Corner radii in pixels."""

    sm: int = 6
    md: int = 8
    lg: int = 10
    xl: int = 14
    pill: int = 999


@dataclass(frozen=True, slots=True)
class Elevation:
    """Shadow definitions (offset-x, offset-y, blur, colour)."""

    card: tuple[int, int, int, str] = (0, 1, 3, "rgba(15, 23, 42, 0.08)")
    raised: tuple[int, int, int, str] = (0, 2, 8, "rgba(15, 23, 42, 0.10)")
    popover: tuple[int, int, int, str] = (0, 6, 18, "rgba(15, 23, 42, 0.16)")
    dialog: tuple[int, int, int, str] = (0, 12, 32, "rgba(15, 23, 42, 0.22)")


@dataclass(frozen=True, slots=True)
class Motion:
    """Animation timings in milliseconds and easing names."""

    fast: int = 120
    base: int = 160
    slow: int = 240
    toast: int = 260
    skeleton_period: int = 1200
    easing: str = "OutCubic"


@dataclass(frozen=True, slots=True)
class Metrics:
    """Control sizes and layout metrics in pixels."""

    control_height_xs: int = 26
    control_height_sm: int = 30
    control_height_md: int = 34
    control_height_lg: int = 40
    input_height: int = 34

    table_row_comfortable: int = 40
    table_row_compact: int = 30
    table_header_height: int = 36
    table_min_column_width: int = 72

    header_height: int = 52
    statusbar_height: int = 26
    sidebar_width: int = 240
    sidebar_collapsed_width: int = 68
    sidebar_item_height: int = 36
    sidebar_section_spacing: int = 14

    icon_sm: int = 14
    icon_md: int = 16
    icon_lg: int = 20
    icon_xl: int = 24

    toast_width: int = 360
    dialog_min_width: int = 380
    form_max_width: int = 720

    scrollbar_width: int = 10
    focus_ring_width: int = 2


@dataclass(frozen=True, slots=True)
class Breakpoints:
    """Viewport widths at which the desktop layout adapts."""

    wide: int = 1600
    standard: int = 1280
    compact: int = 1024
    narrow: int = 900


@dataclass(frozen=True, slots=True)
class DesignTokens:
    """The complete token set for one theme."""

    name: str = "light"
    palette: Palette = field(default_factory=Palette)
    typography: Typography = field(default_factory=Typography)
    spacing: Spacing = field(default_factory=Spacing)
    radii: Radii = field(default_factory=Radii)
    elevation: Elevation = field(default_factory=Elevation)
    motion: Motion = field(default_factory=Motion)
    metrics: Metrics = field(default_factory=Metrics)
    breakpoints: Breakpoints = field(default_factory=Breakpoints)


LIGHT: Final[DesignTokens] = DesignTokens()

#: Semantic aliases used by components so intent, not colour, is referenced in code.
TEXT_PRIMARY: Final[str] = LIGHT.palette.ink_900
TEXT_SECONDARY: Final[str] = LIGHT.palette.ink_600
TEXT_MUTED: Final[str] = LIGHT.palette.ink_500
TEXT_ON_ACCENT: Final[str] = "#FFFFFF"


def tokens() -> DesignTokens:
    """Return the active design tokens."""
    return LIGHT


#: Length of a ``#rrggbb`` colour literal.
_HEX_LENGTH: Final[int] = 6

#: Above this sRGB channel value the gamma curve applies instead of the linear segment.
_SRGB_LINEAR_THRESHOLD: Final[float] = 0.03928


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio between two ``#rrggbb`` colours.

    Used by the design-system tests to prove that text colours remain readable, and by the token lint
    gate to reject a palette change that would break accessibility.
    """

    def _luminance(colour: str) -> float:
        value = colour.lstrip("#")
        if len(value) != _HEX_LENGTH:
            raise ValueError(f"Expected a #rrggbb colour, received {colour!r}")
        channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        adjusted = [
            c / 12.92 if c <= _SRGB_LINEAR_THRESHOLD else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * adjusted[0] + 0.7152 * adjusted[1] + 0.0722 * adjusted[2]

    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
