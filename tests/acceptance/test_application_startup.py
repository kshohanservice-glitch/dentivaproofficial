"""Acceptance: the application starts, prepares its storage and reports its state.

This is the foundation equivalent of the clean-machine start-up check: a fresh data root must produce a
usable database, complete the schema, register the installation and be ready to show the shell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dentivapro.app import ApplicationContext
from dentivapro.core.paths import build_paths
from dentivapro.data.repos.meta_repo import MetaRepository

if TYPE_CHECKING:
    from pathlib import Path


class TestFreshStart:
    def test_creates_every_directory_it_needs(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            for directory in context.paths.all_directories:
                assert directory.exists(), directory
        finally:
            context.shutdown()

    def test_database_is_created_and_migrated(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            database = context.require_database()
            assert database.integrity_check() == "ok"
            assert database.schema_version >= 1
            assert context.status.schema_version >= 1
        finally:
            context.shutdown()

    def test_setup_is_reported_as_incomplete_on_a_fresh_install(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            assert context.status.setup_complete is False
            assert context.load_clinic_identity().is_configured is False
        finally:
            context.shutdown()

    def test_installation_is_registered_for_support(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            repo = MetaRepository(context.require_database())
            assert repo.installation_id()
            assert context.machine.machine_label
        finally:
            context.shutdown()

    def test_machine_configuration_is_written(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            assert context.paths.machine_config_file.exists()
            assert context.machine.installation_id
        finally:
            context.shutdown()

    def test_log_file_is_created(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            logs = list(context.paths.logs_dir.glob("dentivapro-*.jsonl"))
            assert logs, "the application must write a log file for support"
            assert logs[0].stat().st_size > 0
        finally:
            context.shutdown()


class TestRestart:
    def test_second_start_reuses_the_existing_database(self, data_root: Path) -> None:
        first = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        first.start()
        installation_id = first.machine.installation_id
        first.shutdown()

        second = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        second.start()
        try:
            assert second.machine.installation_id == installation_id
            assert second.require_database().integrity_check() == "ok"
        finally:
            second.shutdown()

    def test_settings_survive_a_restart(self, data_root: Path) -> None:
        first = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        first.start()
        first.settings_service().set("clinic.display_name", "Sunrise Dental Care")
        first.shutdown()

        second = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        second.start()
        try:
            assert second.load_clinic_identity().name == "Sunrise Dental Care"
        finally:
            second.shutdown()


class TestStartupFailures:
    def test_unwritable_data_root_is_reported_clearly(self, tmp_path: Path) -> None:
        from dentivapro.core.errors import StorageError

        blocked = tmp_path / "file-not-directory"
        blocked.write_text("x", encoding="utf-8")
        context = ApplicationContext(paths=build_paths(machine_data_root=blocked / "data"))
        with pytest.raises((StorageError, OSError)):
            context.start()

    def test_newer_schema_is_refused(self, data_root: Path) -> None:
        from dentivapro.core.errors import SchemaVersionError

        first = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        first.start()
        first.require_database().set_schema_version(9999)
        first.shutdown()

        second = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        with pytest.raises(SchemaVersionError):
            second.start()
        assert second.database is None

    def test_shutdown_is_safe_to_call_twice(self, data_root: Path) -> None:
        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        context.shutdown()
        context.shutdown()


class TestHeadlessCheck:
    def test_check_mode_reports_a_healthy_installation(self, data_root: Path) -> None:
        from dentivapro.__main__ import EXIT_OK, _run_check

        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            assert _run_check(context, True) == EXIT_OK
        finally:
            context.shutdown()

    def test_check_mode_fails_when_fonts_are_missing(self, data_root: Path) -> None:
        from dentivapro.__main__ import EXIT_STARTUP_FAILURE, _run_check

        context = ApplicationContext(paths=build_paths(machine_data_root=data_root))
        context.start()
        try:
            assert _run_check(context, False) == EXIT_STARTUP_FAILURE
        finally:
            context.shutdown()


class TestVersionFlag:
    def test_version_flag_prints_the_product_version(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from dentivapro.__main__ import main
        from dentivapro.version import APP_NAME, __version__

        assert main(["--version"]) == 0
        captured = capsys.readouterr()
        assert APP_NAME in captured.out
        assert __version__ in captured.out
