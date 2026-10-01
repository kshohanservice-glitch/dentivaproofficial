"""The settings service: validation, caching, change notification and permission handling."""

from __future__ import annotations

from decimal import Decimal

import pytest

from dentivapro.core.errors import PermissionDenied, ValidationError
from dentivapro.core.settings_schema import REGISTRY
from dentivapro.services.settings_service import SettingChange, SettingsService


class TestReads:
    def test_defaults_apply_when_nothing_is_stored(self, settings_service: SettingsService) -> None:
        assert settings_service.get_str("clinic.display_name") == ""
        assert settings_service.get_int("security.auto_lock_minutes") == 15
        assert settings_service.get_bool("backup.include_attachments") is True
        assert settings_service.get("billing.default_discount_percent") == Decimal("0.00")

    def test_unknown_key_raises(self, settings_service: SettingsService) -> None:
        with pytest.raises(ValidationError):
            settings_service.get("not.a.setting")

    def test_all_settings_can_be_listed(self, settings_service: SettingsService) -> None:
        everything = settings_service.get_all()
        assert set(everything) == set(REGISTRY.keys())
        assert set(settings_service.get_all("security")) == {
            spec.key for spec in REGISTRY.by_group("security")
        }

    def test_describe_all_includes_declaration_and_value(
        self, settings_service: SettingsService
    ) -> None:
        described = settings_service.describe_all()
        entry = described["security.auto_lock_minutes"]
        assert entry["value"] == 15
        assert entry["choices"] == [5, 10, 15, 30]
        assert entry["permission"] == "settings.manage"


class TestWrites:
    def test_set_validates_and_persists(self, settings_service: SettingsService) -> None:
        change = settings_service.set("clinic.display_name", "  Sunrise Dental Care  ")
        assert isinstance(change, SettingChange)
        assert change.new_value == "Sunrise Dental Care"
        assert change.requires_audit is True
        assert settings_service.get_str("clinic.display_name") == "Sunrise Dental Care"

    def test_invalid_value_is_rejected_and_nothing_is_stored(
        self, settings_service: SettingsService, db
    ) -> None:
        with pytest.raises(ValidationError):
            settings_service.set("security.auto_lock_minutes", 20)
        assert db.row_count("settings") == 0
        assert settings_service.get_int("security.auto_lock_minutes") == 15

    def test_multi_line_address_is_preserved(self, settings_service: SettingsService) -> None:
        settings_service.set("clinic.address", "House 12, Road 5\nDhanmondi, Dhaka 1205")
        assert "\n" in settings_service.get_str("clinic.address")

    def test_bengali_values_are_stored_without_corruption(
        self, settings_service: SettingsService
    ) -> None:
        settings_service.set("clinic.display_name_bn", "সূর্য ডেন্টাল কেয়ার")
        assert settings_service.get_str("clinic.display_name_bn") == "সূর্য ডেন্টাল কেয়ার"

    def test_unchanged_value_reports_no_change(self, settings_service: SettingsService) -> None:
        settings_service.set("clinic.phone", "01711000000")
        assert settings_service.set("clinic.phone", "01711000000") is None

    def test_permission_denied_is_enforced(self, settings_service: SettingsService, db) -> None:
        with pytest.raises(PermissionDenied) as info:
            settings_service.set("clinic.display_name", "X", permitted=False)
        assert info.value.context["setting"] == "clinic.display_name"
        assert db.row_count("settings") == 0

    def test_set_many_applies_each_change(self, settings_service: SettingsService) -> None:
        changes = settings_service.set_many(
            {"clinic.phone": "01711000000", "clinical.followup_default_days": 10}
        )
        assert len(changes) == 2
        assert settings_service.get_int("clinical.followup_default_days") == 10

    def test_batch_notification_emits_once(self, db) -> None:
        from dentivapro.data.repos.settings_repo import SettingsRepository

        batches: list[list[SettingChange]] = []
        service = SettingsService(SettingsRepository(db), on_change=batches.append)
        service.set_and_notify_batch({"clinic.phone": "1", "clinic.email": "a@b.c"})
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_reset_returns_to_the_default(self, settings_service: SettingsService) -> None:
        settings_service.set("clinical.followup_default_days", 21)
        change = settings_service.reset("clinical.followup_default_days")
        assert change is not None
        assert change.new_value == 7
        assert settings_service.get_int("clinical.followup_default_days") == 7

    def test_reset_requires_permission(self, settings_service: SettingsService) -> None:
        with pytest.raises(PermissionDenied):
            settings_service.reset("clinical.followup_default_days", permitted=False)

    def test_validate_does_not_store(self, settings_service: SettingsService, db) -> None:
        assert settings_service.validate("security.auto_lock_minutes", "30") == 30
        assert db.row_count("settings") == 0


class TestCaching:
    def test_values_are_cached_and_invalidated(self, settings_service: SettingsService, db) -> None:
        assert settings_service.get_int("clinical.followup_default_days") == 7
        # A write from another path (as another screen would) is picked up after invalidation.
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("clinical.followup_default_days", "30", settings_service._repo.now_iso()),  # noqa: SLF001
        )
        assert settings_service.get_int("clinical.followup_default_days") == 7
        settings_service.invalidate(["clinical.followup_default_days"])
        assert settings_service.get_int("clinical.followup_default_days") == 30

    def test_invalidate_all(self, settings_service: SettingsService) -> None:
        settings_service.get_int("clinical.followup_default_days")
        settings_service.invalidate()
        assert settings_service.get_int("clinical.followup_default_days") == 7

    def test_corrupt_stored_value_falls_back_to_default(
        self, settings_service: SettingsService, db
    ) -> None:
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("security.auto_lock_minutes", "seventeen", settings_service._repo.now_iso()),  # noqa: SLF001
        )
        settings_service.invalidate()
        assert settings_service.get_int("security.auto_lock_minutes") == 15

    def test_subscribe_adds_a_second_listener(self, db) -> None:
        from dentivapro.data.repos.settings_repo import SettingsRepository

        first: list[list[SettingChange]] = []
        second: list[list[SettingChange]] = []
        service = SettingsService(SettingsRepository(db), on_change=first.append)
        service.subscribe(second.append)
        service.set("clinic.phone", "01711000000")
        assert first and second


class TestChangeHook:
    def test_change_hook_receives_before_and_after_values(self, db) -> None:
        from dentivapro.data.repos.settings_repo import SettingsRepository

        captured: list[SettingChange] = []
        service = SettingsService(SettingsRepository(db), on_change=captured.extend)
        service.set("clinical.followup_default_days", 14)
        assert captured[0].old_value == 7
        assert captured[0].new_value == 14
        assert captured[0].group == "clinical"

    def test_change_hook_failures_do_not_lose_the_write(self, db) -> None:
        from dentivapro.data.repos.settings_repo import SettingsRepository

        def exploding_hook(_changes: list[SettingChange]) -> None:
            raise RuntimeError("audit unavailable")

        service = SettingsService(SettingsRepository(db), on_change=exploding_hook)
        with pytest.raises(RuntimeError):
            service.set("clinic.phone", "01711000000")
        # The value is stored (settings are not rolled back by an audit outage) and readable.
        service.invalidate()
        assert service.get_str("clinic.phone") == "01711000000"
