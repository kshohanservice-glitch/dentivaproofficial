"""Structured, privacy-respecting logging.

Log records are written as JSON lines so production problems can be diagnosed without guessing, while
a redaction layer guarantees that passwords, activation attempts, tokens and medical free text never
reach the log file.

Two sinks are configured:

* a rotating file in ``<data root>/logs/dentivapro-YYYYMMDD.jsonl``,
* a bounded in-memory ring buffer that the diagnostics export reads (never written to disk by itself).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
import sys
import threading
from collections import deque
from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dentivapro.version import __version__

#: Keys whose values must never be logged, matched case-insensitively as substrings.
SENSITIVE_KEY_PARTS: Final[tuple[str, ...]] = (
    "password",
    "passwd",
    "secret",
    "token",
    "activation",
    "activation_code",
    "salt",
    "hash",
    "verifier",
    "credential",
    "authorization",
    "api_key",
    "apikey",
)

#: Keys that may still be logged but whose free text is clinically sensitive and therefore truncated
#: out of log payloads (the database holds the real content; logs must not become a shadow record).
CLINICAL_TEXT_KEYS: Final[tuple[str, ...]] = (
    "chief_complaint",
    "complaint",
    "diagnosis",
    "examination",
    "notes",
    "note",
    "advice",
    "instructions",
    "medical_history",
    "prescription",
)

REDACTED: Final[str] = "[redacted]"
TRUNCATED: Final[str] = "[clinical text omitted]"

_CORRELATION_CHARS = re.compile(r"[^0-9a-f]")


class ContextFilter(logging.Filter):
    """Injects static fields (app version, process role) into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.app_version = __version__
        return True


class RedactionFilter(logging.Filter):
    """Removes sensitive values from log payloads.

    The filter works on the structured ``extra`` payload (``record.payload``) plus the formatted
    message, so both structured and free-text logging are covered.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        payload = getattr(record, "payload", None)
        if isinstance(payload, Mapping):
            record.payload = _redact_mapping(payload)
        record.msg = _redact_text(str(record.msg))
        if record.args:
            record.args = tuple(_redact_text(str(a)) for a in record.args)
        return True


def _redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in mapping.items():
        lowered = str(key).lower()
        if any(part in lowered for part in SENSITIVE_KEY_PARTS):
            cleaned[key] = REDACTED
        elif any(part in lowered for part in CLINICAL_TEXT_KEYS) and isinstance(value, str):
            cleaned[key] = TRUNCATED
        elif isinstance(value, Mapping):
            cleaned[key] = _redact_mapping(value)
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [_redact_mapping(v) if isinstance(v, Mapping) else v for v in value]
        else:
            cleaned[key] = value
    return cleaned


def _redact_text(text: str) -> str:
    lowered = text.lower()
    if any(part in lowered for part in SENSITIVE_KEY_PARTS) and "=" in text:
        return "[redacted message containing sensitive key]"
    return text


class JsonLineFormatter(logging.Formatter):
    """Formats records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "app_version": getattr(record, "app_version", __version__),
        }
        user = getattr(record, "user", None)
        if user:
            payload["user"] = user
        session = getattr(record, "session_id", None)
        if session:
            payload["session_id"] = session
        extra_payload = getattr(record, "payload", None)
        if isinstance(extra_payload, Mapping) and extra_payload:
            payload["data"] = dict(extra_payload)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if record.levelno >= logging.WARNING and record.pathname:
            payload["location"] = f"{Path(record.pathname).name}:{record.lineno}"
        return json.dumps(payload, ensure_ascii=False, default=str)


class RingBufferHandler(logging.Handler):
    """Keeps the most recent records in memory for the diagnostics export."""

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self._buffer: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - trivial
        try:
            entry = {
                "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="seconds"),
                "level": record.levelname,
                "logger": record.name,
                "event": getattr(record, "event", record.getMessage()),
            }
            payload = getattr(record, "payload", None)
            if isinstance(payload, Mapping) and payload:
                entry["data"] = dict(payload)
            with self._lock:
                self._buffer.append(entry)
        except Exception:  # pragma: no cover - logging must never raise
            self.handleError(record)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._buffer)


_ring_handler = RingBufferHandler()
_configured = False
_lock = threading.Lock()
_active_log_dir: Path | None = None
_active_log_path: Path | None = None


def _release_handlers(root: logging.Logger) -> None:
    """Flush and close the handlers of a previous configuration (the ring buffer is kept)."""
    for handler in list(root.handlers):
        root.removeHandler(handler)
        if handler is _ring_handler:
            continue
        with suppress(Exception):  # logging must never raise while cleaning up
            handler.flush()
        with suppress(Exception):
            handler.close()


def configure_logging(
    logs_dir: Path,
    *,
    level: str = "INFO",
    console: bool = False,
    max_bytes: int = 2_000_000,
    backup_count: int = 5,
) -> Path | None:
    """Configure the root logger and return the log file path (``None`` if unavailable).

    The configuration is reused for the same log folder and re-targeted when the folder changes.
    Re-targeting matters when the data root moves — a restore, or support running the application
    against a copy of a clinic's data folder: without it, records would keep going to the previous
    installation's file and the new folder would silently stay empty.
    """
    global _configured, _active_log_dir, _active_log_path  # noqa: PLW0603 - single configuration point
    resolved = Path(logs_dir)
    with _lock:
        if _configured and _active_log_dir == resolved:
            return _active_log_path

        root = logging.getLogger()
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        _release_handlers(root)

        formatter = JsonLineFormatter()
        log_path: Path | None = None
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            log_path = resolved / f"dentivapro-{datetime.now(tz=UTC):%Y%m%d}.jsonl"
            file_handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(ContextFilter())
            file_handler.addFilter(RedactionFilter())
            root.addHandler(file_handler)
        except OSError as exc:  # pragma: no cover - depends on host permissions
            # The logger may be unusable at this point, so this diagnostic goes straight to stderr.
            print(
                f"[dentivapro] file logging unavailable: {exc}", file=sys.stderr
            )  # qa-allow: debug-print

        _ring_handler.setFormatter(formatter)
        _ring_handler.addFilter(RedactionFilter())
        root.addHandler(_ring_handler)

        if console:
            stream = logging.StreamHandler(sys.stderr)
            stream.setFormatter(formatter)
            stream.addFilter(RedactionFilter())
            root.addHandler(stream)

        _configured = True
        _active_log_dir = resolved
        _active_log_path = log_path
        return log_path


def close_logging() -> None:
    """Flush and release every logging handler.

    Used when the application stops writing to a data folder (the restore path in Phase 13) and by the
    test suite, so that on Windows an open log file can never keep a folder locked.
    """
    global _configured, _active_log_dir, _active_log_path  # noqa: PLW0603
    with _lock:
        _release_handlers(logging.getLogger())
        _configured = False
        _active_log_dir = None
        _active_log_path = None


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    user: str | None = None,
    session_id: str | None = None,
    **payload: Any,
) -> None:
    """Log a structured event with an explicit machine-readable name."""
    logger.log(
        level,
        event,
        extra={"event": event, "user": user, "session_id": session_id, "payload": payload or {}},
    )


def diagnostics_snapshot() -> list[dict[str, Any]]:
    """Return the recent in-memory log records (already redacted)."""
    return _ring_handler.snapshot()


def iter_log_files(logs_dir: Path) -> Iterator[Path]:
    """Yield log files newest first."""
    files: Iterable[Path] = sorted(logs_dir.glob("dentivapro-*.jsonl"), reverse=True)
    return iter(files)


def clear_ring_buffer() -> None:
    """Empty the in-memory buffer (used by tests)."""
    _ring_handler._buffer.clear()  # noqa: SLF001 - intentional test/diagnostic hook


def _reset_for_tests() -> None:
    """Reset the logging configuration so tests can reconfigure with their own directories.

    File handlers are closed, not just detached: on Windows a leaked handle would keep the temporary
    data folder locked for the rest of the run.
    """
    close_logging()
    with _lock:
        _ring_handler._buffer.clear()  # noqa: SLF001


def redact_value(value: Any) -> Any:  # pragma: no cover - convenience for callers
    """Public helper for redacting a single value before logging."""
    if isinstance(value, MutableMapping):
        return _redact_mapping(value)
    return _redact_text(str(value))
