"""Toast notifications.

Toasts confirm completed actions and surface non-blocking problems. They are queued (never stacked
into a wall of messages), auto-dismiss after a severity-dependent delay, can always be dismissed
manually, and never steal keyboard focus.
"""

from __future__ import annotations

from collections import deque
from typing import Literal

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from dentivapro.core.i18n import t
from dentivapro.ui.components.primitives import IconLabel, Text, make_icon_button
from dentivapro.ui.design.icons import tinted_icon_colors
from dentivapro.ui.design.tokens import tokens

ToastVariant = Literal["info", "success", "warning", "danger"]

_ICONS: dict[str, str] = {
    "info": "circle-question-mark",
    "success": "circle-check",
    "warning": "triangle-alert",
    "danger": "circle-alert",
}

_DURATIONS_MS: dict[str, int] = {
    "info": 4000,
    "success": 4000,
    "warning": 6000,
    "danger": 8000,
}

_MAX_VISIBLE = 3


class Toast(QFrame):
    """A single toast card."""

    closed = Signal(object)

    def __init__(
        self,
        title: str,
        body: str = "",
        *,
        variant: ToastVariant = "info",
        duration_ms: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("variant", variant)
        self.setFixedWidth(tokens().metrics.toast_width)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens().spacing.lg, tokens().spacing.lg, tokens().spacing.md, tokens().spacing.lg
        )
        layout.setSpacing(tokens().spacing.lg)
        layout.addWidget(
            IconLabel(
                _ICONS.get(variant, "circle-question-mark"),
                size=tokens().metrics.icon_lg,
                color=tinted_icon_colors().get(variant, tinted_icon_colors()["info"]),
            ),
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        text_block = QWidget(self)
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(tokens().spacing.xs)
        text_layout.addWidget(Text(title, role="h3", object_name="ToastTitle", word_wrap=True))
        if body:
            text_layout.addWidget(Text(body, role="body", object_name="ToastBody", word_wrap=True))
        layout.addWidget(text_block, 1)

        layout.addWidget(
            make_icon_button(
                "x",
                tooltip=t("toast.dismiss"),
                on_click=self._dismiss,
                size=tokens().metrics.control_height_sm,
                color=tinted_icon_colors()["muted"],
            ),
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        self._duration = (
            duration_ms if duration_ms is not None else _DURATIONS_MS.get(variant, 4000)
        )
        self._timer: QTimer | None = None

    def start_timer(self) -> None:
        """Begin the auto-dismiss countdown."""
        if self._duration <= 0:
            return
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._duration)
        self._timer.timeout.connect(self._dismiss)
        self._timer.start()

    def enterEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        """Pause the countdown while the pointer is over the toast."""
        if self._timer is not None:
            self._timer.stop()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        """Resume the countdown when the pointer leaves."""
        if self._timer is not None:
            self._timer.start()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def _dismiss(self) -> None:
        self.closed.emit(self)


class ToastHost(QWidget):
    """Owner of the toast stack, anchored to the bottom-right of its parent window.

    The host is a transparent overlay: it never intercepts clicks outside the toasts themselves.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
            tokens().spacing.xxxl,
        )
        self._layout.setSpacing(tokens().spacing.md)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self._visible: deque[Toast] = deque()
        self._queue: deque[tuple[str, str, str, int | None]] = deque()
        self.hide()

    # ---- public API ------------------------------------------------------
    def show_toast(
        self,
        title: str,
        body: str = "",
        *,
        variant: ToastVariant = "info",
        duration_ms: int | None = None,
    ) -> None:
        """Display a toast (queued when three are already visible)."""
        if len(self._visible) >= _MAX_VISIBLE:
            self._queue.append((title, body, variant, duration_ms))
            return
        self._present(title, body, variant, duration_ms)

    def success(self, title: str, body: str = "") -> None:
        """Show a success toast."""
        self.show_toast(title, body, variant="success")

    def info(self, title: str, body: str = "") -> None:
        """Show an informational toast."""
        self.show_toast(title, body, variant="info")

    def warning(self, title: str, body: str = "") -> None:
        """Show a warning toast."""
        self.show_toast(title, body, variant="warning")

    def danger(self, title: str, body: str = "") -> None:
        """Show an error toast."""
        self.show_toast(title, body, variant="danger")

    def copy_confirmation(self) -> None:
        """Show the standard 'copied to the clipboard' confirmation."""
        self.success(t("toast.copied"))

    # ---- internals --------------------------------------------------------
    def _present(self, title: str, body: str, variant: str, duration_ms: int | None) -> None:
        toast = Toast(title, body, variant=variant, duration_ms=duration_ms, parent=self)  # type: ignore[arg-type]
        toast.closed.connect(self._on_closed)
        toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._layout.addWidget(toast, alignment=Qt.AlignmentFlag.AlignRight)
        self._visible.append(toast)
        self.show()
        self.raise_()
        self._animate_in(toast)
        toast.start_timer()

    def _on_closed(self, toast: Toast) -> None:
        if toast in self._visible:
            self._visible.remove(toast)
        self._layout.removeWidget(toast)
        toast.deleteLater()
        if not self._visible:
            if self._queue:
                title, body, variant, duration = self._queue.popleft()
                self._present(title, body, variant, duration)
            else:
                self.hide()

    def _animate_in(self, toast: Toast) -> None:
        if getattr(self, "_reduce_motion", False):
            return
        start = QPoint(0, tokens().spacing.xxl)
        animation = QPropertyAnimation(toast, b"pos", toast)
        animation.setDuration(tokens().motion.base)
        animation.setStartValue(toast.pos() + start)
        animation.setEndValue(toast.pos())
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    @property
    def visible_count(self) -> int:
        """Number of currently visible toasts (used by tests)."""
        return len(self._visible)

    @property
    def queued_count(self) -> int:
        """Number of toasts waiting for space (used by tests)."""
        return len(self._queue)
