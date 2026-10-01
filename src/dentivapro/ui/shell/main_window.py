"""The main application window.

Assembles the shell: header, collapsible sidebar, routed content area, development-state banner,
toast host and status bar. The window owns navigation, shortcuts and the screen cache; business logic
stays in services, which the screens receive through :class:`dentivapro.app.ApplicationContext`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.i18n import t
from dentivapro.core.logging import get_logger, log_event
from dentivapro.domain.permissions import DEVELOPMENT_PREVIEW, PermissionSet
from dentivapro.ui.components.states import Banner, pending_module_state
from dentivapro.ui.components.toast import ToastHost
from dentivapro.ui.design.icons import icon as themed_icon
from dentivapro.ui.design.theme import theme
from dentivapro.ui.design.tokens import tokens
from dentivapro.ui.dialogs.shortcuts_dialog import ShortcutsDialog
from dentivapro.ui.errors import report_exception
from dentivapro.ui.shell.header import Header
from dentivapro.ui.shell.navigation import DEFAULT_ROUTE, entry_for
from dentivapro.ui.shell.router import Route, Router
from dentivapro.ui.shell.shortcuts import ShortcutManager
from dentivapro.ui.shell.sidebar import Sidebar
from dentivapro.version import APP_NAME, __version__

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

logger = get_logger(__name__)

#: Smallest window the shell is designed to work in (the design system's compact breakpoint, which is
#: the size of a small clinic laptop). Below this a sensible default size is applied instead.
_MIN_SUPPORTED_WIDTH = 1024
_MIN_SUPPORTED_HEIGHT = 720

#: Window size below which the application opens at its comfortable default instead.
_COMFORTABLE_WIDTH = 1200
_COMFORTABLE_HEIGHT = 700


class MainWindow(QMainWindow):
    """Dentiva Pro's main window."""

    def __init__(
        self,
        *,
        router: Router | None = None,
        permissions: PermissionSet | None = None,
        window_icon: QIcon | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("AppShell")
        self.setWindowTitle(APP_NAME)
        if window_icon is not None:
            self.setWindowIcon(window_icon)

        self.router = router or Router(permission_set=permissions or DEVELOPMENT_PREVIEW)
        self._screen_factories: dict[str, Callable[[], QWidget]] = {}
        self._screen_cache: dict[str, QWidget] = {}
        self._current_screen: QWidget | None = None

        root = QWidget(self)
        root.setObjectName("AppShell")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        # Without this the layout would adopt the un-compacted header's width as the window's minimum
        # and the shell could never shrink to a 1024 px laptop screen (the compact header then never
        # gets a chance to engage). The supported minimum is set explicitly below instead.
        root_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumSize(_MIN_SUPPORTED_WIDTH, _MIN_SUPPORTED_HEIGHT)

        self.header = Header(root, now=now)
        root_layout.addWidget(self.header)

        body = QWidget(root)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = Sidebar(parent=body)
        body_layout.addWidget(self.sidebar)

        content_container = QWidget(body)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._banner_host = QWidget(content_container)
        banner_layout = QVBoxLayout(self._banner_host)
        banner_layout.setContentsMargins(
            tokens().spacing.screen_gutter, tokens().spacing.lg, tokens().spacing.screen_gutter, 0
        )
        banner_layout.setSpacing(0)
        banner_layout.addWidget(self._build_foundation_banner())
        content_layout.addWidget(self._banner_host)

        self._stack = QStackedWidget(content_container)
        content_layout.addWidget(self._stack, 1)
        body_layout.addWidget(content_container, 1)
        root_layout.addWidget(body, 1)

        self.setCentralWidget(root)
        self._toast_host = ToastHost(root)

        self.setStatusBar(QStatusBar(self))
        self._status_label = QLabel(
            f"{APP_NAME} {__version__} · {t('app.tagline')}", self.statusBar()
        )
        self.statusBar().addPermanentWidget(self._status_label)
        self.statusBar().setSizeGripEnabled(True)

        self._shortcuts = ShortcutManager(self)
        self._wire_signals()
        self._register_shortcuts()

    # ---- construction helpers ---------------------------------------------
    def _build_foundation_banner(self) -> QWidget:
        """Banner shown while the product is under construction (removed in the final build)."""
        self._foundation_banner = Banner(
            t("foundation.banner_title"),
            t("foundation.banner_body"),
            variant="info",
            parent=self,
        )
        self._foundation_banner.setProperty("developmentState", True)
        return self._foundation_banner

    def _wire_signals(self) -> None:
        self.sidebar.route_selected.connect(self.navigate)
        self.sidebar.collapsed_changed.connect(self._on_sidebar_collapsed)
        self.header.about_requested.connect(lambda: self.navigate("about"))
        self.header.shortcuts_requested.connect(self.show_shortcut_reference)
        self.header.reduce_motion_changed.connect(self._on_reduce_motion)
        self.header.notifications_requested.connect(self._on_notifications)
        self.router.route_changed.connect(self._show_route)
        self.router.permission_denied.connect(self._on_permission_denied)

    def _register_shortcuts(self) -> None:
        self._shortcuts.bind("Ctrl+B", self.sidebar.toggle_collapsed)
        self._shortcuts.bind("F5", self.refresh_current_screen)
        self._shortcuts.bind("F1", self.show_shortcut_reference)
        self._shortcuts.bind("Alt+Left", self.navigate_back)
        self._shortcuts.bind("Alt+Right", self.navigate_forward)
        self._shortcuts.bind("Ctrl+Q", self.close)
        self._shortcuts.bind_navigation(self.navigate)

    # ---- screen registration ------------------------------------------------
    def register_screen(
        self,
        route: str,
        factory: Callable[[], QWidget],
        *,
        title_key: str | None = None,
        permission: str | None = None,
        keep_alive: bool = True,
    ) -> None:
        """Register a screen factory for a route."""
        self._screen_factories[route] = factory
        entry = entry_for(route)
        resolved_title = title_key or (entry.label_key if entry else route)
        self.router.register(
            Route(
                path=route,
                title_key=resolved_title,
                factory=factory,
                permission=permission
                if permission is not None
                else (entry.permission if entry else None),
                keep_alive=keep_alive,
            )
        )

    # ---- navigation -----------------------------------------------------------
    def navigate(self, route: str) -> bool:
        """Navigate to a route, updating the sidebar and the content area."""
        if route not in self._screen_factories:
            log_event(logger, 30, "shell.unknown_route", route=route)
            return False
        resolved = self.router.go(route)
        if resolved is None:
            return False
        self.sidebar.set_current_route(route)
        return True

    def navigate_back(self) -> None:
        """Go back in navigation history."""
        target = self.router.back()
        if target:
            self.sidebar.set_current_route(target)

    def navigate_forward(self) -> None:
        """Go forward in navigation history."""
        target = self.router.forward()
        if target:
            self.sidebar.set_current_route(target)

    def _show_route(self, route: str) -> None:
        screen = self._screen_for(route)
        if screen is None:
            return
        if self._stack.indexOf(screen) == -1:
            self._stack.addWidget(screen)
        self._stack.setCurrentWidget(screen)
        self._current_screen = screen
        resolved = self.router.resolve(route)
        self.setWindowTitle(t("app.window_title", screen=resolved.title if resolved else route))
        self._toast_host.raise_()

    def _screen_for(self, route: str) -> QWidget | None:
        cached = self._screen_cache.get(route)
        if cached is not None:
            return cached
        factory = self._screen_factories.get(route)
        if factory is None:
            return None
        try:
            screen = factory()
        except Exception as exc:  # noqa: BLE001 - a broken screen must not kill the shell
            error = report_exception(exc, context=f"building screen '{route}'")
            fallback = QWidget()
            layout = QVBoxLayout(fallback)
            layout.addWidget(
                pending_module_state(
                    t("state.error_title"),
                    error.correlation_id or "",
                    [error.message],
                    parent=fallback,
                )
            )
            return fallback
        self._screen_cache[route] = screen
        return screen

    def _keep_alive(self, route: str) -> bool:
        resolved = self.router.resolve(route)
        return bool(resolved and resolved.keep_alive)

    def _on_permission_denied(self, route: str, permission: str) -> None:
        self._toast_host.warning(
            t("state.denied_title"),
            f"{route} requires the '{permission}' permission.",
        )

    # ---- header / sidebar state ------------------------------------------------
    def set_clinic_identity(self, name: str, meta: str = "") -> None:
        """Update the clinic identity shown in the header."""
        self.header.set_clinic(name, meta)

    def set_user(self, display_name: str, role_name: str = "") -> None:
        """Update the signed-in user chip."""
        self.header.set_user(display_name, role_name)

    def set_permissions(self, permissions: PermissionSet) -> None:
        """Apply a permission set to navigation and the router."""
        self.router.set_permissions(permissions)
        self.sidebar.set_permissions(permissions)
        self.header.set_permissions(permissions)

    def _on_sidebar_collapsed(self, collapsed: bool) -> None:
        log_event(logger, 20, "shell.sidebar_toggled", collapsed=collapsed)

    def _on_reduce_motion(self, enabled: bool) -> None:
        log_event(logger, 20, "shell.reduce_motion", enabled=enabled)

    def _on_notifications(self) -> None:
        self._toast_host.info(t("app.header.notifications"), t("app.header.notifications_later"))

    # ---- dialogs ----------------------------------------------------------------
    def show_shortcut_reference(self) -> None:
        """Show the keyboard shortcut reference."""
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def show_about(self) -> None:
        """Navigate to the About screen."""
        self.navigate("about")

    def refresh_current_screen(self) -> None:
        """Ask the current screen to reload its data (screens expose ``refresh`` when they can)."""
        screen = self._current_screen
        refresh = getattr(screen, "refresh", None)
        if callable(refresh):
            refresh()
        else:
            self._toast_host.info(t("app.header.today"), t("state.loading"))

    @property
    def toasts(self) -> ToastHost:
        """The toast host, used by screens to report completed actions."""
        return self._toast_host

    @property
    def current_route(self) -> str | None:
        """The route currently displayed."""
        return self.router.current_path

    # ---- window events -------------------------------------------------------------
    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        """Keep the toast overlay aligned with the window."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._toast_host.setGeometry(self.centralWidget().rect())  # type: ignore[union-attr]

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        """Confirm before closing while the product is in its foundation state."""
        log_event(logger, 20, "shell.closing", route=self.current_route or "")
        event.accept()

    def start(self, route: str | None = None) -> None:
        """Show the window and open the first route."""
        self.show()
        if self.width() < _COMFORTABLE_WIDTH or self.height() < _COMFORTABLE_HEIGHT:
            self.resize(*default_window_size().toTuple())
        self._toast_host.setGeometry(self.centralWidget().rect())  # type: ignore[union-attr]
        self.navigate(route or DEFAULT_ROUTE)


def window_icon() -> QIcon:
    """Load the multi-size application icon for the window and taskbar."""
    branding = Path(__file__).resolve().parents[2] / "assets" / "branding"
    icon_path = branding / "app_icon.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return themed_icon("tooth", 32, theme().colour("accent_600"))


def default_window_size() -> QSize:
    """Return a sensible default window size for the supported display range."""
    return QSize(1360, 860)
