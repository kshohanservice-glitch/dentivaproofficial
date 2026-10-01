"""Navigation model.

The sidebar is generated from this declaration rather than being assembled ad hoc, so the navigation
structure required by the product specification (Practice, Clinical, Billing, Administration) is
visible in one place, every entry declares the permission that gates it, and each entry records the
phase that implements it while the product is under construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NavEntry:
    """One navigation destination."""

    route: str
    label_key: str
    icon: str
    #: Permission required to see and open the destination (``None`` = always available).
    permission: str | None = None
    #: True once the destination is implemented; development scaffolding until then.
    implemented: bool = False
    #: Phase that delivers the destination (shown only while it is not implemented).
    phase: str = ""
    #: What the destination will contain, for the development state.
    planned: tuple[str, ...] = field(default_factory=tuple)
    #: Keyboard shortcut digit (``Ctrl+<n>``) assigned to the first nine entries.
    shortcut_index: int | None = None

    @property
    def is_available(self) -> bool:
        """True when the destination can be opened in this build."""
        return True  # navigation always works; unimplemented modules explain themselves


@dataclass(frozen=True, slots=True)
class NavSection:
    """A group of navigation entries."""

    key: str
    label_key: str
    entries: tuple[NavEntry, ...]


NAV_SECTIONS: tuple[NavSection, ...] = (
    NavSection(
        key="practice",
        label_key="nav.section.practice",
        entries=(
            NavEntry(
                route="dashboard",
                label_key="nav.dashboard",
                icon="layout-dashboard",
                permission="dashboard.view",
                phase="Phase 7",
                planned=(
                    "Today's appointments, queue and new registrations",
                    "Collections and outstanding balances (permission aware)",
                    "Low-stock and expiry alerts, upcoming appointments",
                    "Recent clinical activity and quick actions",
                ),
                shortcut_index=1,
            ),
            NavEntry(
                route="patients",
                label_key="nav.patients",
                icon="users",
                permission="patient.view",
                phase="Phase 4",
                planned=(
                    "Registration with duplicate detection and Bengali content",
                    "Date-based list views and fast multi-field search",
                    "Longitudinal patient profile with timeline and attachments",
                ),
                shortcut_index=2,
            ),
            NavEntry(
                route="appointments",
                label_key="nav.appointments",
                icon="calendar-days",
                permission="appointment.view",
                phase="Phase 5",
                planned=(
                    "Day and week calendar with dentist columns",
                    "Booking with conflict detection and status history",
                    "Status workflow: confirmed, checked in, completed, no-show",
                ),
                shortcut_index=3,
            ),
            NavEntry(
                route="queue",
                label_key="nav.queue",
                icon="list-ordered",
                permission="queue.view",
                phase="Phase 5",
                planned=(
                    "Waiting room list with per-dentist queues",
                    "Token numbers, call/start/complete actions",
                    "Synchronisation with visits and appointments",
                ),
                shortcut_index=4,
            ),
        ),
    ),
    NavSection(
        key="clinical",
        label_key="nav.section.clinical",
        entries=(
            NavEntry(
                route="treatments",
                label_key="nav.treatments",
                icon="stethoscope",
                permission="visit.view",
                phase="Phase 4",
                planned=(
                    "Treatment catalogue with categories, codes and default prices",
                    "Clinical visits with findings, diagnosis and performed treatment",
                    "Adult and pediatric dental chart with per-tooth history",
                ),
                shortcut_index=5,
            ),
            NavEntry(
                route="prescriptions",
                label_key="nav.prescriptions",
                icon="pill",
                permission="prescription.view",
                phase="Phase 5",
                planned=(
                    "Multi-medicine prescriptions with dose, duration and instructions",
                    "Structured C/C, O/E, Dx and advice plus free clinical text",
                    "Premium print and PDF output for A4, A5 and thermal printers",
                ),
                shortcut_index=6,
            ),
            NavEntry(
                route="referrals",
                label_key="nav.referrals",
                icon="forward",
                permission="referral.view",
                phase="Phase 4",
                planned=(
                    "Outgoing and incoming referrals with reason and destination",
                    "Follow-up tracking and referral history in the patient timeline",
                ),
            ),
        ),
    ),
    NavSection(
        key="billing",
        label_key="nav.section.billing",
        entries=(
            NavEntry(
                route="invoices",
                label_key="nav.invoices",
                icon="receipt-text",
                permission="invoice.view",
                phase="Phase 6",
                planned=(
                    "Invoices with treatment and product lines, discounts and adjustments",
                    "Paid, partially paid, unpaid and void states with clear stamping",
                    "Print and PDF output with payment history",
                ),
                shortcut_index=7,
            ),
            NavEntry(
                route="payments",
                label_key="nav.payments",
                icon="banknote",
                permission="payment.view",
                phase="Phase 6",
                planned=(
                    "Multiple payments per invoice across cash, bank, card and mobile wallets",
                    "Daily collections with payment-method breakdown",
                    "Immutable payment history with audited voiding",
                ),
                shortcut_index=8,
            ),
            NavEntry(
                route="inventory",
                label_key="nav.inventory",
                icon="package",
                permission="inventory.view",
                phase="Phase 6",
                planned=(
                    "Items, suppliers, batches and unit costs",
                    "Purchase, usage and adjustment movements with a stock ledger",
                    "Low-stock and expiry alerts",
                ),
            ),
            NavEntry(
                route="accounting",
                label_key="nav.accounting",
                icon="calculator",
                permission="finance.accounting.view",
                phase="Phase 6",
                planned=(
                    "Expenses with configurable categories and audited records",
                    "Other income and clinic-level financial summaries",
                    "Income, expense, collection and receivable reporting",
                ),
            ),
            NavEntry(
                route="reports",
                label_key="nav.reports",
                icon="chart-column",
                permission="finance.report.view",
                phase="Phase 6",
                planned=(
                    "Daily, weekly, monthly, quarterly and yearly financial analysis",
                    "Patient, clinical and inventory operational reports",
                    "CSV and PDF export with permission enforcement",
                ),
                shortcut_index=9,
            ),
        ),
    ),
    NavSection(
        key="administration",
        label_key="nav.section.administration",
        entries=(
            NavEntry(
                route="staff",
                label_key="nav.staff",
                icon="user-cog",
                permission="staff.view",
                phase="Phase 3",
                planned=(
                    "Staff and user accounts with role assignment",
                    "Roles and granular permissions including financial restrictions",
                    "Dentist profiles with multiple designations and qualifications",
                ),
            ),
            NavEntry(
                route="backup",
                label_key="nav.backup",
                icon="database-backup",
                permission="backup.view",
                phase="Phase 8",
                planned=(
                    "Verified backups that include patient attachments",
                    "Manual and scheduled backups (7, 15 or 30 days)",
                    "Safe restore with an automatic pre-restore safety backup",
                ),
            ),
            NavEntry(
                route="audit",
                label_key="nav.audit",
                icon="rotate-ccw",
                permission="audit.view",
                phase="Phase 2",
                planned=(
                    "Append-only audit trail of security and business critical actions",
                    "Filtering by user, action, entity and date",
                    "Unexported detail for administrators and auditors",
                ),
            ),
            NavEntry(
                route="settings",
                label_key="nav.settings",
                icon="settings",
                permission="settings.view",
                phase="Phase 3",
                planned=(
                    "Clinic identity, dentists, printing profiles and paper sizes",
                    "Security policy including the automatic lock timeout",
                    "Backup schedule, catalogues and data management",
                ),
            ),
            NavEntry(
                route="about",
                label_key="nav.about",
                icon="info",
                implemented=True,
            ),
        ),
    ),
)

#: Route used when the application starts.
DEFAULT_ROUTE = "dashboard"


def all_entries() -> tuple[NavEntry, ...]:
    """Return every navigation entry in sidebar order."""
    return tuple(entry for section in NAV_SECTIONS for entry in section.entries)


def entry_for(route: str) -> NavEntry | None:
    """Return the navigation entry for a route, if it is part of the navigation."""
    return next((entry for entry in all_entries() if entry.route == route), None)


def shortcut_map() -> dict[int, str]:
    """Return ``Ctrl+<digit>`` assignments as ``{1: 'dashboard', …}``."""
    return {
        entry.shortcut_index: entry.route
        for entry in all_entries()
        if entry.shortcut_index is not None
    }


def unimplemented_routes() -> tuple[str, ...]:
    """Return the routes that are still development scaffolding.

    The release audit requires this to be empty: it is the machine-checkable proof that no module
    placeholder reached the final build.
    """
    return tuple(entry.route for entry in all_entries() if not entry.implemented)
