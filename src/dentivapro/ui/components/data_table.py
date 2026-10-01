"""The data table used by every list screen.

The table supplies the behaviours the product needs everywhere: typed columns (text, code, amount,
badge, boolean), per-column alignment, sortable headers, comfortable/compact density, single-row
selection, keyboard navigation, a sticky header, a totals row and built-in loading/empty/error
overlays so a list can never render as a blank rectangle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.money import Money
from dentivapro.ui.components.primitives import Badge
from dentivapro.ui.components.states import empty_state, loading_state
from dentivapro.ui.design.fonts import font_for_text
from dentivapro.ui.design.theme import theme
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

#: Qt 6.7+ model methods receive either a plain or a persistent index.
_ModelIndex = QModelIndex | QPersistentModelIndex

ColumnKind = Literal["text", "code", "amount", "badge", "boolean", "date"]


@dataclass(frozen=True, slots=True)
class Column:
    """Definition of a table column."""

    key: str
    title: str
    kind: ColumnKind = "text"
    width: int | None = None
    minimum_width: int = 72
    stretch: bool = False
    align: Qt.AlignmentFlag | None = None
    tooltip_from: str | None = None
    sortable: bool = True

    @property
    def resolved_align(self) -> Qt.AlignmentFlag:
        """Return the effective text alignment for this column."""
        if self.align is not None:
            return self.align
        if self.kind in ("amount", "code", "boolean", "date"):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


class TableModel(QAbstractTableModel):
    """A dictionary-backed table model with typed rendering."""

    def __init__(
        self,
        columns: Sequence[Column],
        rows: Sequence[dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self._rows: list[dict[str, Any]] = list(rows or [])

    # ---- Qt model API ----------------------------------------------------
    def rowCount(self, parent: _ModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():  # pragma: no cover - tree model semantics
            return 0
        return len(self._rows)

    def columnCount(self, parent: _ModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():  # pragma: no cover
            return 0
        return len(self._columns)

    def data(  # noqa: PLR0911 - one return per Qt role keeps the model readable
        self, index: _ModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None
        column = self._columns[index.column()]
        row = self._rows[index.row()]
        value = row.get(column.key)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._format(column, value)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(column.resolved_align)
        if role == Qt.ItemDataRole.ForegroundRole and column.kind == "amount":
            return QColor(theme().colour("ink_900"))
        if role == Qt.ItemDataRole.FontRole and column.kind in ("code", "amount"):
            font = QFont(theme().tokens.typography.family_mono)
            font.setPointSizeF(theme().tokens.typography.size_body)
            return font
        if role == Qt.ItemDataRole.ToolTipRole:
            source = column.tooltip_from or column.key
            tooltip_value = row.get(source)
            return None if tooltip_value is None else str(tooltip_value)
        if role == Qt.ItemDataRole.UserRole:
            return value
        return None

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section].title
        return str(section + 1)

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort rows by a column, with amounts compared numerically."""
        key = self._columns[column].key
        reverse = order == Qt.SortOrder.DescendingOrder

        def sort_key(row: dict[str, Any]) -> tuple[int, Any]:
            value = row.get(key)
            if value is None or value == "":
                return (1, "")
            if isinstance(value, Money):
                return (0, value.amount)
            if isinstance(value, (int, float)):
                return (0, value)
            return (0, str(value).casefold())

        self.layoutAboutToBeChanged.emit()
        self._rows.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()

    # ---- data ------------------------------------------------------------
    def set_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        """Replace the table contents."""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, index: int) -> dict[str, Any] | None:
        """Return the raw row dictionary at *index*."""
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    @property
    def rows(self) -> list[dict[str, Any]]:
        """The raw rows currently displayed."""
        return list(self._rows)

    @property
    def columns(self) -> list[Column]:
        """The column definitions."""
        return list(self._columns)

    def _format(self, column: Column, value: Any) -> str:
        if value is None:
            return "—"
        if column.kind == "amount":
            return value.format() if isinstance(value, Money) else Money.from_input(value).format()
        if column.kind == "boolean":
            return "Yes" if value else "No"
        if column.kind == "date" and hasattr(value, "strftime"):
            return value.strftime("%d %b %Y")
        text = str(value)
        return text or "—"


class DataTable(QWidget):
    """A themed table with state overlays."""

    row_activated = Signal(object)
    selection_changed = Signal(object)

    def __init__(
        self,
        columns: Sequence[Column],
        *,
        empty_title: str = "Nothing to show yet",
        empty_body: str = "Records will appear here once they exist.",
        empty_icon: str = "file-text",
        selection_mode: QAbstractItemView.SelectionMode = QAbstractItemView.SelectionMode.SingleSelection,
        density: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self._empty_title = empty_title
        self._empty_body = empty_body
        self._empty_icon = empty_icon

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        # 1 — the table itself
        table_page = QWidget(self)
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self._model = TableModel(self._columns, [], self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self._proxy.setDynamicSortFilter(True)

        self._view = QTableView(table_page)
        self._view.setModel(self._proxy)
        self._view.setSortingEnabled(True)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(selection_mode)
        self._view.setAlternatingRowColors(True)
        self._view.setShowGrid(False)
        self._view.setWordWrap(False)
        self._view.setCornerButtonEnabled(False)
        self._view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._view.verticalHeader().setVisible(False)
        self._view.verticalHeader().setDefaultSectionSize(self._row_height(density))
        header = self._view.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionsClickable(True)
        header.setStretchLastSection(True)
        header.setFixedHeight(tokens().metrics.table_header_height)
        for index, column in enumerate(self._columns):
            self._view.setColumnWidth(index, column.width or 160)
            header.setSectionResizeMode(
                index,
                QHeaderView.ResizeMode.Stretch
                if column.stretch
                else QHeaderView.ResizeMode.Interactive,
            )
        self._view.doubleClicked.connect(self._on_double_clicked)
        self._view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        table_layout.addWidget(self._view)
        self._stack.addWidget(table_page)

        # 2 — empty state
        self._empty_page = empty_state(
            self._empty_title, self._empty_body, icon_name=self._empty_icon, parent=self
        )
        self._stack.addWidget(self._empty_page)

        # 3 — loading state
        self._loading_page = loading_state(parent=self)
        self._stack.addWidget(self._loading_page)

        self._total_label: QLabel | None = None
        self.show_empty()

    # ---- configuration -----------------------------------------------------
    def _row_height(self, density: str | None) -> int:
        metrics = tokens().metrics
        resolved = density or "comfortable"
        return metrics.table_row_compact if resolved == "compact" else metrics.table_row_comfortable

    def set_density(self, density: str) -> None:
        """Switch between comfortable and compact row height."""
        self._view.verticalHeader().setDefaultSectionSize(self._row_height(density))

    # ---- data ---------------------------------------------------------------
    def set_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        """Replace the table contents and show the appropriate state."""
        self._model.set_rows(rows)
        if rows:
            self.show_table()
        else:
            self.show_empty()

    def set_empty_message(self, title: str, body: str) -> None:
        """Customise what the empty state explains."""
        self._empty_title = title
        self._empty_body = body
        page_index = self._stack.indexOf(self._empty_page)
        replacement = empty_state(title, body, icon_name=self._empty_icon, parent=self)
        self._stack.insertWidget(page_index, replacement)
        self._stack.removeWidget(self._empty_page)
        self._empty_page.deleteLater()
        self._empty_page = replacement

    @property
    def model(self) -> TableModel:
        """The underlying source model."""
        return self._model

    @property
    def view(self) -> QTableView:
        """The Qt view (exposed for advanced behaviour in later phases)."""
        return self._view

    @property
    def row_count(self) -> int:
        """Number of source rows."""
        return self._model.rowCount()

    @property
    def current_state(self) -> str:
        """Which overlay is visible: ``table``, ``empty`` or ``loading``."""
        current = self._stack.currentWidget()
        if current is self._empty_page:
            return "empty"
        if current is self._loading_page:
            return "loading"
        return "table"

    def add_totals_row(self, text: str) -> None:
        """Show a sticky summary strip underneath the table."""
        if self._total_label is None:
            self._total_label = QLabel(self)
            self._total_label.setObjectName("TextAmount")
            self.layout().addWidget(self._total_label)  # type: ignore[union-attr]
        self._total_label.setText(text)

    # ---- states ---------------------------------------------------------------
    def show_table(self) -> None:
        """Display the table."""
        self._stack.setCurrentIndex(0)

    def show_empty(self) -> None:
        """Display the empty state (when there is no data at all)."""
        self._stack.setCurrentIndex(1)

    def show_loading(self) -> None:
        """Display the loading state."""
        self._stack.setCurrentIndex(2)

    # ---- selection ------------------------------------------------------------
    def selected_row(self) -> dict[str, Any] | None:
        """Return the currently selected source row, or ``None``."""
        indexes = self._view.selectionModel().selectedRows()
        if not indexes:
            return None
        source_index = self._proxy.mapToSource(indexes[0])
        return self._model.row_at(source_index.row())

    def select_row(self, row_index: int) -> None:
        """Select a row by source index (used by tests and keyboard flows)."""
        if row_index < 0 or row_index >= self._model.rowCount():
            return
        source = self._model.index(row_index, 0)
        proxy_index = self._proxy.mapFromSource(source)
        self._view.selectRow(proxy_index.row())

    def clear_selection(self) -> None:
        """Clear the selection."""
        self._view.clearSelection()

    # ---- events ---------------------------------------------------------------
    def _on_double_clicked(self, index: QModelIndex) -> None:
        source_index = self._proxy.mapToSource(index)
        row = self._model.row_at(source_index.row())
        if row is not None:
            self.row_activated.emit(row)

    def _on_selection_changed(self, *_args: object) -> None:
        row = self.selected_row()
        self.selection_changed.emit(row)


def badge_for(value: str, *, variant: str = "neutral") -> Badge:
    """Helper used by screens that render status chips inside custom cells."""
    return Badge(value, variant=variant)


def truncate_cell(text: str, limit: int = 60) -> str:
    """Shorten long cell content for display (the full value stays in the tooltip)."""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def ensure_readable_font(text: str, size_pt: float) -> QFont:
    """Return a font that renders *text* correctly (Bengali aware)."""
    return font_for_text(text, size_pt)


def sort_callback(table: DataTable) -> Callable[[int], None]:  # pragma: no cover - convenience
    """Return a callable that sorts the table by a column index."""
    return lambda column: table.view.sortByColumn(column, Qt.SortOrder.AscendingOrder)
