"""The collapsible left navigation.

Entries are generated from :mod:`dentivapro.ui.shell.navigation`, filtered by the permission set in
effect, and grouped into the four areas required by the product: Practice, Clinical, Billing and
Administration. The collapsed state shows icons only, with tooltips, and the choice is remembered per
user once settings persistence is available.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.i18n import t
from dentivapro.domain.permissions import DEVELOPMENT_PREVIEW, PermissionSet
from dentivapro.ui.design.icons import icon, tinted_icon_colors
from dentivapro.ui.design.tokens import tokens
from dentivapro.ui.shell.navigation import NAV_SECTIONS, NavEntry, all_entries


@dataclass(frozen=True, slots=True)
class NavItem:
    """A rendered navigation entry."""

    entry: NavEntry
    button: QPushButton


class Sidebar(QWidget):
    """Permission-aware, collapsible navigation rail."""

    route_selected = Signal(str)
    collapsed_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None, *, collapsed: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._collapsed = collapsed
        self._permissions: PermissionSet = DEVELOPMENT_PREVIEW
        self._items: list[NavItem] = []
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, tokens().spacing.lg, 0, tokens().spacing.md)
        layout.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setViewportMargins(0, 0, 0, 0)

        self._content = QWidget(self._scroll)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        self._build_content()
        self._build_footer(layout)
        self.apply_collapsed(collapsed, notify=False)

    # ---- construction -----------------------------------------------------
    def _build_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = None if item is None else item.widget()
            if widget is not None:
                widget.deleteLater()
        self._items.clear()
        self._buttons.clear()

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for section in NAV_SECTIONS:
            section_label = QLabel(t(section.label_key).upper(), self._content)
            section_label.setObjectName("SidebarSectionLabel")
            self._content_layout.addWidget(section_label)

            for entry in section.entries:
                if not self._visible_for(entry):
                    continue
                button = self._make_nav_button(entry)
                self._content_layout.addWidget(button)
                self._group.addButton(button)
                self._items.append(NavItem(entry=entry, button=button))
                self._buttons[entry.route] = button

            spacer = QWidget(self._content)
            spacer.setFixedHeight(tokens().metrics.sidebar_section_spacing)
            self._content_layout.addWidget(spacer)

        self._content_layout.addStretch(1)

    @staticmethod
    def _button_label(entry: NavEntry) -> str:
        """The label as Qt must receive it.

        Qt reads ``&`` in a button's text as a mnemonic marker and draws the following character
        underlined, so "Staff & Users" would render as "Staff _Users". Escaping the ampersand keeps the
        label exactly as written in the translation files.
        """
        return t(entry.label_key).replace("&", "&&")

    def _make_nav_button(self, entry: NavEntry) -> QPushButton:
        label = self._button_label(entry)
        tooltip_label = t(entry.label_key)
        button = QPushButton(label, self._content)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(tokens().metrics.sidebar_item_height)
        button.setIcon(icon(entry.icon, tokens().metrics.icon_lg, tinted_icon_colors()["muted"]))
        button.setIconSize(QSize(tokens().metrics.icon_lg, tokens().metrics.icon_lg))
        tooltip = tooltip_label
        if not entry.implemented and entry.phase:
            tooltip = f"{tooltip_label} — development state ({entry.phase})"
        button.setToolTip(tooltip)
        button.clicked.connect(
            lambda _checked=False, route=entry.route: self.route_selected.emit(route)
        )
        return button

    def _build_footer(self, layout: QVBoxLayout) -> None:
        divider = QFrame(self)
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        footer_row = QWidget(self)
        footer_row.setObjectName("SidebarFooter")
        row_layout = QHBoxLayout(footer_row)
        row_layout.setContentsMargins(
            tokens().spacing.md, tokens().spacing.md, tokens().spacing.sm, 0
        )
        row_layout.setSpacing(tokens().spacing.xs)

        self._mode_label = QLabel(t("foundation.mode_label"), footer_row)
        self._mode_label.setObjectName("SidebarFooter")
        row_layout.addWidget(self._mode_label)
        row_layout.addStretch(1)
        layout.addWidget(footer_row)

    # ---- state -------------------------------------------------------------
    def _visible_for(self, entry: NavEntry) -> bool:
        if entry.permission is None:
            return True
        return self._permissions.allows(entry.permission)

    def set_permissions(self, permissions: PermissionSet) -> None:
        """Rebuild the navigation for a permission set (e.g. after sign-in)."""
        self._permissions = permissions
        current = self.current_route
        self._build_content()
        self.apply_collapsed(self._collapsed, notify=False)
        if current:
            self.set_current_route(current)

    @property
    def permissions(self) -> PermissionSet:
        """The permission set currently driving visibility."""
        return self._permissions

    @property
    def visible_routes(self) -> list[str]:
        """Routes currently shown in the sidebar."""
        return [item.entry.route for item in self._items]

    @property
    def current_route(self) -> str | None:
        """The currently highlighted route."""
        for route, button in self._buttons.items():
            if button.isChecked():
                return route
        return None

    def set_current_route(self, route: str) -> None:
        """Highlight a route (also un-highlights when the route is not in the sidebar)."""
        for candidate, button in self._buttons.items():
            button.setChecked(candidate == route)

    @property
    def is_collapsed(self) -> bool:
        """True when the sidebar renders icons only."""
        return self._collapsed

    def toggle_collapsed(self) -> None:
        """Collapse or expand the sidebar."""
        self.apply_collapsed(not self._collapsed)

    def apply_collapsed(self, collapsed: bool, *, notify: bool = True) -> None:
        """Apply a collapsed/expanded state to width, labels and tooltips."""
        self._collapsed = collapsed
        metrics = tokens().metrics
        self.setFixedWidth(metrics.sidebar_collapsed_width if collapsed else metrics.sidebar_width)
        for item in self._items:
            button = item.button
            button.setText("" if collapsed else self._button_label(item.entry))
            plain_label = t(item.entry.label_key)
            button.setToolTip(
                plain_label
                if collapsed
                else (
                    f"{plain_label} — development state ({item.entry.phase})"
                    if not item.entry.implemented and item.entry.phase
                    else plain_label
                )
            )
            if collapsed:
                button.setStyleSheet(f"padding-left: {tokens().spacing.md}px;")
            else:
                button.setStyleSheet("")
        for label in self._content.findChildren(QLabel, "SidebarSectionLabel"):
            label.setVisible(not collapsed)
        self._mode_label.setVisible(not collapsed)
        if notify:
            self.collapsed_changed.emit(collapsed)

    def focus_route(self, route: str) -> None:
        """Move keyboard focus to a route's button (used by shortcuts)."""
        button = self._buttons.get(route)
        if button is not None:
            button.setFocus(Qt.FocusReason.ShortcutFocusReason)

    @staticmethod
    def navigation_entries() -> tuple[NavEntry, ...]:
        """Every declared navigation entry (used by tests)."""
        return all_entries()
