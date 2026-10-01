"""Command-line entry point.

Launches the Qt application, applies the design system, builds the application context and shows the
main window. Any failure during startup is reported to the user in plain language and logged with a
correlation id — the application never exits silently.

The ``--version`` and ``--check`` flags make the packaged build verifiable from a script, which the
CI packaging smoke test relies on.
"""

from __future__ import annotations

import argparse
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from dentivapro.version import APP_NAME, __version__

if TYPE_CHECKING:
    from dentivapro.app import ApplicationContext
    from dentivapro.ui.shell.main_window import MainWindow

EXIT_OK = 0
EXIT_STARTUP_FAILURE = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dentivapro", description=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Use a specific data folder (support and testing); overrides the machine configuration.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the product version and exit.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Start, verify storage and the database, print a summary and exit (headless).",
    )
    parser.add_argument(
        "--console-log",
        action="store_true",
        help="Also write log records to the console (support use).",
    )
    parser.add_argument(
        "--route",
        default=None,
        help="Open a specific screen at start-up (support use).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the application (or one of its diagnostic modes)."""
    args = _build_parser().parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return EXIT_OK

    # Qt must know the platform before any widget is created.
    from PySide6.QtCore import Qt  # noqa: PLC0415 - Qt loads after arguments are parsed
    from PySide6.QtWidgets import QApplication  # noqa: PLC0415 - lazy Qt import

    from dentivapro.app import ApplicationContext  # noqa: PLC0415 - keeps --version light
    from dentivapro.core.i18n import t  # noqa: PLC0415
    from dentivapro.ui.design.fonts import fonts_healthy  # noqa: PLC0415
    from dentivapro.ui.design.theme import apply_theme  # noqa: PLC0415
    from dentivapro.ui.errors import (  # noqa: PLC0415
        install_exception_hook,
        report_exception,
        show_error_dialog,
    )

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Dentiva Pro")
    app.setQuitOnLastWindowClosed(True)
    apply_theme(app)
    install_exception_hook(app)

    context = ApplicationContext(data_root=args.data_root, console_logging=args.console_log)
    try:
        context.start()
    except Exception as exc:  # noqa: BLE001 - startup failures must be explained, not crashed
        error = report_exception(exc, context="application startup")
        show_error_dialog(error)
        return EXIT_STARTUP_FAILURE

    if args.check:
        return _run_check(context, fonts_healthy())

    from dentivapro.ui.shell.main_window import MainWindow, window_icon  # noqa: PLC0415

    window = MainWindow(window_icon=window_icon())
    _register_screens(window, context)

    clinic = context.load_clinic_identity()
    window.set_clinic_identity(clinic.name, clinic.header_meta())
    if not clinic.is_configured:
        window.set_clinic_identity(
            t("app.header.clinic_unknown"), t("app.header.clinic_setup_hint")
        )
    window.set_permissions(context.permissions)
    window.start(args.route)
    exit_code = app.exec()
    context.shutdown()
    return int(exit_code)


def _register_screens(window: MainWindow, context: ApplicationContext) -> None:
    """Register every screen factory with the shell.

    The UI modules are imported here rather than at module level so that ``--version``, ``--check`` and
    a failed start-up never pay for loading Qt widgets.
    """
    from dentivapro.ui.screens.about_screen import AboutScreen  # noqa: PLC0415 - lazy UI import
    from dentivapro.ui.screens.pending_screen import build_pending_screen  # noqa: PLC0415
    from dentivapro.ui.shell.navigation import all_entries  # noqa: PLC0415

    for entry in all_entries():
        if entry.route == "about":
            window.register_screen(
                entry.route,
                partial(AboutScreen, paths=context.paths),
                permission=entry.permission,
            )
            continue
        window.register_screen(
            entry.route,
            partial(build_pending_screen, entry, context=context),
            permission=entry.permission,
        )


def _run_check(context: ApplicationContext, fonts_ok: bool) -> int:
    """Headless self-check used by the packaging smoke test.

    The health verdict is produced **before** the context shuts down: closing the database first and
    then asking it for ``PRAGMA integrity_check`` would only prove that a closed handle still raises.
    """
    database = context.require_database()
    try:
        info = database.info()
        integrity = database.integrity_check()
        healthy = integrity == "ok" and info.foreign_keys
        print(f"product         : {APP_NAME} {__version__}")
        print(f"data root       : {context.paths.data_root}")
        print(f"database        : {info.path}")
        print(f"journal mode    : {info.journal_mode}")
        print(f"schema version  : {info.schema_version}")
        print(f"sqlite version  : {info.sqlite_version}")
        print(f"foreign keys    : {'on' if info.foreign_keys else 'off'}")
        print(f"integrity check : {integrity}")
        print(f"bundled fonts   : {'ok' if fonts_ok else 'MISSING'}")
        print(f"tables          : {len(database.table_names())}")
        print(f"setup complete  : {'yes' if context.status.setup_complete else 'no'}")
    finally:
        context.shutdown()
    return EXIT_OK if healthy and fonts_ok else EXIT_STARTUP_FAILURE


__all__ = ["main", "EXIT_OK", "EXIT_STARTUP_FAILURE"]


if __name__ == "__main__":  # pragma: no cover - module executed directly
    from dentivapro.core.errors import to_user_error as _to_user_error  # noqa: F401, PLC0415

    raise SystemExit(main())
