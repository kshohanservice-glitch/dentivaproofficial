"""Repository for the ``app_meta`` and ``machine_registry`` tables."""

from __future__ import annotations

from typing import Any

from dentivapro.data.repos.base import BaseRepository

FIRST_RUN_COMPLETED_KEY = "first_run_completed_at"
ACTIVATED_AT_KEY = "activated_at"
INSTALLATION_ID_KEY = "installation_id"
LAST_BACKUP_AT_KEY = "last_backup_at"
CLINIC_UPDATED_AT_KEY = "clinic_updated_at"


class MetaRepository(BaseRepository):
    """Key/value metadata about this installation."""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return a stored value."""
        row = self.db.query_one("SELECT value FROM app_meta WHERE key = ?", (key,))
        if row is None:
            return default
        value = row["value"]
        return default if value is None else str(value)

    def set(self, key: str, value: Any, *, updated_at: str | None = None) -> None:
        """Insert or update a metadata value."""
        self.db.execute(
            "INSERT INTO app_meta (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, None if value is None else str(value), updated_at or self.now_iso()),
        )

    def delete(self, key: str) -> None:
        """Remove a metadata value."""
        self.db.execute("DELETE FROM app_meta WHERE key = ?", (key,))

    def all(self) -> dict[str, str | None]:
        """Return every metadata entry."""
        rows = self.db.query("SELECT key, value FROM app_meta ORDER BY key")
        return {
            str(row["key"]): (None if row["value"] is None else str(row["value"])) for row in rows
        }

    # ---- convenience accessors -----------------------------------------
    @property
    def first_run_completed_at(self) -> str | None:
        """When the first-run setup wizard completed, or ``None``."""
        return self.get(FIRST_RUN_COMPLETED_KEY)

    @property
    def is_setup_complete(self) -> bool:
        """True once the clinic setup wizard has committed successfully."""
        return self.first_run_completed_at is not None

    def mark_setup_complete(self) -> None:
        """Record successful completion of the first-run setup."""
        self.set(FIRST_RUN_COMPLETED_KEY, self.now_iso())

    def register_machine(
        self, *, installation_id: str, machine_label: str, app_version: str
    ) -> None:
        """Record (or refresh) this installation in the machine registry."""
        now = self.now_iso()
        self.db.execute(
            "INSERT INTO machine_registry "
            "(installation_id, first_seen_at, last_seen_at, app_version, machine_label) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(installation_id) DO UPDATE SET "
            "last_seen_at = excluded.last_seen_at, app_version = excluded.app_version, "
            "machine_label = excluded.machine_label",
            (installation_id, now, now, app_version, machine_label),
        )
        self.set(INSTALLATION_ID_KEY, installation_id)

    def installation_id(self) -> str | None:
        """Return this installation's identifier when it has been registered."""
        row = self.db.query_one(
            "SELECT installation_id FROM machine_registry ORDER BY first_seen_at LIMIT 1"
        )
        return None if row is None else str(row["installation_id"])
