"""Repositories: settings persistence, metadata bookkeeping and collision-safe code allocation."""

from __future__ import annotations

import threading
from datetime import date
from typing import TYPE_CHECKING

import pytest

from dentivapro.core.errors import ValidationError
from dentivapro.data.db.connection import Database
from dentivapro.data.db.migrations import MigrationRunner
from dentivapro.data.repos.meta_repo import MetaRepository
from dentivapro.data.repos.sequence_repo import SequenceRepository
from dentivapro.data.repos.settings_repo import SettingsRepository

if TYPE_CHECKING:
    from pathlib import Path


class TestSettingsRepository:
    def test_insert_and_update_round_trip(self, db: Database) -> None:
        repo = SettingsRepository(db)
        assert repo.get_raw("clinic.display_name") is None
        repo.set_raw("clinic.display_name", "Sunrise Dental Care")
        assert repo.get_raw("clinic.display_name") == "Sunrise Dental Care"

        repo.set_raw("clinic.display_name", "Sunrise Dental Care, Dhanmondi")
        assert repo.get_raw("clinic.display_name") == "Sunrise Dental Care, Dhanmondi"
        assert repo.count() == 1

    def test_updated_by_is_recorded(self, db: Database) -> None:
        repo = SettingsRepository(db)
        repo.set_raw("clinic.phone", "01711000000", updated_by=7)
        row = db.query_one("SELECT updated_by, updated_at FROM settings WHERE key = 'clinic.phone'")
        assert row["updated_by"] == 7
        assert row["updated_at"]

    def test_delete_removes_the_override(self, db: Database) -> None:
        repo = SettingsRepository(db)
        repo.set_raw("clinic.phone", "1")
        repo.delete("clinic.phone")
        assert repo.get_raw("clinic.phone") is None
        assert repo.count() == 0

    def test_all_returns_a_mapping(self, db: Database) -> None:
        repo = SettingsRepository(db)
        repo.set_raw("a.key", "1")
        repo.set_raw("b.key", "2")
        assert repo.get_all_raw() == {"a.key": "1", "b.key": "2"}

    def test_timestamps_are_recorded_and_change_on_update(self, db: Database) -> None:
        repo = SettingsRepository(db)
        repo.set_raw("clinic.email", "a@example.com")
        first = repo.updated_at("clinic.email")
        assert first
        repo.set_raw("clinic.email", "b@example.com")
        assert repo.updated_at("clinic.email") is not None


class TestMetaRepository:
    def test_round_trip_and_setup_flag(self, db: Database) -> None:
        repo = MetaRepository(db)
        assert repo.get("anything") is None
        assert repo.is_setup_complete is False

        repo.set("anything", "value")
        assert repo.get("anything") == "value"

        repo.mark_setup_complete()
        assert repo.is_setup_complete is True
        assert repo.first_run_completed_at

    def test_all_entries_are_listed(self, db: Database) -> None:
        repo = MetaRepository(db)
        repo.set("a", "1")
        repo.set("b", "2")
        assert set(repo.all()) >= {"a", "b"}

    def test_machine_registration_is_idempotent(self, db: Database) -> None:
        repo = MetaRepository(db)
        repo.register_machine(
            installation_id="inst-1", machine_label="CLINIC-PC", app_version="1.0.0"
        )
        first = db.query_one("SELECT * FROM machine_registry")
        repo.register_machine(
            installation_id="inst-1", machine_label="CLINIC-PC-2", app_version="1.0.1"
        )
        rows = db.query("SELECT * FROM machine_registry")
        assert len(rows) == 1
        assert rows[0]["machine_label"] == "CLINIC-PC-2"
        assert rows[0]["app_version"] == "1.0.1"
        # The first-seen timestamp is history and must survive a re-registration.
        assert rows[0]["first_seen_at"] == first["first_seen_at"]
        assert repo.installation_id() == "inst-1"

    def test_delete(self, db: Database) -> None:
        repo = MetaRepository(db)
        repo.set("temp", "1")
        repo.delete("temp")
        assert repo.get("temp") is None


class TestSequenceRepository:
    def test_allocates_increasing_codes(self, db: Database) -> None:
        repo = SequenceRepository(db)
        assert repo.allocate("patient") == "P-000001"
        assert repo.allocate("patient") == "P-000002"
        assert repo.allocate("patient") == "P-000003"

    def test_monthly_codes_include_the_period(self, db: Database) -> None:
        repo = SequenceRepository(db)
        code = repo.allocate("invoice", on=date(2026, 10, 1))
        assert code == "INV-2610-00001"
        code_next_month = repo.allocate("invoice", on=date(2026, 11, 1))
        assert code_next_month == "INV-2611-00002"

    def test_each_kind_has_an_independent_sequence(self, db: Database) -> None:
        repo = SequenceRepository(db)
        repo.allocate("patient")
        repo.allocate("visit", on=date(2026, 10, 1))
        assert repo.peek("patient") == 2
        assert (
            repo.peek(
                "visit",
            )
            == 2
        )

    def test_peek_does_not_consume(self, db: Database) -> None:
        repo = SequenceRepository(db)
        assert repo.peek("payment") == 1
        assert repo.peek("payment") == 1
        assert repo.allocate("payment", on=date(2026, 10, 1)) == "PMT-2610-00001"

    def test_unknown_kind_is_rejected(self, db: Database) -> None:
        repo = SequenceRepository(db)
        with pytest.raises(ValidationError):
            repo.allocate("not_a_kind")

    def test_set_next_for_imports(self, db: Database) -> None:
        repo = SequenceRepository(db)
        repo.set_next("patient", 5000)
        assert repo.allocate("patient") == "P-005000"
        with pytest.raises(ValidationError):
            repo.set_next("patient", 0)

    def test_codes_are_unique_under_concurrent_allocation(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sequence.db"
        database = Database(db_path).open()
        MigrationRunner(database).apply_pending()
        repo = SequenceRepository(database)
        allocated: list[str] = []
        lock = threading.Lock()

        def allocate_many() -> None:
            for _ in range(25):
                with database.transaction() as connection:
                    value = repo.next_value("patient")
                    connection.execute(
                        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                        (f"code.{value}", str(value), repo.now_iso()),
                    )
                with lock:
                    allocated.append(f"P-{value:06d}")

        threads = [threading.Thread(target=allocate_many) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        database.close()

        assert len(allocated) == 100
        assert len(set(allocated)) == 100, "a code was handed out twice"

    def test_snapshot_lists_every_allocated_kind(self, db: Database) -> None:
        repo = SequenceRepository(db)
        repo.allocate("patient")
        repo.allocate("referral", on=date(2026, 10, 1))
        snapshot = repo.snapshot()
        assert set(snapshot) == {"patient", "referral"}
