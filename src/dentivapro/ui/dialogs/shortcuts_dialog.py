"""The keyboard shortcut reference dialog.

Lists the shortcuts that work in this build and states clearly which ones arrive with later phases,
so the reference never promises a key that does nothing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.i18n import t
from dentivapro.ui.components.data_table import Column, DataTable
from dentivapro.ui.components.page import PageHeader
from dentivapro.ui.components.primitives import Badge
from dentivapro.ui.design.tokens import tokens
from dentivapro.ui.shell.shortcuts import documented_shortcuts


class ShortcutsDialog(QDialog):
    """Modal reference of every shortcut and its availability."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("shortcuts.title"))
        self.setModal(True)
        self.resize(620, 560)
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens().spacing.xxl, tokens().spacing.xxl, tokens().spacing.xxl, tokens().spacing.xxl
        )
        layout.setSpacing(tokens().spacing.xl)
        layout.addWidget(PageHeader(t("shortcuts.title"), t("shortcuts.hint"), parent=self))

        columns = (
            Column("keys", "Keys", kind="code", width=130, align=Qt.AlignmentFlag.AlignLeft),
            Column("description", "Action", stretch=True),
            Column("category", "Category", width=120),
            Column("status", "Status", width=110, align=Qt.AlignmentFlag.AlignCenter),
        )
        self._table = DataTable(
            columns,
            empty_title="No shortcuts",
            empty_body="This build does not register any keyboard shortcuts.",
            density="compact",
            parent=self,
        )
        rows = [
            {
                "keys": row["keys"],
                "description": row["description"] + (f" ({row['note']})" if row["note"] else ""),
                "category": row["category"],
                "status": "Available" if row["status"] == "available" else "Later phase",
            }
            for row in documented_shortcuts()
        ]
        self._table.set_rows(rows)
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @property
    def table(self) -> DataTable:
        """The shortcut table (used by tests)."""
        return self._table


def status_badge(status: str) -> Badge:
    """Return a badge describing shortcut availability."""
    return Badge(
        "Available" if status == "available" else "Later phase",
        variant="success" if status == "available" else "neutral",
    )


def dialog_button_row(dialog: QDialog) -> QHBoxLayout:  # pragma: no cover - layout helper
    """Return a right-aligned button row for dialogs."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(tokens().spacing.md)
    row.addStretch(1)
    _ = dialog
    return row
