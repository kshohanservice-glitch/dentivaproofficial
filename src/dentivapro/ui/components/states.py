"""Designed states instead of blank screens.

Every region of the interface that can be empty, loading, unavailable or forbidden renders one of these
panels, so a clinic user always sees what is happening and what to do next: a loader while data is
fetched, an empty state with the reason and the first action, a permission-denied state that is honest
about the restriction (the business layer still enforces it), and the development state used while a
module is scheduled for a later phase. :class:`Banner` is the inline non-blocking message strip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from dentivapro.core.errors import UserFacingError
from dentivapro.core.i18n import t
from dentivapro.ui.components.primitives import IconLabel, Text, make_button, spacer
from dentivapro.ui.design.icons import tinted_icon_colors
from dentivapro.ui.design.tokens import tokens

if TYPE_CHECKING:
    from collections.abc import Callable


class StatePanel(QWidget):
    """A centred panel describing a non-content state."""

    @property
    def body_layout(self) -> QVBoxLayout:
        """The panel's vertical layout, so callers can append a structured body."""
        return self._layout

    def __init__(
        self,
        *,
        icon_name: str,
        title: str,
        body: str = "",
        tone: str = "muted",
        actions: list[tuple[str, Callable[[], None], str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
        )
        layout.setSpacing(tokens().spacing.lg)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout = layout

        colours = tinted_icon_colors()
        layout.addWidget(
            IconLabel(
                icon_name,
                size=tokens().metrics.icon_xl * 2,
                color=colours.get(tone, colours["muted"]),
            ),
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        title_label = Text(title, role="h2", object_name="StateTitle", word_wrap=True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title_label)

        if body:
            body_label = Text(body, role="body", object_name="StateBody", word_wrap=True)
            body_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            body_label.setMaximumWidth(560)
            layout.addWidget(body_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        if actions:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(tokens().spacing.md)
            row_layout.addWidget(spacer())
            for label, callback, variant in actions:
                row_layout.addWidget(make_button(label, variant=variant, on_click=callback))  # type: ignore[arg-type]
            row_layout.addWidget(spacer())
            layout.addWidget(row)


def loading_state(message: str | None = None, *, parent: QWidget | None = None) -> StatePanel:
    """Return the standard loading state (used while data is fetched)."""
    return StatePanel(
        icon_name="refresh-cw",
        title=message or t("state.loading"),
        tone="muted",
        parent=parent,
    )


def empty_state(
    title: str | None = None,
    body: str | None = None,
    *,
    icon_name: str = "file-text",
    action_label: str | None = None,
    on_action: Callable[[], None] | None = None,
    parent: QWidget | None = None,
) -> StatePanel:
    """Return an empty state with an optional primary action."""
    actions = [(action_label, on_action, "primary")] if action_label and on_action else None
    return StatePanel(
        icon_name=icon_name,
        title=title or t("state.empty_title"),
        body=body or t("state.empty_body"),
        actions=actions,
        parent=parent,
    )


def error_state(
    error: UserFacingError | None = None,
    *,
    on_retry: Callable[[], None] | None = None,
    on_copy_details: Callable[[UserFacingError], None] | None = None,
    parent: QWidget | None = None,
) -> StatePanel:
    """Return an error state with retry and (when available) copy-details actions."""
    resolved = error or UserFacingError(
        code="UNKNOWN", title=t("state.error_title"), message=t("state.error_body")
    )
    actions: list[tuple[str, Callable[[], None], str]] = []
    if on_retry is not None:
        actions.append((t("state.error_retry"), on_retry, "secondary"))
    if on_copy_details is not None:
        actions.append(
            (
                t("state.copy_details"),
                lambda: on_copy_details(resolved),
                "ghost",
            )
        )
    body = resolved.message
    if resolved.correlation_id:
        body = f"{body}\n\n{t('dialog.correlation')}: {resolved.correlation_id}"
    return StatePanel(
        icon_name="circle-alert",
        title=resolved.title or t("state.error_title"),
        body=body,
        tone="danger",
        actions=actions or None,
        parent=parent,
    )


def permission_denied_state(
    permission: str | None = None, *, parent: QWidget | None = None
) -> StatePanel:
    """Return the permission-denied state (never a blank screen)."""
    body = t("state.denied_body")
    if permission:
        body = f"{body}\n\nRequired permission: {permission}"
    return StatePanel(
        icon_name="shield-check",
        title=t("state.denied_title"),
        body=body,
        tone="warning",
        parent=parent,
    )


def pending_module_state(
    module: str,
    phase: str,
    planned: list[str] | None = None,
    *,
    parent: QWidget | None = None,
) -> StatePanel:
    """Return the development state for a module that is scheduled for a later phase.

    This panel exists only while the product is under construction. It states plainly that the module
    is not implemented yet, so nothing in a development build can be mistaken for finished
    functionality; the release audit verifies that no such screen is reachable in the final build.
    """
    panel = StatePanel(
        icon_name="hard-drive",
        title=t("foundation.pending_title", module=module),
        body=t("foundation.pending_body", module=module, phase=phase),
        tone="info",
        parent=parent,
    )
    body_layout = panel.body_layout
    if planned and body_layout is not None:
        # A bulleted list is left-aligned inside the centred panel: centred bullets are hard to read
        # and make it unclear where each item starts.
        list_block = QWidget(panel)
        list_layout = QVBoxLayout(list_block)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(tokens().spacing.sm)
        list_layout.addWidget(
            Text(t("foundation.pending_planned"), role="label", object_name="TextLabel")
        )
        for item in planned:
            row = QWidget(list_block)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(tokens().spacing.md)
            bullet = IconLabel(
                "check", size=tokens().metrics.icon_sm, color=tinted_icon_colors()["accent"]
            )
            row_layout.addWidget(bullet, alignment=Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(Text(item, role="body", word_wrap=True), 1)
            list_layout.addWidget(row)
        # Maximum, not fixed: a fixed block would stop the window shrinking on a small laptop screen.
        list_block.setMaximumWidth(520)
        body_layout.addWidget(list_block, alignment=Qt.AlignmentFlag.AlignHCenter)
    panel.setProperty("developmentState", True)
    return panel


class Banner(QWidget):
    """An inline message strip (info / warning / danger / success)."""

    def __init__(
        self,
        title: str,
        body: str = "",
        *,
        variant: str = "info",
        icon_name: str | None = None,
        actions: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setProperty("variant", variant)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens().spacing.lg, tokens().spacing.lg, tokens().spacing.lg, tokens().spacing.lg
        )
        layout.setSpacing(tokens().spacing.lg)

        default_icon = {
            "info": "circle-question-mark",
            "warning": "triangle-alert",
            "danger": "circle-alert",
            "success": "circle-check",
        }.get(variant, "circle-question-mark")
        tone = {
            "info": "info",
            "warning": "warning",
            "danger": "danger",
            "success": "success",
        }.get(variant, "info")
        layout.addWidget(
            IconLabel(
                icon_name or default_icon,
                size=tokens().metrics.icon_xl,
                color=tinted_icon_colors()[tone],
            ),
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        text_block = QWidget(self)
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(tokens().spacing.xs)
        text_layout.addWidget(Text(title, role="h3", object_name="BannerTitle", word_wrap=True))
        if body:
            text_layout.addWidget(Text(body, role="body", object_name="BannerBody", word_wrap=True))
        layout.addWidget(text_block, 1)

        if actions:
            action_row = QWidget(self)
            action_layout = QHBoxLayout(action_row)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(tokens().spacing.md)
            for action in actions:
                action_layout.addWidget(action)
            layout.addWidget(action_row, alignment=Qt.AlignmentFlag.AlignTop)
