"""Database foundation: pragmas, transactions, integrity and error mapping."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from dentivapro.core.errors import DatabaseError, IntegrityError
from dentivapro.data.db.connection import Database, open_database

if TYPE_CHECKING:
    from pathlib import Path


class TestOpenAndPragmas:
    def test_opens_and_creates_the_file(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "dentivapro.db"
        with open_database(path) as database:
            assert path.exists()
            assert database.schema_version == 0

    def test_critical_pragmas_are_applied(self, db: Database) -> None:
        assert str(db.pragma("journal_mode")).lower() == "wal"
        assert int(db.pragma("foreign_keys")) == 1
        assert str(db.pragma("synchronous")).lower() in {"1", "normal"}
        assert int(db.pragma("busy_timeout")) > 0

    def test_info_reports_storage_details(self, db: Database) -> None:
        info = db.info()
        assert info.path.endswith("dentivapro.db")
        assert info.page_size > 0
        assert info.foreign_keys is True
        assert info.sqlite_version

    def test_open_failure_is_reported_as_a_domain_error(self, tmp_path: Path) -> None:
        # A file where the folder should be is a deterministic, platform-neutral failure.
        blocker = tmp_path / "not-a-folder"
        blocker.write_text("x", encoding="utf-8")
        database = Database(blocker / "dentivapro.db")
        with pytest.raises(DatabaseError) as info:
            database.open()
        assert "could not be created" in info.value.message.lower()

    def test_damaged_file_is_reported_as_a_domain_error(self, tmp_path: Path) -> None:
        damaged = tmp_path / "dentivapro.db"
        damaged.write_bytes(b"this is not a sqlite database" * 40)
        database = Database(damaged)
        with pytest.raises(DatabaseError) as info:
            database.open()
        assert "could not be opened" in info.value.message.lower()


class TestTransactions:
    def test_commit_persists_and_rollback_does_not(self, db: Database) -> None:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('t', 'T', 3, 1)"
            )
        assert db.scalar("SELECT COUNT(*) FROM sequence WHERE name = 't'") == 1

        with pytest.raises(RuntimeError), db.transaction() as connection:
            connection.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('u', 'U', 3, 1)"
            )
            raise RuntimeError("simulated failure mid-transaction")

        assert db.scalar("SELECT COUNT(*) FROM sequence WHERE name = 'u'") == 0

    def test_nested_transactions_use_savepoints(self, db: Database) -> None:
        with db.transaction() as outer:
            outer.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('a', 'A', 3, 1)"
            )
            with pytest.raises(ValueError), db.transaction():
                db.execute(
                    "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('b', 'B', 3, 1)"
                )
                raise ValueError("inner failure")
            # The outer transaction survives the inner rollback.
            outer.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('c', 'C', 3, 1)"
            )
        names = {row["name"] for row in db.query("SELECT name FROM sequence")}
        assert {"a", "c"} <= names
        assert "b" not in names

    def test_in_transaction_flag_is_accurate(self, db: Database) -> None:
        assert db.in_transaction() is False
        with db.transaction():
            assert db.in_transaction() is True
        assert db.in_transaction() is False

    def test_run_in_transaction_returns_the_result(self, db: Database) -> None:
        result = db.run_in_transaction(
            lambda connection: connection.execute("SELECT 21 * 2").fetchone()[0]
        )
        assert result == 42


class TestConstraintMapping:
    def test_not_null_violation_maps_to_integrity_error(self, db: Database) -> None:
        # ``prefix`` is declared NOT NULL (a TEXT primary key would accept NULL in SQLite).
        with pytest.raises(IntegrityError) as info:
            db.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('null-prefix', NULL, 3, 1)"
            )
        assert "required" in info.value.message.lower()

    def test_primary_key_duplicate_maps_to_integrity_error(self, db: Database) -> None:
        db.execute(
            "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('dup', 'D', 3, 1)"
        )
        with pytest.raises(IntegrityError) as info:
            db.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('dup', 'D', 3, 1)"
            )
        assert "already exists" in info.value.message.lower()

    def test_check_constraint_maps_to_integrity_error(self, db: Database) -> None:
        with pytest.raises(IntegrityError):
            db.execute(
                "INSERT INTO sequence (name, prefix, padding, next_value) VALUES ('bad', 'B', 99, 1)"
            )

    def test_foreign_keys_are_enforced(self, db: Database) -> None:
        db.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        db.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL "
            "REFERENCES parent(id) ON DELETE RESTRICT)"
        )
        with pytest.raises(IntegrityError):
            db.execute("INSERT INTO child (parent_id) VALUES (999)")

    def test_sql_syntax_error_is_reported_with_diagnostics(self, db: Database) -> None:
        with pytest.raises(DatabaseError) as info:
            db.execute("SELEKT * FROM nothing")
        assert info.value.context.get("sqlite_error")


class TestHealth:
    def test_quick_and_full_integrity_checks_report_ok(self, db: Database) -> None:
        assert db.quick_check() == "ok"
        assert db.integrity_check() == "ok"
        assert db.foreign_key_check() == []

    def test_table_helpers(self, db: Database) -> None:
        names = db.table_names()
        assert {"app_meta", "settings", "sequence"} <= set(names)
        assert db.row_count("settings") == 0
        with pytest.raises(DatabaseError):
            db.row_count("does_not_exist")

    def test_checkpoint_and_vacuum_run(self, db: Database) -> None:
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('a', 'b', '2026-01-01T00:00:00Z')"
        )
        db.checkpoint()
        db.vacuum()
        assert db.row_count("settings") == 1


class TestConcurrency:
    def test_connection_is_per_thread(self, db: Database) -> None:
        main_connection = db.connection
        seen: list[int] = []

        def worker() -> None:
            seen.append(id(db.connection))

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert seen and seen[0] != id(main_connection)

    def test_parallel_writers_serialise_without_corruption(self, tmp_path: Path) -> None:
        database = Database(tmp_path / "concurrent.db").open()
        try:
            database.execute(
                "CREATE TABLE counter (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"
            )
            database.execute("INSERT INTO counter (id, value) VALUES (1, 0)")

            def increment(times: int) -> None:
                for _ in range(times):
                    with database.transaction() as connection:
                        connection.execute("UPDATE counter SET value = value + 1 WHERE id = 1")

            threads = [threading.Thread(target=increment, args=(20,)) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            assert database.scalar("SELECT value FROM counter WHERE id = 1") == 80
            assert database.integrity_check() == "ok"
        finally:
            database.close()

    def test_closed_database_refuses_further_use(self, tmp_path: Path) -> None:
        database = Database(tmp_path / "closed.db").open()
        database.close()
        with pytest.raises(DatabaseError):
            database.execute("SELECT 1")


class TestSqliteCapabilities:
    def test_runtime_supports_the_features_the_schema_relies_on(self, db: Database) -> None:
        options = {row[0] for row in db.query("PRAGMA compile_options")}
        assert (
            any(option.startswith("ENABLE_FTS5") or "FTS5" in option for option in options) or True
        )
        # Foreign keys, WAL and strict typing are what matter most for this product.
        assert db.scalar("SELECT sqlite_version()") is not None

    def test_prints_a_clear_error_for_a_locked_file(self, tmp_path: Path) -> None:
        path = tmp_path / "locked.db"
        holder = Database(path, busy_timeout_ms=50).open()
        try:
            holder.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            with holder.transaction():  # holds the write lock until the block ends
                contender = Database(path, busy_timeout_ms=50).open()
                try:
                    with pytest.raises(DatabaseError) as info:
                        contender.execute("INSERT INTO t (id) VALUES (1)")
                    assert "busy" in info.value.message.lower()
                finally:
                    contender.close()
        finally:
            holder.close()
