"""Keyboard shortcuts.

Shortcuts are declared once so they can be documented in the in-app reference, applied to the window
and tested. None of them overrides standard Windows behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from dentivapro.ui.shell.navigation import shortcut_map

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QWidget


@dataclass(frozen=True, slots=True)
class ShortcutSpec:
    """A single keyboard shortcut."""

    key: str
    description: str
    category: str = "General"
    requires_permission: str | None = None
    available: bool = True
    note: str = ""
    handler_name: str = field(default="")


SHORTCUTS: tuple[ShortcutSpec, ...] = (
    ShortcutSpec("Ctrl+K", "Focus global search", "Navigation", note="Phase 12"),
    ShortcutSpec("Ctrl+B", "Collapse or expand the navigation", "Navigation"),
    ShortcutSpec("F5", "Refresh the current screen", "Navigation"),
    ShortcutSpec("Alt+Left", "Go back", "Navigation"),
    ShortcutSpec("Alt+Right", "Go forward", "Navigation"),
    ShortcutSpec("Ctrl+1…9", "Jump to a navigation destination", "Navigation"),
    ShortcutSpec("Esc", "Close a dialog or drawer", "General"),
    ShortcutSpec("F1", "Open this shortcut reference", "General"),
    ShortcutSpec("Ctrl+Q", "Exit " + "Dentiva Pro", "General"),
    ShortcutSpec("Ctrl+N", "New record in the current screen", "Actions", note="Phase 6 onwards"),
    ShortcutSpec("Ctrl+Shift+P", "Register a new patient", "Actions", note="Phase 6"),
    ShortcutSpec("Ctrl+S", "Save the current form", "Actions", note="Phase 6 onwards"),
    ShortcutSpec("Ctrl+P", "Print preview for the active document", "Actions", note="Phase 9"),
    ShortcutSpec("Ctrl+L", "Lock the session now", "Security", note="Phase 3"),
)

#: Shortcuts that exist in this build. Everything else is documented with the phase that delivers it,
#: so the reference never promises a key that does nothing.
AVAILABLE_IN_FOUNDATION: frozenset[str] = frozenset(
    {"Ctrl+B", "F5", "Alt+Left", "Alt+Right", "Esc", "F1", "Ctrl+Q"}
)


class ShortcutManager:
    """Registers the window-level shortcuts that are available in this build."""

    def __init__(self, window: QWidget) -> None:
        self._window = window
        self._registered: list[QShortcut] = []

    def bind(self, sequence: str, handler: Callable[[], object]) -> QShortcut:
        """Bind a shortcut to a handler and keep a reference so it is not garbage collected."""
        shortcut = QShortcut(QKeySequence(sequence), self._window)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(handler)
        self._registered.append(shortcut)
        return shortcut

    def bind_navigation(self, on_route: Callable[[str], object]) -> None:
        """Bind ``Ctrl+1…9`` to the navigation destinations."""
        for index, route in shortcut_map().items():
            self.bind(f"Ctrl+{index}", partial(on_route, route))

    def registered(self) -> tuple[str, ...]:
        """The sequences currently bound."""
        return tuple(shortcut.key().toString() for shortcut in self._registered)

    def clear(self) -> None:
        """Release every binding."""
        for shortcut in self._registered:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self._registered.clear()


def documented_shortcuts(*, include_unavailable: bool = True) -> list[dict[str, str]]:
    """Return the shortcut reference used by the in-app documentation dialog."""
    rows: list[dict[str, str]] = []
    for spec in SHORTCUTS:
        if not include_unavailable and spec.key not in AVAILABLE_IN_FOUNDATION:
            continue
        rows.append(
            {
                "keys": spec.key,
                "description": spec.description,
                "category": spec.category,
                "note": spec.note,
                "status": "available" if spec.key in AVAILABLE_IN_FOUNDATION else "later phase",
            }
        )
    return rows
