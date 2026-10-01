"""Collision-safe allocation of business identifiers.

Codes are allocated inside the caller's transaction: the sequence row is incremented and the new value
returned. Because SQLite serialises writers, two concurrent operations can never receive the same
number, and a rolled-back transaction does not consume a code that another operation could reuse —
gaps are acceptable, duplicates are not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dentivapro.core.errors import ValidationError
from dentivapro.core.ids import CODE_FORMATS, format_code
from dentivapro.data.repos.base import BaseRepository

if TYPE_CHECKING:
    from datetime import date


class SequenceRepository(BaseRepository):
    """Allocates and formats human-readable business codes."""

    def next_value(self, kind: str, *, start_at: int = 1, padding: int | None = None) -> int:
        """Increment and return the next raw sequence value for *kind*."""
        if kind not in CODE_FORMATS:
            raise ValidationError(f"Unknown identifier type '{kind}'.")
        resolved_padding = padding if padding is not None else CODE_FORMATS[kind].padding
        row = self.db.query_one("SELECT next_value FROM sequence WHERE name = ?", (kind,))
        if row is None:
            self.db.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES (?, ?, ?, ?)",
                (kind, CODE_FORMATS[kind].prefix, resolved_padding, start_at + 1),
            )
            return start_at
        value = int(row["next_value"])
        self.db.execute(
            "UPDATE sequence SET next_value = next_value + 1 WHERE name = ?",
            (kind,),
        )
        return value

    def allocate(self, kind: str, *, on: date | None = None, padding: int | None = None) -> str:
        """Allocate and format the next business code for *kind*."""
        value = self.next_value(kind, padding=padding)
        return format_code(kind, value, on=on)

    def peek(self, kind: str) -> int:
        """Return the next value that would be allocated, without consuming it."""
        row = self.db.query_one("SELECT next_value FROM sequence WHERE name = ?", (kind,))
        return int(row["next_value"]) if row is not None else 1

    def set_next(self, kind: str, value: int, *, padding: int | None = None) -> None:
        """Force the next value (used by imports and by the settings screen)."""
        if value < 1:
            raise ValidationError("The next number must be at least 1.")
        resolved_padding = padding if padding is not None else CODE_FORMATS[kind].padding
        self.db.execute(
            "INSERT INTO sequence (name, prefix, padding, next_value) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET next_value = excluded.next_value, padding = excluded.padding",
            (kind, CODE_FORMATS[kind].prefix, resolved_padding, value),
        )

    def snapshot(self) -> dict[str, int]:
        """Return the next value for every known identifier type."""
        rows = self.db.query("SELECT name, next_value FROM sequence ORDER BY name")
        return {str(row["name"]): int(row["next_value"]) for row in rows}
