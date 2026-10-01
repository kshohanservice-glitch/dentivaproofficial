"""Card containers.

Cards are the primary grouping surface of the product: a raised panel with a hairline border, an
optional header (title, subtitle, actions) and an optional footer. Elevation, radius, spacing and
borders all come from the design tokens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from dentivapro.ui.components.primitives import Badge, IconLabel, Text, spacer
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:
    from collections.abc import Iterable


class Card(QFrame):
    """A raised content panel."""

    def __init__(
        self,
        *,
        title: str = "",
        subtitle: str = "",
        icon_name: str | None = None,
        actions: Iterable[QWidget] = (),
        padding: int | None = None,
        parent: QWidget | None = None,
        object_name: str = "Card",
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._padding = padding if padding is not None else tokens().spacing.card_padding

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        self._header: QWidget | None = None
        if title or actions or icon_name:
            self._header = QWidget(self)
            self._header.setObjectName("CardHeader")
            header_layout = QHBoxLayout(self._header)
            header_layout.setContentsMargins(
                self._padding, tokens().spacing.lg, self._padding, tokens().spacing.lg
            )
            header_layout.setSpacing(tokens().spacing.md)
            if icon_name:
                header_layout.addWidget(IconLabel(icon_name, size=tokens().metrics.icon_lg))
            title_block = QVBoxLayout()
            title_block.setSpacing(0)
            if title:
                title_block.addWidget(Text(title, role="h3", object_name="CardTitle"))
            if subtitle:
                title_block.addWidget(
                    Text(subtitle, role="caption", object_name="CardSubtitle", word_wrap=True)
                )
            # The title block owns the remaining width so long subtitles wrap only when they must;
            # action widgets keep their natural size on the right.
            header_layout.addLayout(title_block, 1)
            for action in actions:
                header_layout.addWidget(action)
            self._outer.addWidget(self._header)

        self._body = QWidget(self)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(
            self._padding, self._padding, self._padding, self._padding
        )
        self._body_layout.setSpacing(tokens().spacing.md)
        self._outer.addWidget(self._body)

        self._footer: QWidget | None = None

    # ---- content ---------------------------------------------------------
    @property
    def body(self) -> QWidget:
        """The card's content area."""
        return self._body

    @property
    def body_layout(self) -> QVBoxLayout:
        """The layout of the content area."""
        return self._body_layout

    def add(self, widget: QWidget) -> QWidget:
        """Append a widget to the content area."""
        self._body_layout.addWidget(widget)
        return widget

    def add_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        """Append a layout to the content area."""
        self._body_layout.addLayout(layout)

    def add_stretch(self) -> None:
        """Push the existing content upwards."""
        self._body_layout.addStretch(1)

    def set_footer(self, widgets: Iterable[QWidget]) -> QWidget:
        """Add a footer strip with the given action widgets."""
        if self._footer is not None:
            self._outer.removeWidget(self._footer)
            self._footer.deleteLater()
        footer = QWidget(self)
        footer.setObjectName("CardFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(
            self._padding, tokens().spacing.md, self._padding, tokens().spacing.md
        )
        layout.setSpacing(tokens().spacing.md)
        layout.addWidget(spacer())
        for widget in widgets:
            layout.addWidget(widget)
        self._outer.addWidget(footer)
        self._footer = footer
        return footer

    def set_badge(self, text: str, variant: str = "neutral") -> Badge:
        """Add a status badge to the card body (convenience for list cards)."""
        badge = Badge(text, variant=variant)
        self.add(badge)
        return badge


class KpiCard(Card):
    """A compact metric tile: label, value, optional hint and trend chip."""

    def __init__(
        self,
        label: str,
        value: str = "—",
        *,
        hint: str = "",
        icon_name: str | None = None,
        variant: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(padding=tokens().spacing.xl, parent=parent)
        self._variant = variant
        header = QWidget(self.body)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(tokens().spacing.md)
        header_layout.addWidget(Text(label, role="kpi_label", word_wrap=True))
        header_layout.addWidget(spacer())
        if icon_name:
            header_layout.addWidget(IconLabel(icon_name, size=tokens().metrics.icon_lg))
        self.add(header)

        self._value_label = Text(value, role="kpi_value", object_name="KpiValue")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.add(self._value_label)

        self._hint_label = Text(hint, role="caption", object_name="KpiHint", word_wrap=True)
        self._hint_label.setVisible(bool(hint))
        self.add(self._hint_label)

    def set_value(self, value: str, *, hint: str | None = None) -> None:
        """Update the displayed metric."""
        self._value_label.setText(value)
        if hint is not None:
            self._hint_label.setText(hint)
            self._hint_label.setVisible(bool(hint))

    def set_hint_variant(self, variant: str) -> None:
        """Colour the hint line semantically (e.g. ``danger`` for overdue amounts)."""
        self.setProperty("variant", variant)
