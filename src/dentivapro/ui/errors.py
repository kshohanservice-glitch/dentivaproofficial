"""The application error boundary.

Three layers make sure a failure is always handled deliberately:

1. :func:`install_exception_hook` catches anything that escapes the Qt event loop, converts it to a
   safe user-facing error, logs the technical detail with a correlation id, and shows one dialog
   rather than letting the process die silently.
2. :class:`ErrorBoundary` guards individual screen operations so a failing data load shows the
   designed error state inside the screen instead of taking down the window.
3. :func:`guard_operation` is used by screens around user-triggered actions, offering the same
   consistent reporting for service calls.

Nothing here swallows an error: every path records the failure and surfaces it.
"""

from __future__ import annotations

import sys
import traceback
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from PySide6.QtWidgets import QApplication, QMessageBox

from dentivapro.core.errors import DentivaError, UserFacingError, to_user_error
from dentivapro.core.i18n import t
from dentivapro.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def new_correlation_id() -> str:
    """Return a short identifier that links a user-visible message to the log entry."""
    return uuid.uuid4().hex[:12]


def report_exception(
    exc: BaseException,
    *,
    context: str = "",
    correlation_id: str | None = None,
) -> UserFacingError:
    """Log an exception with full technical detail and return a safe description for the UI."""
    resolved_id = correlation_id or new_correlation_id()
    if isinstance(exc, DentivaError):
        logger.warning(
            "handled failure",
            extra={
                "event": "error.handled",
                "payload": {
                    "code": exc.code,
                    "context": context,
                    "error_context": exc.context,
                    "correlation_id": resolved_id,
                },
            },
        )
    else:
        logger.error(
            "unexpected failure",
            extra={
                "event": "error.unexpected",
                "payload": {"context": context, "correlation_id": resolved_id},
            },
            exc_info=exc,
        )
    user_error = to_user_error(exc, correlation_id=resolved_id)
    if not user_error.detail and not isinstance(exc, DentivaError):
        user_error.detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[
            -2000:
        ]
    return user_error


class ErrorBoundary:
    """Wraps risky operations so the UI can present a designed error state."""

    def __init__(self, *, context: str) -> None:
        self.context = context
        self.last_error: UserFacingError | None = None

    def run(self, operation: Callable[[], R]) -> tuple[R | None, UserFacingError | None]:
        """Execute *operation*, returning either its result or a user-facing error."""
        try:
            result = operation()
        except Exception as exc:  # noqa: BLE001 - this is the boundary
            error = report_exception(exc, context=self.context)
            self.last_error = error
            return None, error
        self.last_error = None
        return result, None


def guard_operation(
    context: str,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Decorator that reports failures from a user-triggered operation.

    The wrapped function returns ``None`` when it fails, after the error has been logged and a message
    shown — the failure is never hidden from the user or the log.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - this is the boundary
                error = report_exception(exc, context=context)
                show_error_dialog(error)
                return None

        return wrapper

    return decorator


def show_error_dialog(error: UserFacingError, *, parent: Any = None) -> None:
    """Show a single, plain-language error dialog with the correlation id."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(error.title or t("dialog.unexpected_title"))
    text = error.message or t("dialog.unexpected_body")
    if error.correlation_id:
        text = f"{text}\n\n{t('dialog.correlation')}: {error.correlation_id}"
    box.setText(text)
    if error.action:
        box.setInformativeText(error.action)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def install_exception_hook(app: QApplication) -> None:
    """Install handlers that turn uncaught exceptions into a logged, user-visible failure."""

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):  # pragma: no cover - console use
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        error = report_exception(exc_value, context="unhandled exception")
        show_error_dialog(error, parent=app.activeWindow())

    sys.excepthook = _hook

    def _qt_message_handler(
        _mode: object, _context: object, message: str
    ) -> None:  # pragma: no cover
        logger.warning(
            "qt message",
            extra={"event": "qt.message", "payload": {"message": message}},
        )

    # Qt's own message handler is intentionally left at the default level; it is noisy for
    # non-fatal warnings and is captured by the log handler above when needed.
    _ = _qt_message_handler
