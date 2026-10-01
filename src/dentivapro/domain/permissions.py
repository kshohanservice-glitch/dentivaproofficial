"""The permission catalogue.

Every sensitive operation in Dentiva Pro is gated by a permission code from this catalogue. The codes
are declared once here so that roles, services, navigation entries and tests all reference the same
strings — a mistyped code cannot silently disable a check.

Phase 1 declares the catalogue so the shell can build permission-aware navigation. Enforcement (the
session object, the service decorators and the query guards) arrives in Phase 2, and the test suite
proves that every service refuses an unauthorised caller rather than merely hiding a button.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Area(StrEnum):
    """Functional areas used to group permissions in the role editor."""

    PRACTICE = "practice"
    CLINICAL = "clinical"
    BILLING = "billing"
    INVENTORY = "inventory"
    ADMINISTRATION = "administration"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


@dataclass(frozen=True, slots=True)
class Permission:
    """A single permission code."""

    code: str
    area: Area
    name: str
    description: str = ""
    sensitive: bool = False
    finance: bool = False


PERMISSIONS: Final[tuple[Permission, ...]] = (
    # ---- practice --------------------------------------------------------
    Permission("dashboard.view", Area.PRACTICE, "View the dashboard"),
    Permission("patient.view", Area.PRACTICE, "View patients"),
    Permission("patient.create", Area.PRACTICE, "Register patients"),
    Permission("patient.edit", Area.PRACTICE, "Edit patient details"),
    Permission("patient.archive", Area.PRACTICE, "Archive patients", sensitive=True),
    Permission(
        "patient.delete_permanent", Area.PRACTICE, "Permanently delete a patient", sensitive=True
    ),
    Permission("patient.export", Area.PRACTICE, "Export patient data", sensitive=True),
    Permission("patient.print", Area.PRACTICE, "Print patient documents"),
    Permission("patient.attachment.view", Area.PRACTICE, "View patient attachments"),
    Permission("patient.attachment.add", Area.PRACTICE, "Add patient attachments"),
    Permission(
        "patient.attachment.delete", Area.PRACTICE, "Remove patient attachments", sensitive=True
    ),
    Permission("appointment.view", Area.PRACTICE, "View appointments"),
    Permission("appointment.create", Area.PRACTICE, "Create appointments"),
    Permission("appointment.edit", Area.PRACTICE, "Edit appointments"),
    Permission("appointment.cancel", Area.PRACTICE, "Cancel appointments"),
    Permission("appointment.manage_settings", Area.PRACTICE, "Configure appointment rules"),
    Permission("queue.view", Area.PRACTICE, "View the patient queue"),
    Permission("queue.manage", Area.PRACTICE, "Manage the patient queue"),
    # ---- clinical --------------------------------------------------------
    Permission("visit.view", Area.CLINICAL, "View visits"),
    Permission("visit.create", Area.CLINICAL, "Record visits"),
    Permission("visit.edit", Area.CLINICAL, "Edit open visits"),
    Permission("visit.void", Area.CLINICAL, "Void a visit", sensitive=True),
    Permission("dental_chart.view", Area.CLINICAL, "View the dental chart"),
    Permission("dental_chart.edit", Area.CLINICAL, "Update the dental chart"),
    Permission("treatment.catalog.view", Area.CLINICAL, "View the treatment catalogue"),
    Permission("treatment.catalog.manage", Area.CLINICAL, "Manage the treatment catalogue"),
    Permission("prescription.view", Area.CLINICAL, "View prescriptions"),
    Permission("prescription.create", Area.CLINICAL, "Write prescriptions"),
    Permission("prescription.edit", Area.CLINICAL, "Edit draft prescriptions"),
    Permission("prescription.finalize", Area.CLINICAL, "Finalise prescriptions"),
    Permission("prescription.void", Area.CLINICAL, "Void a prescription", sensitive=True),
    Permission("prescription.print", Area.CLINICAL, "Print prescriptions"),
    Permission("prescription.manage_settings", Area.CLINICAL, "Configure prescription defaults"),
    Permission("referral.view", Area.CLINICAL, "View referrals"),
    Permission("referral.create", Area.CLINICAL, "Record referrals"),
    Permission("referral.edit", Area.CLINICAL, "Edit referrals"),
    Permission("clinical_catalog.manage", Area.CLINICAL, "Manage clinical finding lists"),
    Permission("medicine_catalog.manage", Area.CLINICAL, "Manage the medicine list"),
    # ---- billing ---------------------------------------------------------
    Permission("invoice.view", Area.BILLING, "View invoices"),
    Permission("invoice.create", Area.BILLING, "Create invoices"),
    Permission("invoice.edit_draft", Area.BILLING, "Edit draft invoices"),
    Permission("invoice.finalize", Area.BILLING, "Finalise invoices"),
    Permission("invoice.void", Area.BILLING, "Void invoices", sensitive=True, finance=True),
    Permission("invoice.print", Area.BILLING, "Print invoices"),
    Permission("payment.view", Area.BILLING, "View payments", finance=True),
    Permission("payment.create", Area.BILLING, "Record payments", finance=True),
    Permission("payment.void", Area.BILLING, "Void payments", sensitive=True, finance=True),
    Permission(
        "patient.financial.view", Area.BILLING, "View patient balances and ledgers", finance=True
    ),
    Permission(
        "finance.report.view", Area.BILLING, "View financial reports", finance=True, sensitive=True
    ),
    Permission(
        "finance.accounting.view", Area.BILLING, "View accounting", finance=True, sensitive=True
    ),
    Permission("finance.expense.view", Area.BILLING, "View expenses", finance=True),
    Permission("finance.expense.create", Area.BILLING, "Record expenses", finance=True),
    Permission("finance.expense.void", Area.BILLING, "Void expenses", finance=True, sensitive=True),
    Permission("finance.income.view", Area.BILLING, "View other income", finance=True),
    Permission("finance.income.create", Area.BILLING, "Record other income", finance=True),
    Permission(
        "finance.export", Area.BILLING, "Export financial data", finance=True, sensitive=True
    ),
    Permission(
        "finance.settings.manage", Area.BILLING, "Configure billing settings", sensitive=True
    ),
    # ---- inventory -------------------------------------------------------
    Permission("inventory.view", Area.INVENTORY, "View inventory"),
    Permission("inventory.manage", Area.INVENTORY, "Manage inventory items"),
    Permission("inventory.purchase", Area.INVENTORY, "Record stock purchases"),
    Permission("inventory.adjust", Area.INVENTORY, "Adjust stock", sensitive=True),
    Permission("inventory.report.view", Area.INVENTORY, "View inventory reports"),
    Permission(
        "inventory.cost.view", Area.INVENTORY, "View item costs", finance=True, sensitive=True
    ),
    Permission("inventory.settings.manage", Area.INVENTORY, "Configure inventory settings"),
    # ---- administration --------------------------------------------------
    Permission("staff.view", Area.ADMINISTRATION, "View staff"),
    Permission("staff.manage", Area.ADMINISTRATION, "Manage staff", sensitive=True),
    Permission("user.view", Area.ADMINISTRATION, "View users", sensitive=True),
    Permission("user.manage", Area.ADMINISTRATION, "Manage users", sensitive=True),
    Permission("role.manage", Area.ADMINISTRATION, "Manage roles", sensitive=True),
    Permission("permission.manage", Area.ADMINISTRATION, "Change permissions", sensitive=True),
    Permission("settings.view", Area.ADMINISTRATION, "View settings"),
    Permission("settings.manage", Area.ADMINISTRATION, "Change settings", sensitive=True),
    Permission(
        "print.profile.manage", Area.ADMINISTRATION, "Manage print profiles", sensitive=True
    ),
    Permission("backup.view", Area.ADMINISTRATION, "View backup status", sensitive=True),
    Permission("backup.create", Area.ADMINISTRATION, "Create backups", sensitive=True),
    Permission("backup.restore", Area.ADMINISTRATION, "Restore a backup", sensitive=True),
    Permission("backup.settings.manage", Area.ADMINISTRATION, "Configure backups", sensitive=True),
    Permission("data.export", Area.ADMINISTRATION, "Export clinic data", sensitive=True),
    Permission(
        "data.destructive",
        Area.ADMINISTRATION,
        "Perform destructive data operations",
        sensitive=True,
    ),
    Permission("audit.view", Area.ADMINISTRATION, "View the audit trail", sensitive=True),
    Permission("audit.export", Area.ADMINISTRATION, "Export the audit trail", sensitive=True),
    Permission("diagnostics.export", Area.ADMINISTRATION, "Export diagnostics"),
    Permission("notification.view", Area.ADMINISTRATION, "View notifications"),
    Permission("notification.manage", Area.ADMINISTRATION, "Manage notifications"),
)

BY_CODE: Final[dict[str, Permission]] = {permission.code: permission for permission in PERMISSIONS}

#: Permissions that must never be granted implicitly (they are called out in the role editor).
SENSITIVE_CODES: Final[frozenset[str]] = frozenset(
    permission.code for permission in PERMISSIONS if permission.sensitive
)

#: Permissions that gate financial information anywhere in the product (dashboard, search, reports).
FINANCE_CODES: Final[frozenset[str]] = frozenset(
    permission.code for permission in PERMISSIONS if permission.finance
)

#: The subset of :data:`FINANCE_CODES` that allows *reading* financial information. These gate the
#: dashboard widgets, reports, search results and exports: recording a payment (a transactional duty)
#: must never by itself expose the clinic's revenue summaries.
FINANCE_VIEW_CODES: Final[frozenset[str]] = frozenset(
    code for code in FINANCE_CODES if code.endswith(".view")
)

ALL_CODES: Final[frozenset[str]] = frozenset(BY_CODE)

#: The wildcard granted to the Administrator role.
WILDCARD: Final[str] = "*"


def is_known(code: str) -> bool:
    """Return True when *code* is part of the catalogue."""
    return code in BY_CODE


def by_area(area: Area) -> tuple[Permission, ...]:
    """Return every permission in an area."""
    return tuple(permission for permission in PERMISSIONS if permission.area is area)


def describe(code: str) -> str:
    """Return a human-readable name for a permission code."""
    permission = BY_CODE.get(code)
    return permission.name if permission else code


@dataclass(frozen=True, slots=True)
class PermissionSet:
    """An immutable set of granted permissions, evaluated with deny-by-default semantics."""

    granted: frozenset[str] = frozenset()
    is_administrator: bool = False

    @classmethod
    def administrator(cls) -> PermissionSet:
        """Return the full permission set."""
        return cls(granted=ALL_CODES, is_administrator=True)

    @classmethod
    def from_codes(cls, codes: frozenset[str] | set[str] | tuple[str, ...]) -> PermissionSet:
        """Build a set from explicit codes, ignoring unknown ones and honouring the wildcard."""
        cleaned = frozenset(code for code in codes if is_known(code))
        if WILDCARD in codes:
            return cls.administrator()
        return cls(granted=cleaned)

    def allows(self, code: str) -> bool:
        """Return True when the set grants *code*.

        Unknown codes are denied for every set — including the administrator wildcard — so a typo in
        a business-layer check fails closed (and is caught by tests) instead of silently granting
        access to whatever the mistyped check was guarding.
        """
        if not is_known(code):
            return False
        if self.is_administrator:
            return True
        return code in self.granted

    def allows_all(self, *codes: str) -> bool:
        """Return True when every code is granted."""
        return all(self.allows(code) for code in codes)

    def allows_any(self, *codes: str) -> bool:
        """Return True when at least one code is granted."""
        return any(self.allows(code) for code in codes)

    def can_see_financials(self) -> bool:
        """Return True when the set may *read* financial information.

        Used by the dashboard, search, notifications and exports as one gate, so financial summaries
        never leak to a role that only records transactions (for example a receptionist who takes
        payments but must not see revenue reports).
        """
        if self.is_administrator:
            return True
        return bool(self.granted & FINANCE_VIEW_CODES)

    def to_codes(self) -> frozenset[str]:
        """Return the granted codes (for persistence and diagnostics)."""
        return self.granted


#: Permission set used while the product is under construction (it has no user accounts and no
#: clinic data yet, so nothing can be leaked). It exists so the shell's full navigation structure can
#: be reviewed, and it is replaced by the authenticated session in Phase 2. Any build that reaches
#: release must run with a real session: ``tools/qa`` verifies that no production entry point uses
#: this constant.
DEVELOPMENT_PREVIEW: Final[PermissionSet] = PermissionSet.administrator()

#: Permission set used before anyone signs in, once authentication exists: it grants nothing.
ANONYMOUS: Final[PermissionSet] = PermissionSet()
