"""The settings registry is the contract for every configurable value."""

from __future__ import annotations

from decimal import Decimal

import pytest

from dentivapro.core.errors import ValidationError
from dentivapro.core.settings_schema import REGISTRY, SettingSpec, SettingsRegistry, SettingType


class TestRegistry:
    def test_keys_are_unique_and_non_empty(self) -> None:
        keys = [spec.key for spec in REGISTRY]
        assert len(keys) == len(set(keys))
        assert all(key.strip() for key in keys)

    def test_every_spec_has_a_group_and_label(self) -> None:
        for spec in REGISTRY:
            assert spec.group, spec.key
            assert spec.label, spec.key

    def test_choices_are_declared_for_choice_settings(self) -> None:
        for spec in REGISTRY:
            if spec.value_type is SettingType.CHOICE:
                assert spec.choices, spec.key
                assert spec.default in spec.choices, spec.key

    def test_auto_lock_offers_exactly_the_required_timeouts(self) -> None:
        spec = REGISTRY.get("security.auto_lock_minutes")
        assert tuple(spec.choices) == (5, 10, 15, 30)
        assert spec.default == 15

    def test_backup_schedule_offers_7_15_and_30_days(self) -> None:
        spec = REGISTRY.get("backup.schedule_days")
        assert 7 in spec.choices and 15 in spec.choices and 30 in spec.choices

    def test_payment_methods_include_the_required_wallets(self) -> None:
        spec = REGISTRY.get("billing.payment_methods")
        for method in ("cash", "bank", "card", "bkash", "nagad", "rocket", "upay", "other"):
            assert method in str(spec.default)

    def test_print_profiles_cover_a4_a5_and_thermal(self) -> None:
        choices = REGISTRY.get("printing.prescription_profile").choices
        for profile in ("a4-portrait", "a5-portrait", "thermal-80mm", "thermal-58mm"):
            assert profile in choices

    def test_unknown_key_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            REGISTRY.get("clinic.nonexistent")

    def test_duplicate_keys_are_rejected_at_construction(self) -> None:
        spec = SettingSpec(key="a.b", group="g", label="L")
        with pytest.raises(ValueError, match="duplicate"):
            SettingsRegistry((spec, spec))

    def test_by_group_returns_only_that_group(self) -> None:
        clinic_specs = REGISTRY.by_group("clinic")
        assert clinic_specs
        assert all(spec.group == "clinic" for spec in clinic_specs)


class TestCoercion:
    def test_boolean_accepts_user_friendly_words(self) -> None:
        spec = REGISTRY.get("backup.include_attachments")
        for truthy in ("1", "true", "YES", "on", True):
            assert spec.coerce(truthy) is True
        for falsy in ("0", "false", "No", "off", False):
            assert spec.coerce(falsy) is False

    def test_boolean_rejects_nonsense(self) -> None:
        spec = REGISTRY.get("backup.include_attachments")
        with pytest.raises(ValidationError):
            spec.coerce("maybe")

    def test_integer_range_is_enforced(self) -> None:
        spec = REGISTRY.get("security.max_failed_attempts")
        assert spec.coerce("4") == 4
        with pytest.raises(ValidationError):
            spec.coerce(99)
        with pytest.raises(ValidationError):
            spec.coerce("abc")

    def test_decimal_setting_keeps_decimals(self) -> None:
        spec = REGISTRY.get("billing.default_discount_percent")
        assert spec.coerce("12.5") == Decimal("12.5")
        with pytest.raises(ValidationError):
            spec.coerce("101")

    def test_choice_is_case_sensitive_but_accepts_numbers_as_text(self) -> None:
        spec = REGISTRY.get("security.auto_lock_minutes")
        assert spec.coerce("15") == 15
        assert spec.coerce(5) == 5
        with pytest.raises(ValidationError):
            spec.coerce(20)

    def test_single_line_text_strips_newlines(self) -> None:
        spec = REGISTRY.get("clinic.phone")
        assert spec.coerce("01711  000000\n") == "01711  000000"

    def test_multiline_text_keeps_line_breaks(self) -> None:
        spec = REGISTRY.get("clinic.address")
        assert spec.coerce("House 12\nRoad 5") == "House 12\nRoad 5"

    def test_serialisation_round_trips_booleans_and_decimals(self) -> None:
        boolean = REGISTRY.get("printing.show_document_qr")
        assert boolean.coerce(boolean.serialise(True)) is True
        decimal = REGISTRY.get("billing.default_discount_percent")
        assert decimal.coerce(decimal.serialise(Decimal("7.5"))) == Decimal("7.50")

    def test_error_messages_are_user_readable(self) -> None:
        with pytest.raises(ValidationError) as info:
            REGISTRY.get("clinical.signature_height_mm").coerce(5)
        assert "signature" in info.value.message.lower()
