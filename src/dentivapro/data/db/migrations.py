"""Schema migration framework.

Rules implemented here:

* migrations are **ordered, numbered and immutable** — each file is applied exactly once;
* every migration runs inside its own transaction, so a failure leaves the database exactly as it was;
* the applied version is recorded twice (``PRAGMA user_version`` and ``app_meta.schema_version``) plus
  in the ``schema_history`` table for diagnostics;
* a database written by a **newer** schema than this build supports is refused instead of being
  modified (the user is offered backup/export paths in the UI);
* a callback hook lets the caller take a pre-migration backup once a backup subsystem exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from dentivapro.core.errors import MigrationError, SchemaVersionError
from dentivapro.core.logging import get_logger, log_event
from dentivapro.version import __version__

if TYPE_CHECKING:
    from collections.abc import Callable

    from dentivapro.data.db.connection import Database

logger = get_logger(__name__)

SCHEMA_DIR = Path(__file__).parent / "schema"
_MIGRATION_RE = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclass(frozen=True, slots=True)
class Migration:
    """A single schema migration discovered on disk."""

    version: int
    name: str
    sql: str
    filename: str


@dataclass(slots=True)
class MigrationResult:
    """Outcome of :meth:`MigrationRunner.apply_pending`."""

    from_version: int
    to_version: int
    applied: list[Migration]
    duration_ms: int

    @property
    def changed(self) -> bool:
        """True when at least one migration was applied."""
        return bool(self.applied)


def discover_migrations(schema_dir: Path | None = None) -> list[Migration]:
    """Read every migration file, validating numbering and rejecting duplicates."""
    directory = schema_dir or SCHEMA_DIR
    if not directory.exists():  # pragma: no cover - packaging failure guard
        raise MigrationError(
            "The database schema files are missing from this installation.",
            context={"schema_dir": str(directory)},
        )
    migrations: list[Migration] = []
    seen: set[int] = set()
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_RE.match(path.name)
        if not match:
            raise MigrationError(
                f"Schema file '{path.name}' does not follow the NNN_name.sql convention.",
                context={"file": path.name},
            )
        version = int(match.group("version"))
        if version in seen:
            raise MigrationError(
                f"Two schema files share version {version}.", context={"file": path.name}
            )
        seen.add(version)
        migrations.append(
            Migration(
                version=version,
                name=match.group("name"),
                sql=path.read_text(encoding="utf-8"),
                filename=path.name,
            )
        )
    if not migrations:  # pragma: no cover - packaging failure guard
        raise MigrationError(
            "No database schema files were found.", context={"dir": str(directory)}
        )
    migrations.sort(key=lambda migration: migration.version)
    return migrations


class MigrationRunner:
    """Applies pending migrations to an open database."""

    def __init__(
        self,
        database: Database,
        *,
        schema_dir: Path | None = None,
        supported_max_version: int | None = None,
    ) -> None:
        # Imported lazily to avoid a circular import between data.db modules; the runtime check keeps
        # the failure obvious if the runner is ever handed the wrong object.
        from dentivapro.data.db.connection import Database as DatabaseClass  # noqa: PLC0415

        if not isinstance(database, DatabaseClass):  # pragma: no cover - defensive
            raise TypeError("MigrationRunner requires a Database instance")
        self.database = database
        self.migrations = discover_migrations(schema_dir)
        self.max_version = supported_max_version or self.migrations[-1].version

    # ---- inspection -----------------------------------------------------
    def current_version(self) -> int:
        """Return the schema version recorded in the database."""
        recorded = int(self.database.schema_version)
        if recorded:
            return recorded
        # A database created before app_meta existed (or a fresh file) may only have app_meta.
        try:
            value = self.database.scalar("SELECT value FROM app_meta WHERE key = 'schema_version'")
        except Exception:  # noqa: BLE001 - a missing table means "version 0"
            return 0
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):  # pragma: no cover - corrupt metadata
            return 0

    def pending(self) -> list[Migration]:
        """Return migrations that have not been applied yet."""
        current = self.current_version()
        return [migration for migration in self.migrations if migration.version > current]

    def assert_compatible(self) -> None:
        """Refuse to operate on a database created by a newer application version."""
        current = self.current_version()
        if current > self.max_version:
            raise SchemaVersionError(
                "This database was created by a newer version of Dentiva Pro than the one "
                "installed on this computer. Install the newer version (or restore a backup made "
                "by this version) instead of opening it with an older build.",
                context={"database_version": current, "supported_version": self.max_version},
            )

    # ---- application ----------------------------------------------------
    def apply_pending(
        self,
        *,
        on_before_migrate: Callable[[int, int], None] | None = None,
    ) -> MigrationResult:
        """Apply every pending migration, one transaction each.

        ``on_before_migrate(from_version, to_version)`` is invoked once before the first change so the
        caller can take a safety backup (implemented together with the backup subsystem).
        """
        self.assert_compatible()
        from_version = self.current_version()
        pending = self.pending()
        if not pending:
            return MigrationResult(from_version, from_version, [], 0)

        if on_before_migrate is not None:
            on_before_migrate(from_version, pending[-1].version)

        started = perf_counter()
        applied: list[Migration] = []
        for migration in pending:
            self._apply_one(migration)
            applied.append(migration)

        to_version = applied[-1].version
        duration_ms = int((perf_counter() - started) * 1000)
        log_event(
            logger,
            20,
            "db.migrated",
            from_version=from_version,
            to_version=to_version,
            migrations=[m.filename for m in applied],
            duration_ms=duration_ms,
        )
        return MigrationResult(from_version, to_version, applied, duration_ms)

    def _apply_one(self, migration: Migration) -> None:
        """Apply one migration as a single atomic unit.

        SQLite's DDL is transactional, so the schema change, the bookkeeping rows and the version
        pragma are all committed together. ``executescript`` implicitly commits any pending
        transaction, so the script declares its own transaction boundaries explicitly rather than
        relying on the connection-level transaction manager.
        """
        started = perf_counter()
        applied_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{migration.sql}\n"
            "INSERT OR REPLACE INTO schema_history "
            "(version, name, applied_at, app_version, duration_ms) VALUES "
            f"({migration.version}, {_quote(migration.name)}, {_quote(applied_at)}, "
            f"{_quote(__version__)}, {int((perf_counter() - started) * 1000)});\n"
            "INSERT OR REPLACE INTO app_meta (key, value, updated_at) VALUES "
            f"('schema_version', {_quote(str(migration.version))}, {_quote(applied_at)});\n"
            f"PRAGMA user_version = {migration.version};\n"
            "COMMIT;\n"
        )
        connection = self.database.connection
        try:
            connection.executescript(script)
        except Exception as exc:
            # A failure inside the script leaves the transaction open; roll it back explicitly so
            # the database is exactly as it was before this migration.
            try:
                connection.execute("ROLLBACK")
            except Exception:  # noqa: BLE001 - nothing more can be done here
                logger.exception("rollback after a failed migration also failed")
            self._raise_migration_error(migration, exc)

        health = self.database.quick_check()
        if health.lower() != "ok":  # pragma: no cover - corrupted storage
            raise MigrationError(
                "The database reported a consistency problem after the upgrade.",
                context={"migration": migration.filename, "quick_check": health},
            )
        log_event(
            logger,
            20,
            "db.migration_applied",
            migration=migration.filename,
            duration_ms=int((perf_counter() - started) * 1000),
        )

    @staticmethod
    def _raise_migration_error(migration: Migration, exc: BaseException) -> None:
        log_event(
            logger,
            40,
            "db.migration_failed",
            migration=migration.filename,
            error=str(exc),
        )
        if isinstance(exc, MigrationError):  # pragma: no cover - defensive re-raise
            raise exc
        raise MigrationError(
            f"The database could not be upgraded (step {migration.version}: {migration.name}). "
            "No changes were kept. If the problem persists, restore your most recent backup.",
            context={"migration": migration.filename, "error": str(exc)},
            cause=exc,
        ) from exc

    def describe(self) -> dict[str, object]:
        """Return a diagnostics-friendly summary of the schema state."""
        return {
            "current_version": self.current_version(),
            "supported_version": self.max_version,
            "available_migrations": [m.filename for m in self.migrations],
            "pending": [m.filename for m in self.pending()],
        }


def _quote(value: str) -> str:
    """Quote a string for safe interpolation into a migration script.

    Migration scripts are built as a single `executescript` call so the whole change is one atomic
    transaction. The interpolated values are entirely controlled (a name parsed from a migration
    filename, an ISO timestamp and a version string), and this helper makes the quoting explicit and
    testable rather than relying on that being obvious.
    """
    return "'" + value.replace("'", "''") + "'"
