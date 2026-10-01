"""Page-level composition helpers: screen headers, toolbars and section titles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from dentivapro.ui.components.primitives import Text, make_button, spacer
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


class PageHeader(QWidget):
    """The title block of a screen, with optional context actions."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(tokens().spacing.lg)

        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens().spacing.md)

        text_block = QWidget(row)
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(tokens().spacing.xs)
        self._title = Text(title, role="h1", object_name="ScreenTitle", word_wrap=False)
        text_layout.addWidget(self._title)
        self._subtitle = Text(subtitle, role="body", object_name="ScreenSubtitle", word_wrap=True)
        self._subtitle.setVisible(bool(subtitle))
        text_layout.addWidget(self._subtitle)
        layout.addWidget(text_block, 1)

        self._actions_widget = QWidget(row)
        self._actions_layout = QHBoxLayout(self._actions_widget)
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(tokens().spacing.md)
        layout.addWidget(self._actions_widget, alignment=Qt.AlignmentFlag.AlignTop)

        outer.addWidget(row)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle text."""
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))

    def set_title(self, title: str) -> None:
        """Update the title text."""
        self._title.setText(title)

    def add_action(self, widget: QWidget) -> QWidget:
        """Add a widget to the header's action area."""
        self._actions_layout.addWidget(widget)
        return widget

    def add_button(
        self,
        label: str,
        *,
        variant: str = "secondary",
        icon_name: str | None = None,
        tooltip: str = "",
        enabled: bool = True,
        on_click: Callable[[], None] | None = None,
    ) -> QWidget:
        """Create and add a button to the header's action area."""
        button = make_button(
            label,
            variant=variant,  # type: ignore[arg-type]
            icon_name=icon_name,
            tooltip=tooltip,
            enabled=enabled,
            on_click=on_click,
        )
        return self.add_action(button)


class Toolbar(QWidget):
    """A horizontal strip of filters and actions above a data area."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(tokens().spacing.md)

    def add(self, widget: QWidget, *, stretch: int = 0) -> QWidget:
        """Add a widget to the toolbar."""
        self._layout.addWidget(widget, stretch)
        return widget

    def add_spacer(self) -> None:
        """Push subsequent widgets to the right."""
        self._layout.addWidget(spacer())

    def widgets(self) -> Iterable[QWidget]:
        """Return the toolbar's widgets (used by tests)."""
        found: list[QWidget] = []
        for index in range(self._layout.count()):
            item = self._layout.itemAt(index)
            widget = None if item is None else item.widget()
            if widget is not None:
                found.append(widget)
        return found


class SectionTitle(QWidget):
    """A section heading with an optional caption and trailing divider."""

    def __init__(self, title: str, caption: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens().spacing.xs)
        layout.addWidget(Text(title, role="h2"))
        if caption:
            layout.addWidget(Text(caption, role="caption", word_wrap=True))
