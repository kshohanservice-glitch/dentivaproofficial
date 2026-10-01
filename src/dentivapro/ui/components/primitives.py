"""Primitive interface elements built on the design tokens.

Every control used by the product is defined once here so that spacing, colour, focus behaviour and
keyboard handling stay consistent, and so a change to the design system propagates everywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dentivapro.ui.design.fonts import contains_bengali, font_for_text
from dentivapro.ui.design.icons import icon, tinted_icon_colors
from dentivapro.ui.design.theme import theme
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:
    from collections.abc import Callable

ButtonVariant = Literal["primary", "secondary", "ghost", "danger", "link", "icon"]

_OBJECT_NAMES: dict[str, str] = {
    "primary": "PrimaryButton",
    "secondary": "SecondaryButton",
    "ghost": "GhostButton",
    "danger": "DangerButton",
    "link": "LinkButton",
    "icon": "IconButton",
}


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------


class Text(QLabel):
    """A label with a semantic type role and correct Bengali font selection."""

    def __init__(
        self,
        text: str = "",
        *,
        role: str = "body",
        object_name: str | None = None,
        word_wrap: bool = False,
        selectable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(object_name or _ROLE_OBJECT_NAMES.get(role, "TextBody"))
        self.setWordWrap(word_wrap)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            if selectable
            else Qt.TextInteractionFlag.NoTextInteraction
        )
        self._apply_font()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt naming
        super().setText(text)
        self._apply_font()

    def _apply_font(self) -> None:
        base = self.font().pointSizeF() or tokens().typography.size_body
        self.setFont(font_for_text(self.text(), base, self.font().weight()))

    def set_tone(self, role: str) -> None:
        """Switch the semantic role (updates the object name used by the stylesheet)."""
        self.setObjectName(_ROLE_OBJECT_NAMES.get(role, "TextBody"))
        style = self.style()
        if style is not None:  # pragma: no cover - Qt internal refresh
            style.unpolish(self)
            style.polish(self)


_ROLE_OBJECT_NAMES: dict[str, str] = {
    "display": "TextDisplay",
    "h1": "TextH1",
    "h2": "TextH2",
    "h3": "TextH3",
    "body": "TextBody",
    "secondary": "TextSecondary",
    "caption": "TextCaption",
    "label": "TextLabel",
    "mono": "TextMono",
    "amount": "TextAmount",
    "kpi_value": "KpiValue",
    "kpi_label": "KpiLabel",
}


def elide_text(text: str, max_chars: int = 60) -> str:
    """Shorten *text* for compact contexts, keeping words intact where possible."""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rstrip()
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


# ---------------------------------------------------------------------------
# Structural elements
# ---------------------------------------------------------------------------


class Divider(QFrame):
    """A one-pixel horizontal divider."""

    def __init__(self, *, vertical: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("VerticalDivider" if vertical else "Divider")
        if vertical:
            self.setFixedWidth(1)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setFixedHeight(1)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def spacer(width: int | None = None, height: int | None = None) -> QWidget:
    """Return a flexible or fixed spacer widget."""
    widget = QWidget()
    if width is not None:
        widget.setFixedWidth(width)
    if height is not None:
        widget.setFixedHeight(height)
    if width is None and height is None:
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return widget


class Badge(QLabel):
    """A small status chip."""

    def __init__(
        self,
        text: str,
        *,
        variant: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.setProperty("variant", variant)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


class IconLabel(QLabel):
    """A label that renders a themed icon (used in empty states and headers)."""

    def __init__(
        self,
        name: str,
        *,
        size: int = 20,
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StateIcon")
        self.setFixedSize(size, size)
        self.setPixmap(
            icon(name, size, color or tinted_icon_colors()["muted"]).pixmap(QSize(size, size))
        )


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


def make_button(
    text: str,
    *,
    variant: ButtonVariant = "secondary",
    icon_name: str | None = None,
    tooltip: str = "",
    shortcut: str | None = None,
    on_click: Callable[[], None] | None = None,
    enabled: bool = True,
    checkable: bool = False,
    parent: QWidget | None = None,
) -> QPushButton:
    """Create a themed button.

    When *enabled* is False the button is genuinely disabled (not clickable) and the tooltip explains
    why — the product never shows a control that silently does nothing.
    """
    button = QPushButton(text, parent)
    button.setObjectName(_OBJECT_NAMES[variant])
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setEnabled(enabled)
    button.setCheckable(checkable)
    if icon_name:
        button.setIcon(icon(icon_name, tokens().metrics.icon_md, _icon_color(variant)))
        button.setIconSize(QSize(tokens().metrics.icon_md, tokens().metrics.icon_md))
    if tooltip:
        button.setToolTip(tooltip)
    if shortcut:
        button.setShortcut(QKeySequence(shortcut))
        button.setToolTip(f"{tooltip + '  ' if tooltip else ''}({shortcut})")
    if on_click is not None:
        button.clicked.connect(on_click)
    if contains_bengali(text):
        button.setFont(font_for_text(text, tokens().typography.size_body))
    return button


def _icon_color(variant: ButtonVariant) -> str:
    colours = tinted_icon_colors()
    return colours["on_accent"] if variant in ("primary", "danger") else colours["default"]


def make_icon_button(
    icon_name: str,
    *,
    tooltip: str,
    on_click: Callable[[], None] | None = None,
    size: int | None = None,
    enabled: bool = True,
    checkable: bool = False,
    checked: bool = False,
    color: str | None = None,
    parent: QWidget | None = None,
) -> QToolButton:
    """Create a square icon-only button with a mandatory tooltip (accessibility requirement)."""
    resolved_size = size or tokens().metrics.control_height_md
    button = QToolButton(parent)
    button.setObjectName("IconButton")
    button.setIcon(icon(icon_name, tokens().metrics.icon_lg, color))
    button.setIconSize(QSize(tokens().metrics.icon_lg, tokens().metrics.icon_lg))
    button.setFixedSize(resolved_size, resolved_size)
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setEnabled(enabled)
    button.setCheckable(checkable)
    button.setChecked(checked)
    button.setAutoRaise(True)
    if on_click is not None:
        button.clicked.connect(on_click)
    return button


def make_menu_action(
    menu: QMenu,
    text: str,
    *,
    icon_name: str | None = None,
    enabled: bool = True,
    tooltip: str = "",
    on_trigger: Callable[[], None] | None = None,
) -> QAction:
    """Add an action to a menu, with an honest tooltip when the action is unavailable."""
    action = QAction(text, menu)
    if icon_name:
        action.setIcon(icon(icon_name, tokens().metrics.icon_md, tinted_icon_colors()["default"]))
    action.setEnabled(enabled)
    if tooltip:
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
    if on_trigger is not None:
        action.triggered.connect(lambda _checked=False: on_trigger())
    menu.addAction(action)
    return action


# ---------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------


class SearchField(QLineEdit):
    """A debounced search input with a leading icon and a clear button."""

    search_requested = Signal(str)

    def __init__(
        self,
        placeholder: str = "Search",
        *,
        debounce_ms: int = 200,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SearchField")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(220)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._emit_search)
        self.textChanged.connect(lambda _text: self._timer.start())
        self.returnPressed.connect(self._emit_search_immediate)
        self._leading_icon = QLabel(self)
        self._leading_icon.setPixmap(
            icon("search", tokens().metrics.icon_md, tinted_icon_colors()["muted"]).pixmap(
                QSize(tokens().metrics.icon_md, tokens().metrics.icon_md)
            )
        )
        self._leading_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._leading_icon.move(tokens().spacing.md, 9)

    def _emit_search(self) -> None:
        self.search_requested.emit(self.text().strip())

    def _emit_search_immediate(self) -> None:
        self._timer.stop()
        self._emit_search()

    def set_error(self, has_error: bool) -> None:
        """Mark the field as invalid (used by form validation)."""
        self.setProperty("state", "error" if has_error else "")
        style = self.style()
        if style is not None:  # pragma: no cover - Qt internal refresh
            style.unpolish(self)
            style.polish(self)


class ComboField(QComboBox):
    """A combo box that carries an optional value distinct from its display text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(tokens().metrics.input_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def add_option(self, label: str, value: object | None = None) -> None:
        """Add an option, storing *value* as item data (defaults to the label)."""
        self.addItem(label, label if value is None else value)

    def current_value(self) -> object:
        """Return the value stored in the current item."""
        data = self.currentData()
        return self.currentText() if data is None else data


def field_row(
    label: str, field: QWidget, *, hint: str = "", parent: QWidget | None = None
) -> QWidget:
    """Return a labelled form row (label above the field, hint below)."""
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(tokens().spacing.xs)
    caption = Text(label, role="label")
    layout.addWidget(caption)
    layout.addWidget(field)
    if hint:
        layout.addWidget(Text(hint, role="caption", word_wrap=True))
    return container


def hstack(
    *widgets: QWidget,
    spacing: int | None = None,
    margins: tuple[int, int, int, int] | None = None,
) -> QWidget:
    """Pack widgets horizontally into a container."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setSpacing(tokens().spacing.md if spacing is None else spacing)
    if margins is None:
        layout.setContentsMargins(0, 0, 0, 0)
    else:
        layout.setContentsMargins(*margins)
    for widget in widgets:
        layout.addWidget(widget)
    return container


def vstack(
    *widgets: QWidget,
    spacing: int | None = None,
    margins: tuple[int, int, int, int] | None = None,
) -> QWidget:
    """Pack widgets vertically into a container."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setSpacing(tokens().spacing.md if spacing is None else spacing)
    if margins is None:
        layout.setContentsMargins(0, 0, 0, 0)
    else:
        layout.setContentsMargins(*margins)
    for widget in widgets:
        layout.addWidget(widget)
    return container


def styled_separator(parent: QWidget | None = None) -> QFrame:
    """Return a horizontal separator with the theme's divider colour."""
    separator = QFrame(parent)
    separator.setObjectName("Divider")
    separator.setFixedHeight(1)
    separator.setStyleSheet(f"background-color: {theme().colour('border_subtle')};")
    return separator
