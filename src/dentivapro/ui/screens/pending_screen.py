"""Development-state screen for modules scheduled in later phases.

This screen exists **only while the product is under construction**. It states plainly that the module
is not implemented yet, lists exactly what the module will contain, and shows the phase that delivers
it. It is deliberately obvious so that no reviewer, and no acceptance test, can mistake it for finished
functionality.

The release audit requires :func:`dentivapro.ui.shell.navigation.unimplemented_routes` to be empty in
the final build; when it is, this screen is unreachable and is removed from the package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from dentivapro.core.i18n import t
from dentivapro.ui.components.page import PageHeader
from dentivapro.ui.components.states import pending_module_state
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dentivapro.app import ApplicationContext
    from dentivapro.ui.shell.navigation import NavEntry


class PendingModuleScreen(QWidget):
    """Explains that a module is scheduled for a later phase."""

    def __init__(
        self,
        entry: NavEntry,
        *,
        context: ApplicationContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.context = context
        self.setObjectName("PendingModuleScreen")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens().spacing.screen_gutter,
            tokens().spacing.xl,
            tokens().spacing.screen_gutter,
            tokens().spacing.xl,
        )
        layout.setSpacing(tokens().spacing.xl)
        layout.addWidget(PageHeader(t(entry.label_key), "", parent=self))

        self._state = pending_module_state(
            t(entry.label_key),
            entry.phase or "a later phase",
            list(entry.planned),
            parent=self,
        )
        layout.addWidget(self._state, 1)


def build_pending_screen(entry: NavEntry, *, context: ApplicationContext | None = None) -> QWidget:
    """Factory used by the shell for modules that are not implemented in this build."""
    return PendingModuleScreen(entry, context=context)
