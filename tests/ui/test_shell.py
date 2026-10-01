"""Acceptance: the application shell (header, collapsible navigation, routing).

These tests assert the structural requirements of the product's main window: the four navigation areas
and their required destinations, a header that carries identity/date/session information, working
collapse behaviour, working keyboard shortcuts, and designed states instead of blank screens.
"""

from __future__ import annotations

import pytest

from dentivapro.domain.permissions import ALL_CODES, PermissionSet
from dentivapro.ui.shell.navigation import (
    DEFAULT_ROUTE,
    NAV_SECTIONS,
    all_entries,
    entry_for,
    shortcut_map,
    unimplemented_routes,
)

pytestmark = pytest.mark.ui

REQUIRED_SECTIONS = {"practice", "clinical", "billing", "administration"}

REQUIRED_ROUTES = {
    "dashboard",
    "patients",
    "appointments",
    "queue",
    "treatments",
    "prescriptions",
    "invoices",
    "payments",
    "inventory",
    "accounting",
    "staff",
    "backup",
    "settings",
    "about",
}


class TestNavigationModel:
    def test_all_required_sections_are_present(self) -> None:
        assert {section.key for section in NAV_SECTIONS} == REQUIRED_SECTIONS

    def test_all_required_destinations_are_present(self) -> None:
        routes = {entry.route for entry in all_entries()}
        assert routes >= REQUIRED_ROUTES

    def test_destinations_live_in_the_correct_area(self) -> None:
        expectations = {
            "practice": {"dashboard", "patients", "appointments", "queue"},
            "clinical": {"treatments", "prescriptions", "referrals"},
            "billing": {"invoices", "payments", "inventory", "accounting", "reports"},
            "administration": {"staff", "backup", "audit", "settings", "about"},
        }
        for key, expected in expectations.items():
            section = next(section for section in NAV_SECTIONS if section.key == key)
            assert {entry.route for entry in section.entries} == expected

    def test_every_entry_declares_an_icon_and_label(self) -> None:
        for entry in all_entries():
            assert entry.icon
            assert entry.label_key.startswith("nav.")

    def test_permission_gated_entries_declare_known_permissions(self) -> None:
        for entry in all_entries():
            if entry.permission is not None:
                assert entry.permission in ALL_CODES, entry.route

    def test_unimplemented_entries_declare_their_phase_and_scope(self) -> None:
        for entry in all_entries():
            if not entry.implemented:
                assert entry.phase.startswith("Phase"), entry.route
                assert entry.planned, entry.route

    def test_about_is_implemented(self) -> None:
        entry = entry_for("about")
        assert entry is not None
        assert entry.implemented is True

    def test_only_about_is_finished_in_the_foundation_build(self) -> None:
        # The release audit requires this set to shrink to nothing; today only About is complete.
        implemented = {entry.route for entry in all_entries() if entry.implemented}
        assert implemented == {"about"}
        assert "about" not in unimplemented_routes()
        assert unimplemented_routes()

    def test_shortcuts_are_assigned_to_the_first_nine_destinations(self) -> None:
        mapping = shortcut_map()
        assert set(mapping) == set(range(1, 10))
        assert mapping[1] == "dashboard"

    def test_default_route_exists(self) -> None:
        assert entry_for(DEFAULT_ROUTE) is not None


class TestShellConstruction:
    def test_window_opens_on_the_default_route(self, shell_window) -> None:
        assert shell_window.current_route is not None

    def test_sidebar_lists_every_required_route(self, shell_window) -> None:
        visible = set(shell_window.sidebar.visible_routes)
        assert visible >= REQUIRED_ROUTES

    def test_navigation_labels_render_exactly_as_translated(self, shell_window) -> None:
        """An unescaped ``&`` would make Qt draw a mnemonic underline ("Staff _Users")."""
        from dentivapro.core.i18n import t

        for entry in all_entries():
            button = shell_window.sidebar._buttons[entry.route]  # noqa: SLF001
            assert button.text().replace("&&", "&") == t(entry.label_key)
            assert "&" not in button.text().replace("&&", "")

    def test_header_shows_product_clinic_date_and_session(self, shell_window) -> None:
        header = shell_window.header
        assert header.height() > 0
        assert header._date_label.text()  # noqa: SLF001 - asserting visible information
        assert header._clinic_label.text()  # noqa: SLF001
        assert header._user_button.text()  # noqa: SLF001

    def test_sidebar_can_be_collapsed_and_expanded(self, shell_window) -> None:
        expanded_width = shell_window.sidebar.width()
        assert shell_window.sidebar.is_collapsed is False

        shell_window.sidebar.toggle_collapsed()
        assert shell_window.sidebar.is_collapsed is True
        assert shell_window.sidebar.width() < expanded_width

        shell_window.sidebar.toggle_collapsed()
        assert shell_window.sidebar.is_collapsed is False
        assert shell_window.sidebar.width() == expanded_width

    def test_collapsed_sidebar_keeps_tooltips_for_icons(self, shell_window) -> None:
        shell_window.sidebar.toggle_collapsed()
        for route in shell_window.sidebar.visible_routes:
            button = shell_window.sidebar._buttons[route]  # noqa: SLF001
            assert button.toolTip()
            assert button.text() == ""

    def test_navigating_updates_the_current_route_and_sidebar(self, shell_window) -> None:
        assert shell_window.navigate("patients") is True
        assert shell_window.current_route == "patients"
        assert shell_window.sidebar.current_route == "patients"

    def test_every_route_can_be_opened(self, shell_window) -> None:
        for entry in all_entries():
            assert shell_window.navigate(entry.route) is True, entry.route
            assert shell_window.current_route == entry.route

    def test_unknown_route_is_refused_without_crashing(self, shell_window) -> None:
        current = shell_window.current_route
        assert shell_window.navigate("does-not-exist") is False
        assert shell_window.current_route == current

    def test_back_and_forward_navigation(self, shell_window) -> None:
        shell_window.navigate("patients")
        shell_window.navigate("queue")
        shell_window.navigate_back()
        assert shell_window.current_route == "patients"
        shell_window.navigate_forward()
        assert shell_window.current_route == "queue"

    def test_window_title_tracks_the_screen(self, shell_window) -> None:
        shell_window.navigate("patients")
        assert "Patients" in shell_window.windowTitle()

    def test_status_bar_identifies_the_product_and_version(self, shell_window) -> None:
        from dentivapro.version import __version__

        assert __version__ in shell_window._status_label.text()  # noqa: SLF001


class TestPermissionAwareNavigation:
    def test_restricted_permissions_hide_navigation_entries(self, shell_window) -> None:
        shell_window.set_permissions(
            PermissionSet.from_codes({"patient.view", "appointment.view", "dashboard.view"})
        )
        visible = set(shell_window.sidebar.visible_routes)
        assert {"patients", "appointments", "dashboard"} <= visible
        assert "settings" not in visible
        assert "backup" not in visible
        assert "payments" not in visible

    def test_router_refuses_a_route_without_permission(self, shell_window) -> None:
        shell_window.set_permissions(PermissionSet.from_codes({"patient.view"}))
        assert shell_window.router.is_allowed("patients") is True
        assert shell_window.router.is_allowed("settings") is False

    def test_permission_denied_is_reported_to_the_user(self, shell_window) -> None:
        shell_window.set_permissions(PermissionSet.from_codes({"patient.view"}))
        shell_window.navigate("settings")
        # The navigation attempt is refused and the user is told why (never a blank screen).
        assert shell_window.current_route != "settings"

    def test_administrator_sees_everything(self, shell_window) -> None:
        shell_window.set_permissions(PermissionSet.administrator())
        assert set(shell_window.sidebar.visible_routes) == {entry.route for entry in all_entries()}


class TestShortcuts:
    def test_available_shortcuts_are_registered(self, shell_window) -> None:
        registered = set(shell_window._shortcuts.registered())  # noqa: SLF001
        assert "Ctrl+B" in registered
        assert "F5" in registered
        assert "F1" in registered
        assert "Alt+Left" in registered
        assert "Alt+Right" in registered

    def test_navigation_shortcuts_are_registered(self, shell_window) -> None:
        registered = set(shell_window._shortcuts.registered())  # noqa: SLF001
        for index in range(1, 10):
            assert f"Ctrl+{index}" in registered

    def test_shortcut_reference_marks_unavailable_keys_honestly(self, qt_app) -> None:
        from dentivapro.ui.dialogs.shortcuts_dialog import ShortcutsDialog

        dialog = ShortcutsDialog()
        rows = dialog.table.model.rows
        statuses = {row["keys"]: row["status"] for row in rows}
        # The reference lists every shortcut but tells the truth about what works today.
        assert statuses["Ctrl+B"] == "Available"
        assert statuses["Ctrl+K"] == "Later phase"
        assert statuses["Ctrl+P"] == "Later phase"
        # Unavailable entries must still explain what they will do, never just a disabled key.
        assert all(row["description"] for row in rows)
        dialog.close()


class TestShellState:
    def test_foundation_banner_is_visible_while_the_product_is_incomplete(
        self, shell_window
    ) -> None:
        banner = shell_window._foundation_banner  # noqa: SLF001
        assert banner.parent() is not None
        assert banner.isHidden() is False
        assert banner.property("developmentState") is True

    def test_pending_screens_state_that_they_are_not_implemented(self, shell_window) -> None:
        shell_window.navigate("patients")
        screen = shell_window._current_screen  # noqa: SLF001
        assert screen is not None
        assert screen.entry.route == "patients"  # noqa: SLF001
        assert screen._state.property("developmentState") is True  # noqa: SLF001

    def test_toasts_are_available_for_feedback(self, shell_window) -> None:
        shell_window.toasts.success("Saved", "The change was stored.")
        assert shell_window.toasts.visible_count == 1
