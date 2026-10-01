"""Background work that keeps the interface responsive.

Long-running operations (backup, restore, export, attachment hashing, large imports) must never block
the UI thread. :class:`Task` runs a callable on a ``QThreadPool`` and reports progress, completion and
failure through Qt signals, which Qt delivers safely on the UI thread.

Cancellation is cooperative: the callable receives a :class:`CancellationToken` and checks it between
steps (every heavy operation in this product is written that way).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from dentivapro.core.errors import DentivaError
from dentivapro.core.logging import get_logger, log_event

logger = get_logger(__name__)

T = TypeVar("T")


class TaskCancelled(Exception):  # noqa: N818 - raised by a cancelled task, not a fault
    """Raised by a task that honoured a cancellation request."""


class CancellationToken:
    """Cooperative cancellation flag shared with a running task."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation."""
        self._event.set()

    @property
    def cancelled(self) -> bool:
        """True once cancellation has been requested."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise :class:`TaskCancelled` when cancellation has been requested."""
        if self._event.is_set():
            raise TaskCancelled


@dataclass(slots=True)
class Progress:
    """Progress report for a running task."""

    current: int = 0
    total: int = 0
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def fraction(self) -> float:
        """Progress as a 0.0–1.0 fraction (0.0 when the total is unknown)."""
        if self.total <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current / self.total))

    @property
    def percent(self) -> int:
        """Progress as an integer percentage."""
        return int(round(self.fraction * 100))


ProgressCallback = Callable[[Progress], None]
TaskFunction = Callable[..., T]


class TaskSignals(QObject):
    """Signals emitted by a running task.

    Kept in its own ``QObject`` because ``QRunnable`` is not a ``QObject`` and therefore cannot own
    signals itself.
    """

    started = Signal()
    progressed = Signal(object)
    finished = Signal(object)
    failed = Signal(object)
    cancelled = Signal()


class _TaskRunnable(QRunnable):
    """Executes a task function and forwards its outcome through signals."""

    def __init__(
        self,
        name: str,
        fn: TaskFunction[T],
        token: CancellationToken,
        kwargs: dict[str, Any],
    ) -> None:
        super().__init__()
        self._name = name
        self._fn = fn
        self._token = token
        self._kwargs = kwargs
        self.signals = TaskSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            result = self._fn(token=self._token, progress=self._emit_progress, **self._kwargs)
        except TaskCancelled:
            log_event(logger, logging.INFO, "task.cancelled", task=self._name)
            self.signals.cancelled.emit()
        except DentivaError as exc:
            log_event(
                logger,
                logging.WARNING,
                "task.failed",
                task=self._name,
                code=exc.code,
                context=exc.context,
            )
            self.signals.failed.emit(exc)
        except Exception as exc:  # noqa: BLE001 - background work must never crash the application
            logger.exception(
                "background task raised an unexpected error",
                extra={"event": "task.unexpected_failure", "payload": {"task": self._name}},
            )
            self.signals.failed.emit(exc)
        else:
            log_event(logger, logging.INFO, "task.finished", task=self._name)
            self.signals.finished.emit(result)

    def _emit_progress(self, progress: Progress) -> None:
        self.signals.progressed.emit(progress)


class Task(QObject):
    """A supervised background task with progress, completion and failure signals.

    Example::

        task = Task("backup.create", backup_service.create, db=db)
        task.progressed.connect(self._on_progress)
        task.finished.connect(self._on_done)
        task.failed.connect(self._on_failed)
        task.start()
    """

    started = Signal()
    progressed = Signal(object)
    finished = Signal(object)
    failed = Signal(object)
    cancelled = Signal()

    def __init__(
        self,
        name: str,
        fn: TaskFunction[T],
        *,
        pool: QThreadPool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.name = name
        self._pool = pool or QThreadPool.globalInstance()
        self._token = CancellationToken()
        self._finished = False
        self._runnable = _TaskRunnable(name, fn, self._token, kwargs)
        self._runnable.signals.started.connect(self.started.emit)
        self._runnable.signals.progressed.connect(self.progressed.emit)
        self._runnable.signals.finished.connect(self._on_finished)
        self._runnable.signals.failed.connect(self._on_failed)
        self._runnable.signals.cancelled.connect(self._on_cancelled)

    # ---- lifecycle -----------------------------------------------------
    def start(self) -> None:
        """Submit the task to the thread pool."""
        log_event(logger, logging.INFO, "task.start", task=self.name)
        self._pool.start(self._runnable)

    def cancel(self) -> None:
        """Request cooperative cancellation."""
        log_event(logger, logging.INFO, "task.cancel_requested", task=self.name)
        self._token.cancel()

    @property
    def is_finished(self) -> bool:
        """True once the task has completed, failed or been cancelled."""
        return self._finished

    @property
    def token(self) -> CancellationToken:
        """The cancellation token handed to the task function."""
        return self._token

    def _on_finished(self, result: object) -> None:
        self._finished = True
        self.finished.emit(result)

    def _on_failed(self, error: object) -> None:
        self._finished = True
        self.failed.emit(error)

    def _on_cancelled(self) -> None:
        self._finished = True
        self.cancelled.emit()


def run_sync(fn: TaskFunction[T], **kwargs: Any) -> T:
    """Run a task function synchronously (used by tests and non-UI callers).

    The function receives the same cancellation token and progress callback the threaded version
    supplies, so one implementation serves both execution modes.
    """
    token = CancellationToken()
    progress_reports: list[Progress] = []
    result = fn(token=token, progress=progress_reports.append, **kwargs)
    log_event(
        logger,
        logging.DEBUG,
        "task.sync_completed",
        progress_reports=len(progress_reports),
    )
    return result
