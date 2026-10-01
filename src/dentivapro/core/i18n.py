"""Single message catalogue for all user-facing text.

The product's interface language is professional English, but no string is ever written inline in a
widget: every label resolves through this catalogue. That keeps the interface consistent, makes the
wording reviewable in one place, and leaves the door open to a full Bengali interface later without
touching the UI code.

Bengali *content* (patient names, clinical notes, printed documents) is fully supported elsewhere —
this module is about interface copy only.
"""

from __future__ import annotations

from typing import Final

from dentivapro.version import APP_NAME, CREATOR_EMAIL, CREATOR_NAME

#: Interface language used for messages ("bn" support is added for selected printed labels).
DEFAULT_LOCALE: Final[str] = "en"

MESSAGES: Final[dict[str, str]] = {
    # ---- application shell --------------------------------------------
    "app.title": f"{APP_NAME}",
    "app.window_title": "{screen} · " + APP_NAME,
    "app.tagline": "Dental clinic management",
    "app.header.clinic_unknown": "Clinic setup not completed",
    "app.header.clinic_setup_hint": "Clinic identity appears here after the setup wizard (Phase 5).",
    "app.header.today": "Today",
    "app.header.search_placeholder": "Search patients, invoices, items… (Ctrl+K)",
    "app.header.search_available_later": "Global search arrives in Phase 12.",
    "app.header.notifications": "Notifications",
    "app.header.notifications_empty": "No notifications yet",
    "app.header.notifications_empty_hint": (
        "Appointment reminders, low-stock and backup alerts will appear here."
    ),
    "app.header.notifications_later": "The notification centre is implemented in Phase 12.",
    "app.header.user": "Signed-in user",
    "app.header.user_none": "Not signed in",
    "app.header.user_hint": "Authentication and sessions arrive in Phase 3.",
    "app.header.lock": "Lock now",
    "app.header.lock_hint": "Session locking arrives in Phase 3.",
    "app.header.sign_out": "Sign out",
    "app.header.sign_out_hint": "Sessions arrive in Phase 3.",
    "app.header.help": "Help and diagnostics",
    "app.header.about": "About " + APP_NAME,
    "app.header.shortcuts": "Keyboard shortcuts",
    "app.header.reduce_motion": "Reduce motion",
    "app.header.diagnostics": "Export diagnostics…",
    "app.header.diagnostics_hint": "Available once data management is implemented (Phase 13).",
    # ---- navigation ----------------------------------------------------
    "nav.section.practice": "Practice",
    "nav.section.clinical": "Clinical",
    "nav.section.billing": "Billing",
    "nav.section.administration": "Administration",
    "nav.dashboard": "Dashboard",
    "nav.patients": "Patients",
    "nav.appointments": "Appointments",
    "nav.queue": "Queue",
    "nav.treatments": "Treatments",
    "nav.prescriptions": "Prescriptions",
    "nav.referrals": "Referrals",
    "nav.invoices": "Invoice",
    "nav.payments": "Payments",
    "nav.inventory": "Inventory",
    "nav.accounting": "Accounting",
    "nav.reports": "Reports",
    "nav.staff": "Staff & Users",
    "nav.backup": "Backup & Restore",
    "nav.audit": "Audit Log",
    "nav.settings": "Settings",
    "nav.about": "About",
    "nav.collapse": "Collapse navigation",
    "nav.expand": "Expand navigation",
    # ---- foundation state ---------------------------------------------
    "foundation.banner_title": "Foundation build — clinic setup is not implemented yet",
    "foundation.banner_body": (
        "The application shell, design system, database foundation and packaging are in place. "
        "The first-run setup wizard, authentication and clinic modules are delivered in the phases "
        "listed on each screen. No clinic data exists yet and no module pretends to work."
    ),
    "foundation.pending_title": "{module} is not available in this build yet",
    "foundation.pending_body": (
        "This module is scheduled for {phase} and will be fully implemented, tested and permission "
        "controlled before the final release. Nothing here is a placeholder for shipped "
        "functionality — it is development scaffolding that is removed before release."
    ),
    "foundation.pending_planned": "Planned in this module",
    "foundation.mode_label": "Foundation mode",
    # ---- shared states ---------------------------------------------------
    "state.loading": "Loading…",
    "state.empty_title": "Nothing to show yet",
    "state.empty_body": "Data will appear here once records exist.",
    "state.error_title": "This could not be loaded",
    "state.error_retry": "Try again",
    "state.denied_title": "You do not have permission",
    "state.denied_body": "Ask an administrator if you need access to this area.",
    "state.not_implemented_title": "Not implemented yet",
    "state.copy_details": "Copy diagnostic details",
    "state.details_copied": "Diagnostic details copied to the clipboard",
    # ---- about -----------------------------------------------------------
    "about.title": "About " + APP_NAME,
    "about.product": "Product",
    "about.version": "Version",
    "about.build": "Build",
    "about.created_by": "Created by",
    "about.description": "Description",
    "about.system": "System information",
    "about.data_location": "Data location",
    "about.database": "Database",
    "about.qt_version": "Qt version",
    "about.python_version": "Python version",
    "about.platform": "Operating system",
    "about.notices": "Open-source notices",
    "about.notices_hint": (
        "Third-party components are used under their own licences; the full texts are shown below."
    ),
    "about.copyright": "© 2026 {creator}. All rights reserved.",
    "about.licence": "Licence",
    "about.licence_value": "Proprietary — commercial licence",
    # ---- toasts ----------------------------------------------------------
    "toast.dismiss": "Dismiss",
    "toast.copied": "Copied to the clipboard",
    # ---- dialogs ---------------------------------------------------------
    "dialog.close": "Close",
    "dialog.ok": "OK",
    "dialog.cancel": "Cancel",
    "dialog.copy": "Copy details",
    "dialog.unexpected_title": "Something went wrong",
    "dialog.unexpected_body": (
        "The action could not be completed and your data has not been changed. "
        "The technical details have been written to the application log."
    ),
    "dialog.correlation": "Reference",
    # ---- shortcuts --------------------------------------------------------
    "shortcuts.title": "Keyboard shortcuts",
    "shortcuts.hint": "These shortcuts work anywhere in the application.",
}


class MessageCatalogue:
    """Resolves message keys and reports missing entries loudly in development."""

    def __init__(self, messages: dict[str, str] | None = None) -> None:
        self._messages: dict[str, str] = dict(messages or MESSAGES)
        self._missing: set[str] = set()

    def t(self, key: str, **kwargs: object) -> str:
        """Return the message for *key* with ``str.format`` placeholders applied."""
        template = self._messages.get(key)
        if template is None:
            self._missing.add(key)
            return key
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):  # pragma: no cover - guarded by tests
            self._missing.add(key)
            return template

    @property
    def missing_keys(self) -> frozenset[str]:
        """Keys that were requested but are not defined (checked by the test suite)."""
        return frozenset(self._missing)

    def keys(self) -> frozenset[str]:
        """All defined message keys."""
        return frozenset(self._messages)


_catalogue = MessageCatalogue()


def t(key: str, **kwargs: object) -> str:
    """Translate a message key using the active catalogue."""
    return _catalogue.t(key, **kwargs)


def catalogue() -> MessageCatalogue:
    """Return the active catalogue (used by tests and diagnostics)."""
    return _catalogue


def creator_line() -> str:
    """Return the standard attribution line used on the About screen and printed documents."""
    return f"{CREATOR_NAME} · {CREATOR_EMAIL}"
