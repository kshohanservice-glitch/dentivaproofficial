"""The application header.

Contains the product identity, the clinic identity, the live date, the global search entry point, the
notification centre, the help/diagnostics menu and the signed-in user chip. Controls that depend on
features delivered in later phases are honestly disabled with a tooltip that names the phase — the
product never shows a control that silently does nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.i18n import t
from dentivapro.core.timeutil import clinic_now, format_display_date
from dentivapro.domain.permissions import DEVELOPMENT_PREVIEW, PermissionSet
from dentivapro.ui.components.primitives import Text, make_icon_button, make_menu_action, spacer
from dentivapro.ui.design.icons import icon, tinted_icon_colors
from dentivapro.ui.design.tokens import tokens
from dentivapro.version import APP_NAME

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

CLOCK_INTERVAL_MS = 30_000
#: Above this unread count the bell shows ``99+`` instead of the exact number.
_MAX_BADGE_COUNT = 100


class Header(QWidget):
    """Top application bar."""

    search_requested = Signal(str)
    search_available = Signal()
    notifications_requested = Signal()
    shortcuts_requested = Signal()
    about_requested = Signal()
    diagnostics_requested = Signal()
    lock_requested = Signal()
    sign_out_requested = Signal()
    reduce_motion_changed = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Header")
        self.setFixedHeight(tokens().metrics.header_height)
        #: Clinic clock. Injectable so a caller (and the golden-image tests) can pin "today".
        self._now = now or clinic_now
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._clinic_name = ""
        self._clinic_meta = ""
        self._user_name = ""
        self._user_role = ""
        self._permissions: PermissionSet = DEVELOPMENT_PREVIEW
        self._search_enabled = False
        self._unread_count = 0
        self._reduce_motion = False
        self._compact = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens().spacing.xl, 0, tokens().spacing.lg, 0)
        layout.setSpacing(tokens().spacing.lg)

        layout.addWidget(self._build_brand())
        layout.addWidget(self._vertical_divider())
        layout.addWidget(self._build_clinic())
        layout.addWidget(spacer())
        layout.addWidget(self._build_search())
        layout.addWidget(self._build_date())
        layout.addWidget(self._build_notifications())
        layout.addWidget(self._build_help())
        layout.addWidget(self._vertical_divider())
        layout.addWidget(self._build_user())

        self._clock = QTimer(self)
        self._clock.setInterval(CLOCK_INTERVAL_MS)
        self._clock.timeout.connect(self.refresh_date)
        self._clock.start()
        self.refresh_date()

    # ---- sections ----------------------------------------------------------
    def _build_brand(self) -> QWidget:
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens().spacing.md)

        logo = QLabel(container)
        logo.setFixedSize(tokens().metrics.icon_xl + 4, tokens().metrics.icon_xl + 4)
        logo.setPixmap(
            icon("tooth", tokens().metrics.icon_xl + 4, tinted_icon_colors()["accent"]).pixmap(
                QSize(tokens().metrics.icon_xl + 4, tokens().metrics.icon_xl + 4)
            )
        )
        row.addWidget(logo)

        name = Text(APP_NAME, role="h1", object_name="HeaderBrand")
        row.addWidget(name)
        return container

    def _build_clinic(self) -> QWidget:
        container = QWidget(self)
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._clinic_label = Text(
            t("app.header.clinic_unknown"), role="body", object_name="HeaderClinic"
        )
        self._clinic_meta_label = Text(
            t("app.header.clinic_setup_hint"), role="caption", object_name="HeaderClinicMeta"
        )
        self._clinic_meta_label.setVisible(True)
        column.addWidget(self._clinic_label)
        column.addWidget(self._clinic_meta_label)
        self._clinic_container = container
        return container

    def _build_search(self) -> QWidget:
        self._search_button = QPushButton(t("app.header.search_placeholder"), self)
        self._search_button.setObjectName("SearchField")
        self._search_button.setMinimumWidth(280)
        self._search_button.setMaximumWidth(380)
        self._search_button.setFixedHeight(tokens().metrics.control_height_md)
        self._search_button.setIcon(
            icon("search", tokens().metrics.icon_md, tinted_icon_colors()["muted"])
        )
        self._search_button.setIconSize(QSize(tokens().metrics.icon_md, tokens().metrics.icon_md))
        self._search_button.setEnabled(False)
        self._search_button.setToolTip(t("app.header.search_available_later"))
        self._search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_button.clicked.connect(self._on_search_clicked)
        return self._search_button

    def _build_date(self) -> QWidget:
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens().spacing.sm)

        self._date_label = Text("", role="caption", object_name="HeaderDate")
        row.addWidget(self._date_label)
        return container

    def _build_notifications(self) -> QWidget:
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._bell = make_icon_button(
            "bell",
            tooltip=t("app.header.notifications_later"),
            on_click=self._on_notifications_clicked,
            color=tinted_icon_colors()["default"],
        )
        row.addWidget(self._bell)
        self._badge = QLabel("", container)
        self._badge.setObjectName("Badge")
        self._badge.setProperty("variant", "danger")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setVisible(False)
        row.addWidget(self._badge)
        return container

    def _build_help(self) -> QWidget:
        self._help_button = QToolButton(self)
        self._help_button.setObjectName("IconButton")
        self._help_button.setIcon(
            icon("circle-question-mark", tokens().metrics.icon_lg, tinted_icon_colors()["default"])
        )
        self._help_button.setIconSize(QSize(tokens().metrics.icon_lg, tokens().metrics.icon_lg))
        self._help_button.setFixedSize(
            tokens().metrics.control_height_md, tokens().metrics.control_height_md
        )
        self._help_button.setToolTip(t("app.header.help"))
        self._help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_button.setAutoRaise(True)
        self._help_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(self._help_button)
        make_menu_action(
            menu,
            t("app.header.shortcuts"),
            icon_name="clipboard-list",
            on_trigger=self.shortcuts_requested.emit,
        )
        make_menu_action(
            menu,
            t("app.header.about"),
            icon_name="info",
            on_trigger=self.about_requested.emit,
        )
        menu.addSeparator()
        self._motion_action = QAction(t("app.header.reduce_motion"), menu)
        self._motion_action.setCheckable(True)
        self._motion_action.setChecked(self._reduce_motion)
        self._motion_action.toggled.connect(self._on_motion_toggled)
        menu.addAction(self._motion_action)
        menu.addSeparator()
        make_menu_action(
            menu,
            t("app.header.diagnostics"),
            icon_name="hard-drive",
            tooltip=t("app.header.diagnostics_hint"),
            enabled=False,
        )
        self._help_button.setMenu(menu)
        return self._help_button

    def _build_user(self) -> QWidget:
        self._user_button = QToolButton(self)
        self._user_button.setObjectName("IconButton")
        self._user_button.setAutoRaise(True)
        self._user_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._user_button.setIcon(
            icon("user-round", tokens().metrics.icon_lg, tinted_icon_colors()["default"])
        )
        self._user_button.setIconSize(QSize(tokens().metrics.icon_lg, tokens().metrics.icon_lg))
        self._user_button.setText(t("app.header.user_none"))
        self._user_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._user_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._user_button.setToolTip(t("app.header.user_hint"))

        menu = QMenu(self._user_button)
        self._user_header = QAction(t("app.header.user_none"), menu)
        self._user_header.setEnabled(False)
        menu.addAction(self._user_header)
        menu.addSeparator()
        make_menu_action(
            menu,
            t("app.header.lock"),
            icon_name="lock",
            tooltip=t("app.header.lock_hint"),
            enabled=False,
        )
        make_menu_action(
            menu,
            t("app.header.sign_out"),
            icon_name="log-out",
            tooltip=t("app.header.sign_out_hint"),
            enabled=False,
        )
        self._user_button.setMenu(menu)
        return self._user_button

    def _vertical_divider(self) -> QFrame:
        divider = QFrame(self)
        divider.setObjectName("VerticalDivider")
        divider.setFixedWidth(1)
        divider.setFixedHeight(tokens().metrics.header_height - 2 * tokens().spacing.lg)
        return divider

    # ---- public API ----------------------------------------------------------
    # ---- responsive behaviour ---------------------------------------------
    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        """Switch to a compact bar on narrow windows so the shell fits a 1024 px laptop."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._apply_compact(self.width() < tokens().breakpoints.standard)

    def _apply_compact(self, compact: bool) -> None:
        """Drop the search placeholder text, the clinic subtitle and the user label when narrow."""
        if compact == self._compact:
            return
        self._compact = compact
        metrics = tokens().metrics
        if compact:
            self._search_button.setText("")
            self._search_button.setMaximumWidth(metrics.control_height_md)
            self._search_button.setMinimumWidth(metrics.control_height_md)
            self._user_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self._clinic_meta_label.setVisible(False)
        else:
            self._search_button.setText(t("app.header.search_placeholder"))
            self._search_button.setMaximumWidth(380)
            self._search_button.setMinimumWidth(280)
            self._user_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self._clinic_meta_label.setVisible(True)
        self.updateGeometry()

    def refresh_date(self) -> None:
        """Update the clinic date display."""
        current: datetime = self._now()
        weekday = current.strftime("%A")
        self._date_label.setText(f"{weekday}, {format_display_date(current.date())}")

    def set_clinic(self, name: str, meta: str = "") -> None:
        """Set the clinic identity shown in the header."""
        self._clinic_name = name
        self._clinic_meta = meta
        self._clinic_label.setText(name or t("app.header.clinic_unknown"))
        self._clinic_meta_label.setText(meta or t("app.header.clinic_setup_hint"))
        self._clinic_meta_label.setVisible(bool(meta) or not name)

    def set_user(self, display_name: str, role_name: str = "") -> None:
        """Set the signed-in user chip."""
        self._user_name = display_name
        self._user_role = role_name
        self._user_button.setText(display_name or t("app.header.user_none"))
        self._user_header.setText(f"{display_name} · {role_name}" if role_name else display_name)

    def set_permissions(self, permissions: PermissionSet) -> None:
        """Apply the permission set that gates header actions."""
        self._permissions = permissions

    def set_search_enabled(
        self, enabled: bool, *, callback: Callable[[str], None] | None = None
    ) -> None:
        """Enable the global search entry point once the feature exists."""
        self._search_enabled = enabled
        self._search_button.setEnabled(enabled)
        self._search_button.setToolTip("" if enabled else t("app.header.search_available_later"))
        if callback is not None:
            self._search_callback = callback

    def set_unread_count(self, count: int) -> None:
        """Show or hide the notification badge."""
        self._unread_count = max(0, count)
        self._badge.setText(
            str(self._unread_count) if self._unread_count < _MAX_BADGE_COUNT else "99+"
        )
        self._badge.setVisible(self._unread_count > 0)
        self._badge.setToolTip(t("app.header.notifications"))

    def _on_search_clicked(self) -> None:
        callback = getattr(self, "_search_callback", None)
        if callable(callback):
            callback(self._search_button.text())
        else:
            self.search_requested.emit("")

    def _on_notifications_clicked(self) -> None:
        self.notifications_requested.emit()

    def _on_motion_toggled(self, checked: bool) -> None:
        self._reduce_motion = checked
        self.reduce_motion_changed.emit(checked)

    @property
    def reduce_motion(self) -> bool:
        """True when the user asked for reduced animation."""
        return self._reduce_motion

    @property
    def unread_count(self) -> int:
        """Number of unread notifications shown on the bell."""
        return self._unread_count
