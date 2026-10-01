"""Shared repository plumbing.

Repositories own every SQL statement in the application. Services call repositories inside explicit
transactions; the UI never touches SQL. This base class holds the pieces every repository needs:
a database handle, a clock, and small helpers for mapping rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dentivapro.data.db.connection import Database


class BaseRepository:
    """Base class for repositories bound to a single :class:`Database`."""

    def __init__(self, database: Database) -> None:
        self.db = database

    # ---- helpers ---------------------------------------------------------
    @staticmethod
    def now_iso() -> str:
        """Return the current instant as a UTC ISO-8601 string."""
        return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def row_to_dict(row: Any) -> dict[str, Any]:
        """Convert a ``sqlite3.Row`` to a plain dictionary."""
        return {key: row[key] for key in row}

    @staticmethod
    def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
        """Convert a list of ``sqlite3.Row`` objects to dictionaries."""
        return [{key: row[key] for key in row} for row in rows]

    def exists(self, table: str) -> bool:
        """Return True when *table* exists in the database."""
        return table in self.db.table_names()
