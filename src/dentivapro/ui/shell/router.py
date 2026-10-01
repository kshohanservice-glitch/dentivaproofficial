"""Screen routing.

The router owns the mapping from route names to screens, history (back/forward), and the permission
decision for each destination. The permission decision is *reported* to the UI so it can explain
itself; enforcement itself lives in the service layer, so hiding a screen is never the security
boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from dentivapro.core.i18n import t
from dentivapro.core.logging import get_logger, log_event
from dentivapro.domain.permissions import ANONYMOUS, PermissionSet

logger = get_logger(__name__)

ScreenFactory = Callable[[], QWidget]


@dataclass(slots=True)
class Route:
    """A navigable destination."""

    path: str
    title_key: str
    factory: ScreenFactory
    permission: str | None = None
    area: str = ""
    description_key: str = ""
    keep_alive: bool = True
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> str:
        """Human-readable screen title."""
        return t(self.title_key)


class Router(QObject):
    """Resolves routes, keeps history and reports navigation events."""

    route_changed = Signal(str)
    permission_denied = Signal(str, str)  # route, permission

    def __init__(self, *, permission_set: PermissionSet | None = None) -> None:
        super().__init__()
        self._routes: dict[str, Route] = {}
        self._history: list[str] = []
        self._forward: list[str] = []
        self._current: str | None = None
        self._permissions = permission_set or ANONYMOUS

    # ---- registration -----------------------------------------------------
    def register(self, route: Route) -> None:
        """Register a route (replacing any previous registration at the same path)."""
        self._routes[route.path] = route

    def routes(self) -> tuple[str, ...]:
        """Return every registered path."""
        return tuple(self._routes)

    def resolve(self, path: str) -> Route | None:
        """Return the route for *path*, or ``None``."""
        return self._routes.get(path)

    # ---- permissions --------------------------------------------------------
    def set_permissions(self, permissions: PermissionSet) -> None:
        """Update the permission set used for navigation decisions."""
        self._permissions = permissions

    @property
    def permissions(self) -> PermissionSet:
        """The permission set currently in effect."""
        return self._permissions

    def is_allowed(self, path: str) -> bool:
        """True when the current permission set may open *path*."""
        route = self.resolve(path)
        if route is None:
            return False
        if route.permission is None:
            return True
        return self._permissions.allows(route.permission)

    # ---- navigation -----------------------------------------------------------
    def go(self, path: str, *, push_history: bool = True) -> Route | None:
        """Navigate to a route, returning it (or ``None`` when unknown)."""
        route = self.resolve(path)
        if route is None:
            log_event(logger, 30, "router.unknown_route", route=path)
            return None
        if not self.is_allowed(path):
            log_event(
                logger,
                30,
                "router.permission_denied",
                route=path,
                permission=route.permission,
            )
            self.permission_denied.emit(path, route.permission or "")
            return route
        if push_history and self._current is not None and self._current != path:
            self._history.append(self._current)
            self._forward.clear()
        self._current = path
        log_event(logger, 20, "router.navigated", route=path)
        self.route_changed.emit(path)
        return route

    def back(self) -> str | None:
        """Navigate to the previous route."""
        if not self._history:
            return None
        target = self._history.pop()
        if self._current is not None:
            self._forward.append(self._current)
        self._current = target
        self.route_changed.emit(target)
        return target

    def forward(self) -> str | None:
        """Navigate forward again after :meth:`back`."""
        if not self._forward:
            return None
        target = self._forward.pop()
        if self._current is not None:
            self._history.append(self._current)
        self._current = target
        self.route_changed.emit(target)
        return target

    @property
    def current_path(self) -> str | None:
        """The route currently displayed."""
        return self._current

    @property
    def can_go_back(self) -> bool:
        """True when a previous route exists."""
        return bool(self._history)

    @property
    def can_go_forward(self) -> bool:
        """True when a forward route exists."""
        return bool(self._forward)

    def clear_history(self) -> None:
        """Drop the navigation history (used on sign-out)."""
        self._history.clear()
        self._forward.clear()
