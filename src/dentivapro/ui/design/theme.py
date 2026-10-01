"""The Qt stylesheet and palette generated from the design tokens.

Every widget in the application is styled from this single stylesheet. Components set an
``objectName`` or a dynamic property (for example ``variant="primary"``) and the stylesheet answers —
no screen writes its own colours, and a change to the tokens restyles the whole product consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

from dentivapro.ui.design.fonts import ensure_fonts_loaded
from dentivapro.ui.design.tokens import DesignTokens, tokens


@dataclass(frozen=True, slots=True)
class Theme:
    """Applies the design tokens to a Qt application."""

    tokens: DesignTokens

    # ---- palette ---------------------------------------------------------
    def colour(self, name: str) -> str:
        """Return a palette colour by attribute name (e.g. ``accent_600``)."""
        return str(getattr(self.tokens.palette, name))

    def qcolor(self, name: str) -> QColor:
        """Return a palette colour as a :class:`QColor`."""
        return QColor(self.colour(name))

    # ---- application ------------------------------------------------------
    def apply(self, app: QApplication) -> None:
        """Install the palette and stylesheet on the application."""
        ensure_fonts_loaded()
        app.setStyle("Fusion")
        app.setPalette(self.build_palette())
        app.setStyleSheet(self.stylesheet())
        base_font = QFont(self.tokens.typography.family_ui)
        base_font.setPointSizeF(self.tokens.typography.size_body)
        app.setFont(base_font)

    def build_palette(self) -> QPalette:
        """Build a Qt palette that matches the tokens (used by native dialogs and menus)."""
        palette = self.tokens.palette
        qt_palette = QPalette()
        qt_palette.setColor(QPalette.ColorRole.Window, QColor(palette.surface_base))
        qt_palette.setColor(QPalette.ColorRole.WindowText, QColor(palette.ink_900))
        qt_palette.setColor(QPalette.ColorRole.Base, QColor(palette.surface_raised))
        qt_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.surface_sunken))
        qt_palette.setColor(QPalette.ColorRole.Text, QColor(palette.ink_900))
        qt_palette.setColor(QPalette.ColorRole.Button, QColor(palette.surface_raised))
        qt_palette.setColor(QPalette.ColorRole.ButtonText, QColor(palette.ink_800))
        qt_palette.setColor(QPalette.ColorRole.Highlight, QColor(palette.accent_600))
        qt_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        qt_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(palette.ink_900))
        qt_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
        qt_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(palette.ink_400))
        qt_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(palette.disabled_fg)
        )
        qt_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(palette.disabled_fg)
        )
        return qt_palette

    # ---- stylesheet --------------------------------------------------------
    @lru_cache(maxsize=4)  # noqa: B019 - a single theme instance per process
    def stylesheet(self) -> str:
        """Build the complete application stylesheet from the tokens."""
        t = self.tokens
        p = t.palette
        ty = t.typography
        m = t.metrics
        r = t.radii

        ui_font_stack = f'"{ty.family_ui}", "{ty.family_bengali}", ' + ", ".join(
            f'"{family}"' for family in ty.fallback
        )

        return f"""
/* ===================================================================== *
 *  Dentiva Pro — generated from design tokens. Do not edit by hand.     *
 * ===================================================================== */

QWidget {{
    font-family: {ui_font_stack};
    font-size: {ty.size_body}pt;
    color: {p.ink_900};
    background-color: transparent;
}}

QMainWindow, QDialog, #AppShell {{
    background-color: {p.surface_base};
}}

/* ---- header ------------------------------------------------------- */
#Header {{
    background-color: {p.surface_raised};
    border-bottom: 1px solid {p.border_subtle};
}}
#HeaderBrand {{
    font-size: {ty.size_h1}pt;
    font-weight: {ty.weight_bold};
    color: {p.ink_900};
}}
#HeaderClinic {{
    font-size: {ty.size_body}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_700};
}}
#HeaderClinicMeta, #HeaderDate {{
    font-size: {ty.size_caption}pt;
    color: {p.ink_500};
}}
#HeaderSeparator {{
    background-color: {p.border_subtle};
}}

/* ---- sidebar ------------------------------------------------------ */
#Sidebar {{
    background-color: {p.surface_raised};
    border-right: 1px solid {p.border_subtle};
}}
#SidebarSectionLabel {{
    font-size: {ty.size_micro}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_400};
    letter-spacing: 0.08em;
    padding: 0px {t.spacing.md}px;
}}
#NavButton {{
    text-align: left;
    padding: 0px {t.spacing.md}px;
    margin: 1px {t.spacing.sm}px;
    border: none;
    border-radius: {r.md}px;
    background-color: transparent;
    color: {p.ink_700};
    font-size: {ty.size_body}pt;
    font-weight: {ty.weight_medium};
}}
#NavButton:hover {{
    background-color: {p.surface_sunken};
    color: {p.ink_900};
}}
#NavButton:checked {{
    background-color: {p.accent_050};
    color: {p.accent_ink};
    font-weight: {ty.weight_semibold};
}}
#NavButton:disabled {{
    color: {p.disabled_fg};
}}
#NavButton:focus {{
    outline: none;
    border: 1px solid {p.accent_200};
}}
#NavActiveBar {{
    background-color: {p.accent_600};
    border-radius: 2px;
}}
#SidebarFooter {{
    color: {p.ink_400};
    font-size: {ty.size_micro}pt;
}}

/* ---- cards --------------------------------------------------------- */
#Card {{
    background-color: {p.surface_raised};
    border: 1px solid {p.border_subtle};
    border-radius: {r.lg}px;
}}
#CardHeader {{
    border-bottom: 1px solid {p.border_subtle};
}}
#CardTitle {{
    font-size: {ty.size_h3}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_900};
}}
#CardSubtitle {{
    font-size: {ty.size_caption}pt;
    color: {p.ink_500};
}}
#CardFooter {{
    border-top: 1px solid {p.border_subtle};
    background-color: {p.surface_base};
    border-bottom-left-radius: {r.lg}px;
    border-bottom-right-radius: {r.lg}px;
}}
#KpiValue {{
    font-size: {ty.size_amount_lg}pt;
    font-weight: {ty.weight_bold};
    color: {p.ink_900};
}}
#KpiLabel {{
    font-size: {ty.size_label}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_500};
    letter-spacing: 0.02em;
}}
#KpiHint {{
    font-size: {ty.size_caption}pt;
    color: {p.ink_500};
}}

/* ---- typography helpers -------------------------------------------- */
#TextDisplay {{
    font-size: {ty.size_display}pt;
    font-weight: {ty.weight_bold};
    color: {p.ink_900};
}}
#TextH1 {{
    font-size: {ty.size_h1}pt;
    font-weight: {ty.weight_bold};
    color: {p.ink_900};
}}
#TextH2 {{
    font-size: {ty.size_h2}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_800};
}}
#TextH3 {{
    font-size: {ty.size_h3}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_800};
}}
#TextLabel {{
    font-size: {ty.size_label}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_600};
}}
#TextBody {{
    font-size: {ty.size_body}pt;
    color: {p.ink_800};
}}
#TextSecondary {{
    font-size: {ty.size_body}pt;
    color: {p.ink_600};
}}
#TextCaption {{
    font-size: {ty.size_caption}pt;
    color: {p.ink_500};
}}
#TextMono {{
    font-family: "{ty.family_mono}", "Consolas", "Courier New", monospace;
    font-size: {ty.size_body}pt;
    color: {p.ink_800};
}}
#TextAmount {{
    font-family: "{ty.family_mono}", "Consolas", monospace;
    font-size: {ty.size_body}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_900};
}}
#ScreenTitle {{
    font-size: {ty.size_h1}pt;
    font-weight: {ty.weight_bold};
    color: {p.ink_900};
}}
#ScreenSubtitle {{
    font-size: {ty.size_body}pt;
    color: {p.ink_500};
}}

/* ---- buttons -------------------------------------------------------- */
QPushButton {{
    background-color: {p.surface_raised};
    color: {p.ink_800};
    border: 1px solid {p.border_strong};
    border-radius: {r.md}px;
    padding: 0px {t.spacing.lg}px;
    min-height: {m.control_height_md}px;
    font-size: {ty.size_body}pt;
    font-weight: {ty.weight_medium};
}}
QPushButton:hover {{
    background-color: {p.surface_sunken};
    border-color: {p.ink_400};
}}
QPushButton:pressed {{
    background-color: {p.surface_sunken};
    border-color: {p.ink_500};
}}
QPushButton:focus {{
    outline: none;
    border: {m.focus_ring_width}px solid {p.border_focus};
}}
QPushButton:disabled {{
    background-color: {p.disabled_bg};
    color: {p.disabled_fg};
    border-color: {p.border_subtle};
}}
#PrimaryButton {{
    background-color: {p.accent_600};
    color: #FFFFFF;
    border: 1px solid {p.accent_600};
    font-weight: {ty.weight_semibold};
}}
#PrimaryButton:hover {{ background-color: {p.accent_700}; border-color: {p.accent_700}; }}
#PrimaryButton:pressed {{ background-color: {p.accent_700}; }}
#PrimaryButton:disabled {{
    background-color: {p.disabled_bg};
    color: {p.disabled_fg};
    border-color: {p.border_subtle};
}}
#SecondaryButton {{
    background-color: {p.surface_raised};
    color: {p.accent_ink};
    border: 1px solid {p.accent_200};
}}
#SecondaryButton:hover {{ background-color: {p.accent_050}; }}
#GhostButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {p.ink_600};
}}
#GhostButton:hover {{ background-color: {p.surface_sunken}; color: {p.ink_900}; }}
#DangerButton {{
    background-color: {p.danger_fg};
    color: #FFFFFF;
    border: 1px solid {p.danger_fg};
    font-weight: {ty.weight_semibold};
}}
#DangerButton:hover {{ background-color: #7F1D1D; }}
#LinkButton {{
    background: transparent;
    border: none;
    color: {p.accent_600};
    padding: 0px {t.spacing.xs}px;
    min-height: {m.control_height_xs}px;
    font-weight: {ty.weight_semibold};
}}
#LinkButton:hover {{ color: {p.accent_700}; text-decoration: underline; }}
#IconButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: {r.md}px;
    padding: 0px;
}}
#IconButton:hover {{ background-color: {p.surface_sunken}; }}
#IconButton:pressed {{ background-color: {p.border_subtle}; }}
#IconButton:checked {{ background-color: {p.accent_050}; }}

/* ---- inputs ---------------------------------------------------------- */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {p.surface_raised};
    border: 1px solid {p.border_strong};
    border-radius: {r.md}px;
    padding: {t.spacing.xs}px {t.spacing.md}px;
    min-height: {m.input_height - 12}px;
    selection-background-color: {p.accent_100};
    selection-color: {p.ink_900};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
    border: {m.focus_ring_width}px solid {p.border_focus};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
    background-color: {p.disabled_bg};
    color: {p.disabled_fg};
    border-color: {p.border_subtle};
}}
QLineEdit[state="error"], QComboBox[state="error"], QSpinBox[state="error"],
QDoubleSpinBox[state="error"], QDateEdit[state="error"] {{
    border: 1px solid {p.danger_fg};
}}
QLineEdit[state="ok"], QComboBox[state="ok"] {{
    border: 1px solid {p.success_fg};
}}
#SearchField {{
    padding-left: {t.spacing.huge}px;
    background-color: {p.surface_sunken};
    border: 1px solid {p.border_subtle};
}}
#SearchField:focus {{
    background-color: {p.surface_raised};
    border: {m.focus_ring_width}px solid {p.border_focus};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.surface_raised};
    border: 1px solid {p.border_subtle};
    selection-background-color: {p.accent_050};
    selection-color: {p.accent_ink};
    outline: none;
}}
QCheckBox, QRadioButton {{
    spacing: {t.spacing.md}px;
    color: {p.ink_800};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p.border_strong};
    background-color: {p.surface_raised};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {p.accent_600};
    border-color: {p.accent_600};
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: {p.disabled_bg};
    border-color: {p.border_subtle};
}}

/* ---- tables ----------------------------------------------------------- */
QTableView, QTreeView, QListView {{
    background-color: {p.surface_raised};
    alternate-background-color: {p.surface_base};
    border: 1px solid {p.border_subtle};
    border-radius: {r.lg}px;
    gridline-color: {p.border_subtle};
    selection-background-color: {p.accent_050};
    selection-color: {p.ink_900};
    outline: none;
}}
QTableView::item, QTreeView::item, QListView::item {{
    padding: {t.spacing.xs}px {t.spacing.md}px;
    border: none;
}}
QTableView::item:hover, QListView::item:hover {{ background-color: {p.surface_sunken}; }}
QTableView::item:selected, QListView::item:selected {{
    background-color: {p.accent_050};
    color: {p.ink_900};
}}
QHeaderView {{ background-color: {p.surface_sunken}; }}
QHeaderView::section {{
    background-color: {p.surface_sunken};
    color: {p.ink_600};
    font-size: {ty.size_label}pt;
    font-weight: {ty.weight_semibold};
    padding: {t.spacing.md}px {t.spacing.md}px;
    border: none;
    border-bottom: 1px solid {p.border_subtle};
    border-right: 1px solid {p.border_subtle};
}}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{
    background-color: {p.surface_sunken};
    border: none;
    border-bottom: 1px solid {p.border_subtle};
}}
#TableEmptyState {{
    color: {p.ink_500};
    font-size: {ty.size_body}pt;
}}

/* ---- tabs, menus, dialogs --------------------------------------------- */
QTabWidget::pane {{
    border: 1px solid {p.border_subtle};
    border-radius: {r.lg}px;
    background-color: {p.surface_raised};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {p.ink_600};
    padding: {t.spacing.md}px {t.spacing.xl}px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: {ty.weight_medium};
}}
QTabBar::tab:hover {{ color: {p.ink_900}; }}
QTabBar::tab:selected {{
    color: {p.accent_ink};
    border-bottom: 2px solid {p.accent_600};
    font-weight: {ty.weight_semibold};
}}
QMenu {{
    background-color: {p.surface_raised};
    border: 1px solid {p.border_subtle};
    border-radius: {r.md}px;
    padding: {t.spacing.xs}px;
}}
QMenu::item {{
    padding: {t.spacing.md}px {t.spacing.xxl}px {t.spacing.md}px {t.spacing.lg}px;
    border-radius: {r.sm}px;
    color: {p.ink_800};
}}
QMenu::item:selected {{ background-color: {p.accent_050}; color: {p.accent_ink}; }}
QMenu::item:disabled {{ color: {p.disabled_fg}; }}
QMenu::separator {{ height: 1px; background: {p.border_subtle}; margin: {t.spacing.xs}px 0; }}
QToolTip {{
    background-color: {p.ink_900};
    color: #FFFFFF;
    border: none;
    border-radius: {r.sm}px;
    padding: {t.spacing.sm}px {t.spacing.md}px;
    font-size: {ty.size_caption}pt;
}}

/* ---- scrollbars -------------------------------------------------------- */
QScrollBar:vertical {{
    background: transparent;
    width: {m.scrollbar_width}px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {p.ink_300};
    min-height: 32px;
    border-radius: {m.scrollbar_width // 2}px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.ink_400}; }}
QScrollBar:horizontal {{
    background: transparent;
    height: {m.scrollbar_width}px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {p.ink_300};
    min-width: 32px;
    border-radius: {m.scrollbar_width // 2}px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p.ink_400}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- scroll areas ------------------------------------------------------ */
QScrollArea {{ border: none; background-color: transparent; }}
QScrollArea > QWidget > QWidget {{ background-color: transparent; }}

/* ---- badges and banners ------------------------------------------------ */
#Badge {{
    border-radius: {r.pill}px;
    padding: 2px {t.spacing.md}px;
    font-size: {ty.size_micro}pt;
    font-weight: {ty.weight_semibold};
    background-color: {p.surface_sunken};
    color: {p.ink_600};
}}
#Badge[variant="success"] {{ background-color: {p.success_bg}; color: {p.success_fg}; }}
#Badge[variant="warning"] {{ background-color: {p.warning_bg}; color: {p.warning_fg}; }}
#Badge[variant="danger"] {{ background-color: {p.danger_bg}; color: {p.danger_fg}; }}
#Badge[variant="info"] {{ background-color: {p.info_bg}; color: {p.info_fg}; }}
#Badge[variant="accent"] {{ background-color: {p.accent_050}; color: {p.accent_ink}; }}

#Banner {{
    border-radius: {r.lg}px;
    border: 1px solid {p.border_subtle};
    background-color: {p.surface_sunken};
}}
#Banner[variant="info"] {{ background-color: {p.info_bg}; border-color: {p.info_border}; }}
#Banner[variant="warning"] {{ background-color: {p.warning_bg}; border-color: {p.warning_border}; }}
#Banner[variant="danger"] {{ background-color: {p.danger_bg}; border-color: {p.danger_border}; }}
#Banner[variant="success"] {{ background-color: {p.success_bg}; border-color: {p.success_border}; }}
#BannerTitle {{
    font-size: {ty.size_h3}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_900};
}}
#BannerBody {{
    font-size: {ty.size_body}pt;
    color: {p.ink_700};
}}

/* ---- toasts ------------------------------------------------------------ */
#Toast {{
    background-color: {p.surface_raised};
    border: 1px solid {p.border_subtle};
    border-left: 3px solid {p.accent_600};
    border-radius: {r.lg}px;
}}
#Toast[variant="success"] {{ border-left-color: {p.success_fg}; }}
#Toast[variant="warning"] {{ border-left-color: {p.warning_fg}; }}
#Toast[variant="danger"] {{ border-left-color: {p.danger_fg}; }}
#Toast[variant="info"] {{ border-left-color: {p.info_fg}; }}
#ToastTitle {{ font-weight: {ty.weight_semibold}; color: {p.ink_900}; }}
#ToastBody {{ color: {p.ink_600}; }}

/* ---- misc -------------------------------------------------------------- */
#Divider {{ background-color: {p.border_subtle}; }}
#StateTitle {{
    font-size: {ty.size_h2}pt;
    font-weight: {ty.weight_semibold};
    color: {p.ink_800};
}}
#StateBody {{
    font-size: {ty.size_body}pt;
    color: {p.ink_500};
}}
#StateIcon {{ color: {p.ink_400}; }}
#EmptyStateIcon {{ color: {p.ink_300}; }}

QProgressBar {{
    background-color: {p.surface_sunken};
    border: none;
    border-radius: {r.sm}px;
    height: 6px;
    text-align: center;
    color: {p.ink_600};
    font-size: {ty.size_micro}pt;
}}
QProgressBar::chunk {{
    background-color: {p.accent_600};
    border-radius: {r.sm}px;
}}

QSplitter::handle {{ background-color: {p.border_subtle}; }}
QStatusBar {{
    background-color: {p.surface_raised};
    border-top: 1px solid {p.border_subtle};
    color: {p.ink_500};
    font-size: {ty.size_caption}pt;
}}
QFrame#HeaderDivider, QFrame#VerticalDivider {{ background-color: {p.border_subtle}; }}
"""

    # ---- helpers -----------------------------------------------------------
    def apply_shadow(self, widget: QWidget, level: str = "card") -> None:
        """Apply a token-defined drop shadow to a widget (QSS cannot express shadows)."""
        offset_x, offset_y, blur, colour = getattr(self.tokens.elevation, level)
        effect = QGraphicsDropShadowEffect(widget)
        effect.setOffset(offset_x, offset_y)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(colour) if colour.startswith("#") else _parse_rgba(colour))
        widget.setGraphicsEffect(effect)


#: Number of channels in an ``rgba(r, g, b, a)`` value.
_RGBA_CHANNELS: Final[int] = 4


def _parse_rgba(value: str) -> QColor:
    """Parse ``rgba(r, g, b, a)`` into a :class:`QColor`."""
    parts = value[value.index("(") + 1 : value.rindex(")")].split(",")
    red, green, blue = (int(float(part.strip())) for part in parts[: _RGBA_CHANNELS - 1])
    alpha = float(parts[_RGBA_CHANNELS - 1].strip()) if len(parts) >= _RGBA_CHANNELS else 1.0
    return QColor(red, green, blue, int(alpha * 255))


_active_theme: Theme | None = None


def theme() -> Theme:
    """Return the active theme (created from the current tokens on first use)."""
    global _active_theme  # noqa: PLW0603 - a single process-wide theme
    if _active_theme is None:
        _active_theme = Theme(tokens())
    return _active_theme


def apply_theme(app: QApplication) -> Theme:
    """Apply the design system to a Qt application and return the theme."""
    active = theme()
    active.apply(app)
    return active
