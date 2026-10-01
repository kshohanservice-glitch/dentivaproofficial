"""Schema migrations must be ordered, atomic and safe against version mismatches."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dentivapro.core.errors import MigrationError, SchemaVersionError
from dentivapro.data.db.migrations import (
    Migration,
    MigrationRunner,
    discover_migrations,
)

if TYPE_CHECKING:
    from pathlib import Path

    from dentivapro.data.db.connection import Database


class TestDiscovery:
    def test_migrations_are_discovered_in_order(self) -> None:
        migrations = discover_migrations()
        assert migrations
        versions = [migration.version for migration in migrations]
        assert versions == sorted(versions)
        assert versions[0] == 1

    def test_every_migration_follows_the_naming_convention(self) -> None:
        for migration in discover_migrations():
            assert migration.filename[0].isdigit()
            assert migration.sql.strip()

    def test_bad_filename_is_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "not-a-migration.sql").write_text("SELECT 1;", encoding="utf-8")
        with pytest.raises(MigrationError, match="convention"):
            discover_migrations(tmp_path)

    def test_duplicate_versions_are_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "001_a.sql").write_text("SELECT 1;", encoding="utf-8")
        (tmp_path / "001_b.sql").write_text("SELECT 1;", encoding="utf-8")
        with pytest.raises(MigrationError, match="version"):
            discover_migrations(tmp_path)

    def test_empty_directory_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(MigrationError):
            discover_migrations(tmp_path)


class TestApplication:
    def test_applies_pending_migrations_once(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        assert runner.current_version() == 0
        result = runner.apply_pending()
        assert result.changed
        assert result.from_version == 0
        assert result.to_version == result.applied[-1].version
        assert runner.current_version() == result.to_version
        assert runner.pending() == []

        # Running again is a no-op.
        second = MigrationRunner(fresh_db).apply_pending()
        assert not second.changed

    def test_version_is_recorded_in_both_places(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        result = runner.apply_pending()
        assert int(fresh_db.pragma("user_version")) == result.to_version
        assert fresh_db.scalar("SELECT value FROM app_meta WHERE key = 'schema_version'") == str(
            result.to_version
        )

    def test_history_records_what_ran(self, fresh_db: Database) -> None:
        MigrationRunner(fresh_db).apply_pending()
        rows = fresh_db.query(
            "SELECT version, name, app_version FROM schema_history ORDER BY version"
        )
        assert rows
        assert rows[0]["name"]
        assert rows[0]["app_version"]

    def test_base_migration_creates_the_foundation_tables(self, fresh_db: Database) -> None:
        MigrationRunner(fresh_db).apply_pending()
        tables = set(fresh_db.table_names())
        assert {
            "app_meta",
            "settings",
            "sequence",
            "machine_registry",
            "schema_history",
        } <= tables

    def test_database_remains_healthy_after_migrating(self, fresh_db: Database) -> None:
        MigrationRunner(fresh_db).apply_pending()
        assert fresh_db.integrity_check() == "ok"
        assert fresh_db.foreign_key_check() == []

    def test_failing_migration_rolls_back_completely(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        broken = Migration(
            version=99,
            name="broken",
            sql="CREATE TABLE good (id INTEGER PRIMARY KEY);\nTHIS IS NOT SQL;",
            filename="099_broken.sql",
        )
        with pytest.raises(MigrationError):
            runner._apply_one(broken)  # noqa: SLF001 - exercising the atomicity guarantee directly
        assert "good" not in fresh_db.table_names()
        assert runner.current_version() == 0
        assert fresh_db.integrity_check() == "ok"

    def test_newer_database_is_refused_rather_than_modified(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        runner.apply_pending()
        fresh_db.set_schema_version(999)
        stricter = MigrationRunner(fresh_db)
        with pytest.raises(SchemaVersionError) as info:
            stricter.assert_compatible()
        assert "newer version" in info.value.message

    def test_pre_migration_hook_receives_the_version_range(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        captured: list[tuple[int, int]] = []
        runner.apply_pending(on_before_migrate=lambda a, b: captured.append((a, b)))
        assert captured
        assert captured[0][0] == 0

    def test_describe_reports_state(self, fresh_db: Database) -> None:
        runner = MigrationRunner(fresh_db)
        described = runner.describe()
        assert described["current_version"] == 0
        assert described["pending"]
        runner.apply_pending()
        assert MigrationRunner(fresh_db).describe()["pending"] == []
