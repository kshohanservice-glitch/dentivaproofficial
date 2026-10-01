"""Repository for the business settings table.

Values are stored as text and converted by :class:`dentivapro.services.settings_service.SettingsService`
using the typed schema in :mod:`dentivapro.core.settings_schema`. The repository stays deliberately
dumb so all validation lives in one place.
"""

from __future__ import annotations

from dentivapro.data.repos.base import BaseRepository


class SettingsRepository(BaseRepository):
    """Raw read/write access to clinic settings."""

    def get_raw(self, key: str) -> str | None:
        """Return the stored text for *key*, or ``None`` when unset."""
        row = self.db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return None if row is None else str(row["value"])

    def get_all_raw(self) -> dict[str, str]:
        """Return every stored setting as text."""
        rows = self.db.query("SELECT key, value FROM settings ORDER BY key")
        return {str(row["key"]): str(row["value"]) for row in rows}

    def set_raw(self, key: str, value: str, *, updated_by: int | None = None) -> None:
        """Insert or update a setting value."""
        self.db.execute(
            "INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
            (key, value, self.now_iso(), updated_by),
        )

    def delete(self, key: str) -> None:
        """Remove a setting (it falls back to its declared default)."""
        self.db.execute("DELETE FROM settings WHERE key = ?", (key,))

    def count(self) -> int:
        """Return how many settings are stored (defaults are not counted)."""
        return int(self.db.scalar("SELECT COUNT(*) FROM settings", default=0))

    def updated_at(self, key: str) -> str | None:
        """Return when a setting was last changed."""
        row = self.db.query_one("SELECT updated_at FROM settings WHERE key = ?", (key,))
        return None if row is None else str(row["updated_at"])
