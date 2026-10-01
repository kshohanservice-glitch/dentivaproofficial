"""SQLite connection management.

Design notes:

* **WAL journaling** is enabled so readers never block the writer and a crash cannot corrupt the
  database file.
* **One connection per thread** keeps Qt worker threads independent while SQLite serialises writes
  with ``busy_timeout`` rather than failing immediately.
* **Explicit transactions** — every multi-row change happens inside :meth:`Database.transaction`,
  which issues ``BEGIN IMMEDIATE`` so write locks are taken up front and cannot deadlock half-way
  through a business operation.
* **Foreign keys are enforced** (``PRAGMA foreign_keys = ON``), because referential integrity is a
  product requirement, not an optional nicety.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, TypeVar, cast

from dentivapro.core.errors import DatabaseError, IntegrityError
from dentivapro.core.logging import get_logger, log_event

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

logger = get_logger(__name__)

T = TypeVar("T")

DEFAULT_BUSY_TIMEOUT_MS = 5000
MMAP_SIZE_BYTES = 256 * 1024 * 1024


@dataclass(slots=True)
class DatabaseInfo:
    """Summary of the open database, used by diagnostics and the About screen."""

    path: str
    journal_mode: str
    page_size: int
    page_count: int
    schema_version: int
    foreign_keys: bool
    sqlite_version: str

    @property
    def size_bytes(self) -> int:
        """Approximate database size in bytes."""
        return self.page_size * self.page_count


class Database:
    """A small, explicit wrapper around SQLite used by every repository."""

    def __init__(self, path: Path, *, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS) -> None:
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self._local = threading.local()
        self._main_connection: sqlite3.Connection | None = None
        self._closed = False
        self._write_lock = threading.RLock()

    # ---- lifecycle ------------------------------------------------------
    def open(self) -> Self:
        """Open the database, creating the file (and its folder) when necessary."""
        if self._closed:
            raise DatabaseError("This database handle has already been closed.")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(
                f"The data folder '{self.path.parent}' could not be created.",
                context={"path": str(self.path), "os_error": str(exc)},
                cause=exc,
            ) from exc
        self._main_connection = self._connect()
        log_event(
            logger,
            20,
            "db.opened",
            path=str(self.path),
            journal_mode=self.pragma("journal_mode"),
        )
        return self

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.path,
                timeout=self.busy_timeout_ms / 1000,
                isolation_level=None,  # explicit transaction control
                check_same_thread=True,
            )
            connection.row_factory = sqlite3.Row
            self._apply_pragmas(connection)
        except sqlite3.Error as exc:
            # Covers an unreadable file, a file that is not a database and a folder that is read-only.
            raise DatabaseError(
                f"The clinic database at '{self.path}' could not be opened.",
                context={"path": str(self.path), "sqlite_error": str(exc)},
                cause=exc,
            ) from exc
        return connection

    def _apply_pragmas(self, connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)}")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.execute("PRAGMA cache_size = -16000")  # ~16 MB page cache
        with suppress(sqlite3.Error):  # pragma: no cover - platform dependent
            connection.execute(f"PRAGMA mmap_size = {MMAP_SIZE_BYTES}")

    @property
    def connection(self) -> sqlite3.Connection:
        """Return this thread's connection, creating it on first use."""
        if self._closed:
            raise DatabaseError("This database handle has already been closed.")
        existing = getattr(self._local, "connection", None)
        if existing is None:
            if threading.current_thread() is threading.main_thread() and self._main_connection:
                existing = self._main_connection
            else:
                existing = self._connect()
            self._local.connection = existing
        return existing

    def close(self) -> None:
        """Close every connection opened by this handle."""
        if self._closed:
            return
        self._closed = True
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            with suppress(sqlite3.Error):  # pragma: no cover - best effort
                connection.close()
            self._local.connection = None
        if self._main_connection is not None:
            with suppress(sqlite3.Error):  # pragma: no cover - best effort
                self._main_connection.close()
            self._main_connection = None
        log_event(logger, 20, "db.closed", path=str(self.path))

    def __enter__(self) -> Self:  # pragma: no cover - convenience
        return self.open()

    def __exit__(self, *_exc: object) -> None:  # pragma: no cover - convenience
        self.close()

    # ---- statements -------------------------------------------------------
    def execute(self, sql: str, parameters: Sequence[Any] | dict[str, Any] = ()) -> sqlite3.Cursor:
        """Execute a statement and return the cursor."""
        try:
            return self.connection.execute(sql, parameters)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(
                _integrity_message(exc),
                context={"sql": _summarise_sql(sql), "sqlite_error": str(exc)},
                cause=exc,
            ) from exc
        except sqlite3.Error as exc:
            raise DatabaseError(
                _operation_message(exc),
                context={"sql": _summarise_sql(sql), "sqlite_error": str(exc)},
                cause=exc,
            ) from exc

    def execute_many(self, sql: str, rows: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        """Execute a statement for many parameter rows."""
        try:
            return self.connection.executemany(sql, rows)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(
                _integrity_message(exc),
                context={"sql": _summarise_sql(sql), "sqlite_error": str(exc)},
                cause=exc,
            ) from exc
        except sqlite3.Error as exc:
            raise DatabaseError(
                _operation_message(exc),
                context={"sql": _summarise_sql(sql), "sqlite_error": str(exc)},
                cause=exc,
            ) from exc

    def query(self, sql: str, parameters: Sequence[Any] | dict[str, Any] = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return every row."""
        return list(self.execute(sql, parameters).fetchall())

    def query_one(
        self, sql: str, parameters: Sequence[Any] | dict[str, Any] = ()
    ) -> sqlite3.Row | None:
        """Run a SELECT and return the first row, or ``None``."""
        row = self.execute(sql, parameters).fetchone()
        return cast("sqlite3.Row | None", row)

    def scalar(
        self, sql: str, parameters: Sequence[Any] | dict[str, Any] = (), default: Any = None
    ) -> Any:
        """Run a SELECT and return the first column of the first row."""
        row = self.query_one(sql, parameters)
        if row is None:
            return default
        value = row[0]
        return default if value is None else value

    def pragma(self, name: str, value: Any | None = None) -> Any:
        """Read or set a pragma, returning the resulting value when one is produced."""
        if value is None:
            cursor = self.connection.execute(f"PRAGMA {name}")
        else:
            cursor = self.connection.execute(f"PRAGMA {name} = {value}")
        row = cursor.fetchone()
        return None if row is None else row[0]

    # ---- transactions ------------------------------------------------------
    @contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        """Run a block inside a transaction.

        Nested calls reuse the outer transaction through SQLite savepoints, so service methods can
        compose without accidentally committing a partially finished operation.
        """
        connection = self.connection
        depth = getattr(self._local, "depth", 0)
        with self._write_lock:
            if depth == 0:
                try:
                    connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
                except sqlite3.OperationalError as exc:
                    raise DatabaseError(
                        "The database is busy. Close other Dentiva Pro windows and try again.",
                        context={"sqlite_error": str(exc)},
                        cause=exc,
                    ) from exc
            else:
                connection.execute(f"SAVEPOINT sp_{depth}")
            self._local.depth = depth + 1
            try:
                yield connection
            except BaseException:
                if depth == 0:
                    connection.execute("ROLLBACK")
                else:
                    connection.execute(f"ROLLBACK TO sp_{depth}")
                    connection.execute(f"RELEASE sp_{depth}")
                raise
            else:
                if depth == 0:
                    connection.execute("COMMIT")
                else:
                    connection.execute(f"RELEASE sp_{depth}")
            finally:
                self._local.depth = depth

    def in_transaction(self) -> bool:
        """True when the current thread has an open transaction."""
        return bool(getattr(self._local, "depth", 0))

    def run_in_transaction(self, action: Callable[[sqlite3.Connection], T]) -> T:
        """Convenience wrapper that runs *action* inside a transaction and returns its result."""
        with self.transaction() as connection:
            return action(connection)

    # ---- health ------------------------------------------------------------
    def integrity_check(self) -> str:
        """Run ``PRAGMA integrity_check`` and return the result (``ok`` when healthy)."""
        return str(self.scalar("PRAGMA integrity_check", default="unknown"))

    def foreign_key_check(self) -> list[sqlite3.Row]:
        """Return every foreign-key violation (empty when the data is consistent)."""
        return self.query("PRAGMA foreign_key_check")

    def quick_check(self) -> str:
        """Run the faster ``PRAGMA quick_check``."""
        return str(self.scalar("PRAGMA quick_check", default="unknown"))

    def checkpoint(self) -> None:
        """Fold the write-ahead log back into the main database file."""
        try:
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error as exc:  # pragma: no cover - depends on concurrent readers
            log_event(logger, 30, "db.checkpoint_failed", error=str(exc))

    def vacuum(self) -> None:
        """Rebuild the database file (used by maintenance tools)."""
        self.connection.execute("VACUUM")

    def table_names(self) -> list[str]:
        """Return user table names in the database."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    def row_count(self, table: str) -> int:
        """Return the number of rows in *table* (identifier is validated against sqlite_master)."""
        if table not in self.table_names():
            raise DatabaseError(f"Unknown table '{table}'.")
        return int(self.scalar(f'SELECT COUNT(*) FROM "{table}"', default=0))

    @property
    def schema_version(self) -> int:
        """The ``user_version`` pragma, maintained by the migration runner."""
        return int(self.pragma("user_version") or 0)

    def set_schema_version(self, version: int) -> None:
        """Set ``user_version`` (called by the migration runner inside a transaction)."""
        self.connection.execute(f"PRAGMA user_version = {int(version)}")

    def info(self) -> DatabaseInfo:
        """Return a diagnostics summary."""
        return DatabaseInfo(
            path=str(self.path),
            journal_mode=str(self.pragma("journal_mode") or "unknown"),
            page_size=int(self.pragma("page_size") or 0),
            page_count=int(self.pragma("page_count") or 0),
            schema_version=self.schema_version,
            foreign_keys=bool(self.pragma("foreign_keys")),
            sqlite_version=sqlite3.sqlite_version,
        )


def _summarise_sql(sql: str, limit: int = 180) -> str:
    compact = " ".join(sql.split())
    return compact if len(compact) <= limit else compact[:limit] + "…"


def _operation_message(exc: sqlite3.Error) -> str:
    """Turn a low-level SQLite failure into something a clinic user can act on."""
    text = str(exc).lower()
    if "locked" in text or "busy" in text:
        return (
            "The database is busy. Close any other Dentiva Pro windows, wait for a running backup to "
            "finish, then try again."
        )
    if "readonly" in text or "read-only" in text or "attempt to write" in text:
        return (
            "The data folder is read-only. Check the folder permissions (or move the data folder), "
            "then try again."
        )
    if "not a database" in text or "malformed" in text or "disk image" in text:
        return "The database file is damaged or is not a Dentiva Pro database."
    if "database or disk is full" in text or "disk full" in text:
        return "There is not enough free disk space to save this change."
    return "The database operation could not be completed."


def _integrity_message(exc: sqlite3.IntegrityError) -> str:
    text = str(exc).lower()
    if "unique" in text:
        return "A record with the same identifier already exists."
    if "foreign key" in text:
        return "This change refers to a record that does not exist or is still in use."
    if "not null" in text:
        return "A required value is missing."
    if "check" in text:
        return "A value is outside the range allowed for this field."
    return "The change conflicts with existing data."


@contextmanager
def open_database(
    path: Path, *, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS
) -> Iterator[Database]:
    """Context manager that opens and always closes a database."""
    database = Database(path, busy_timeout_ms=busy_timeout_ms).open()
    try:
        yield database
    finally:
        database.close()
