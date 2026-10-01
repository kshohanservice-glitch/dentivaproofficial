"""The permission catalogue and its deny-by-default evaluation."""

from __future__ import annotations

import pytest

from dentivapro.core.settings_schema import REGISTRY
from dentivapro.domain.permissions import (
    ALL_CODES,
    BY_CODE,
    FINANCE_CODES,
    FINANCE_VIEW_CODES,
    SENSITIVE_CODES,
    WILDCARD,
    Area,
    PermissionSet,
    by_area,
    describe,
    is_known,
)

#: Permissions that appear in the product specification's role examples.
REQUIRED_FINANCE_PERMISSIONS = {
    "payment.view",
    "payment.create",
    "finance.report.view",
    "finance.accounting.view",
    "patient.financial.view",
    "finance.expense.view",
}

REQUIRED_CLINICAL_PERMISSIONS = {
    "prescription.create",
    "prescription.print",
    "visit.create",
    "dental_chart.edit",
    "referral.create",
}

REQUIRED_ADMIN_PERMISSIONS = {
    "user.manage",
    "role.manage",
    "settings.manage",
    "backup.create",
    "backup.restore",
    "data.destructive",
    "audit.view",
}


class TestCatalogue:
    def test_codes_are_unique_and_well_formed(self) -> None:
        codes = [permission.code for permission in BY_CODE.values()]
        assert len(codes) == len(set(codes))
        assert all(code == code.strip().lower() for code in codes)
        assert all("." in code for code in codes)

    def test_required_areas_are_covered(self) -> None:
        areas = {permission.area for permission in BY_CODE.values()}
        assert areas == {
            Area.PRACTICE,
            Area.CLINICAL,
            Area.BILLING,
            Area.INVENTORY,
            Area.ADMINISTRATION,
        }

    @pytest.mark.parametrize(
        "group",
        [REQUIRED_FINANCE_PERMISSIONS, REQUIRED_CLINICAL_PERMISSIONS, REQUIRED_ADMIN_PERMISSIONS],
    )
    def test_required_permissions_exist(self, group: set[str]) -> None:
        missing = group - ALL_CODES
        assert not missing, f"missing permissions: {sorted(missing)}"

    def test_finance_permissions_are_flagged(self) -> None:
        assert REQUIRED_FINANCE_PERMISSIONS <= FINANCE_CODES

    def test_finance_visibility_is_a_subset_of_finance_permissions(self) -> None:
        assert FINANCE_VIEW_CODES <= FINANCE_CODES
        # Read permissions that gate dashboards, reports, search and exports.
        assert {
            "finance.report.view",
            "finance.accounting.view",
            "payment.view",
        } <= FINANCE_VIEW_CODES
        # Recording a transaction is not visibility.
        assert "payment.create" not in FINANCE_VIEW_CODES
        assert "invoice.create" not in FINANCE_VIEW_CODES

    def test_destructive_and_administrative_permissions_are_sensitive(self) -> None:
        for code in (
            "data.destructive",
            "backup.restore",
            "role.manage",
            "patient.delete_permanent",
        ):
            assert code in SENSITIVE_CODES

    def test_by_area_returns_only_that_area(self) -> None:
        clinical = by_area(Area.CLINICAL)
        assert clinical
        assert all(permission.area is Area.CLINICAL for permission in clinical)

    def test_describe_is_human_readable(self) -> None:
        assert describe("invoice.finalize") == "Finalise invoices"
        assert describe("unknown.code") == "unknown.code"

    def test_is_known(self) -> None:
        assert is_known("patient.view")
        assert not is_known("patient.view_all")


class TestPermissionSet:
    def test_deny_by_default(self) -> None:
        permissions = PermissionSet()
        assert not permissions.allows("patient.view")
        assert not permissions.allows("payment.view")

    def test_recording_a_payment_does_not_reveal_financial_summaries(self) -> None:
        cashier = PermissionSet.from_codes({"patient.view", "payment.create", "invoice.create"})
        assert cashier.allows("payment.create")
        assert not cashier.can_see_financials()

    def test_reading_financial_data_enables_the_financial_gate(self) -> None:
        for code in sorted(FINANCE_VIEW_CODES):
            assert PermissionSet.from_codes({code}).can_see_financials(), code

    def test_unknown_permission_is_always_denied(self) -> None:
        assert not PermissionSet.administrator().allows("not.a.permission")

    def test_administrator_holds_every_declared_permission(self) -> None:
        admin = PermissionSet.administrator()
        for code in ALL_CODES:
            assert admin.allows(code), code
        assert admin.can_see_financials()

    def test_wildcard_grants_everything(self) -> None:
        assert PermissionSet.from_codes({WILDCARD}).is_administrator

    def test_unknown_codes_are_dropped_when_building_a_set(self) -> None:
        permissions = PermissionSet.from_codes({"patient.view", "made.up"})
        assert permissions.allows("patient.view")
        assert permissions.to_codes() == frozenset({"patient.view"})

    def test_receptionist_like_set_cannot_reach_financial_data(self) -> None:
        receptionist = PermissionSet.from_codes(
            {
                "dashboard.view",
                "patient.view",
                "patient.create",
                "appointment.view",
                "appointment.create",
                "queue.view",
                "queue.manage",
                "invoice.create",
                "payment.create",
            }
        )
        assert receptionist.allows("patient.create")
        assert not receptionist.allows("finance.report.view")
        assert not receptionist.allows("finance.accounting.view")
        assert not receptionist.allows("payment.void")
        assert not receptionist.can_see_financials()

    def test_clinical_staff_cannot_see_finance(self) -> None:
        assistant = PermissionSet.from_codes(
            {"dashboard.view", "patient.view", "visit.create", "dental_chart.edit", "queue.manage"}
        )
        assert assistant.allows("dental_chart.edit")
        assert not assistant.allows("invoice.view")
        assert not assistant.can_see_financials()

    def test_billing_officer_can_see_finance_but_not_clinical_edits(self) -> None:
        billing = PermissionSet.from_codes(
            {"invoice.view", "invoice.create", "payment.create", "finance.report.view"}
        )
        assert billing.can_see_financials()
        assert not billing.allows("dental_chart.edit")
        assert not billing.allows("prescription.create")

    def test_allows_all_and_any(self) -> None:
        permissions = PermissionSet.from_codes({"a.b", "patient.view", "patient.edit"})
        assert permissions.allows_all("patient.view", "patient.edit")
        assert not permissions.allows_all("patient.view", "patient.archive")
        assert permissions.allows_any("patient.archive", "patient.edit")
        assert not permissions.allows_any("patient.archive", "role.manage")


class TestSettingsPermissions:
    def test_every_setting_permission_exists_in_the_catalogue(self) -> None:
        for spec in REGISTRY:
            if spec.permission:
                assert spec.permission in ALL_CODES, f"{spec.key} -> {spec.permission}"

    def test_interface_preferences_need_no_permission(self) -> None:
        for key in ("ui.reduce_motion", "ui.table_density", "ui.default_date_range"):
            assert REGISTRY.get(key).permission == ""
