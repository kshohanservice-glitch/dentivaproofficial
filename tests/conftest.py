"""Shared test fixtures.

Tests run headless (offscreen Qt) so the suite works identically on a developer machine and in CI, and
every test that touches storage gets its own temporary data root so a real clinic's data can never be
affected.

The stubbed-platform environment is documented in ``docs/environment-and-limitations.md``: on Linux
build agents the Qt libraries need a few desktop libraries that are not installed; the sandbox
scaffolding supplies loader-only stubs through ``LD_LIBRARY_PATH`` and is never part of the product.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from typing import TYPE_CHECKING

from dentivapro.core.paths import build_paths  # noqa: E402
from dentivapro.data.db.connection import Database  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator
from functools import partial


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path of the repository root."""
    return REPO_ROOT


@pytest.fixture()
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """An isolated data root for one test."""
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DENTIVAPRO_DATA_ROOT", str(root))
    monkeypatch.setenv("DENTIVAPRO_MACHINE_CONFIG", str(tmp_path / "machine.json"))
    yield root


@pytest.fixture()
def db(data_root: Path) -> Iterator[Database]:
    """An open, migrated database in an isolated data root."""
    from dentivapro.data.db.migrations import MigrationRunner

    database = Database(data_root / "dentivapro.db").open()
    MigrationRunner(database).apply_pending()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture()
def fresh_db(data_root: Path) -> Iterator[Database]:
    """An open database with no migrations applied (used by migration tests)."""
    database = Database(data_root / "fresh.db").open()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture()
def settings_service(db: Database):
    """A settings service bound to the isolated database."""
    from dentivapro.data.repos.settings_repo import SettingsRepository
    from dentivapro.services.settings_service import SettingsService

    return SettingsService(SettingsRepository(db))


@pytest.fixture()
def app_context(data_root: Path):
    """A fully started application context in an isolated data root."""
    from dentivapro.app import ApplicationContext

    context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
    context.start()
    try:
        yield context
    finally:
        context.shutdown()


@pytest.fixture(scope="session")
def qt_app():
    """A single ``QApplication`` for the whole test session (Qt allows only one)."""
    from PySide6.QtWidgets import QApplication

    from dentivapro.ui.design.theme import apply_theme

    app = QApplication.instance() or QApplication(sys.argv[:1])
    apply_theme(app)
    return app


class _GoldenDisplayPaths:
    """Display-only stand-in for the real data paths (see ``GOLDEN_PATHS``)."""

    data_root = "C:/ProgramData/Dentiva Pro"
    database_file = "C:/ProgramData/Dentiva Pro/dentivapro.db"


#: Values the golden-image tests pin so a baseline never contains a temporary folder name, the real
#: machine's version numbers or the day the test happened to run.
#: The clinic clock is a local wall-clock time (the header only shows a date), so no tzinfo is needed.
GOLDEN_NOW = datetime(2026, 10, 1, 9, 15)  # noqa: DTZ001
GOLDEN_PATHS = _GoldenDisplayPaths()
GOLDEN_DIAGNOSTICS = {
    "python": "3.12.4",
    "qt": "6.11.2",
    "platform": "Windows 11 (AMD64)",
    "build": "3.12",
}


@pytest.fixture()
def golden_window(qt_app, app_context):
    """A shell wired like ``shell_window`` but with every environment value pinned.

    Golden images are compared between runs and between platforms, so anything that varies with the
    machine (data-root path, Python/Qt/platform strings) or with the calendar (the header date) is
    replaced by a fixed value here. Only the layout is under test.
    """
    from dentivapro.ui.screens.about_screen import AboutScreen
    from dentivapro.ui.screens.pending_screen import build_pending_screen
    from dentivapro.ui.shell.main_window import MainWindow
    from dentivapro.ui.shell.navigation import all_entries

    window = MainWindow(now=lambda: GOLDEN_NOW)
    for entry in all_entries():
        if entry.route == "about":
            window.register_screen(
                entry.route,
                partial(AboutScreen, paths=GOLDEN_PATHS, diagnostics=GOLDEN_DIAGNOSTICS),
                permission=entry.permission,
            )
        else:
            window.register_screen(
                entry.route,
                partial(build_pending_screen, entry, context=app_context),
                permission=entry.permission,
            )
    window.resize(1360, 860)
    window.start("about")
    qt_app.processEvents()
    yield window
    window.close()


@pytest.fixture()
def shell_window(qt_app, app_context):
    """A main window wired to the real screens, sized to a standard 1360 × 860 viewport."""
    from dentivapro.ui.screens.about_screen import AboutScreen
    from dentivapro.ui.screens.pending_screen import build_pending_screen
    from dentivapro.ui.shell.main_window import MainWindow
    from dentivapro.ui.shell.navigation import all_entries

    window = MainWindow()
    for entry in all_entries():
        if entry.route == "about":
            window.register_screen(
                entry.route,
                partial(AboutScreen, paths=app_context.paths),
                permission=entry.permission,
            )
        else:
            window.register_screen(
                entry.route,
                partial(build_pending_screen, entry, context=app_context),
                permission=entry.permission,
            )
    window.resize(1360, 860)
    window.start("about")
    qt_app.processEvents()
    yield window
    window.close()
