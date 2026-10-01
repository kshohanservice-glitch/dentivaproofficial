"""Filesystem layout for Dentiva Pro.

The data root is resolved in a deliberate order so the product works on managed clinic PCs without
administrator rights, while still preferring the machine-wide location when it is usable:

1. ``DENTIVAPRO_DATA_ROOT`` environment variable (development, tests, and support scenarios),
2. the ``data_root`` recorded in the machine configuration (chosen by the administrator),
3. ``%PROGRAMDATA%\\DentivaPro\\data`` when it exists and is writable,
4. the per-user application data directory (``platformdirs``), e.g.
   ``%LOCALAPPDATA%\\DentivaPro\\data`` on Windows.

Nothing here creates directories as a side effect of reading a path; call
:meth:`AppPaths.ensure_directories` explicitly.
"""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

from dentivapro.core.errors import StorageError
from dentivapro.version import APP_SLUG

ENV_DATA_ROOT = "DENTIVAPRO_DATA_ROOT"
ENV_MACHINE_CONFIG = "DENTIVAPRO_MACHINE_CONFIG"

_SUBDIRECTORIES = (
    "attachments",
    "backups",
    "exports",
    "logs",
    "restore-staging",
    ".locks",
    ".trash",
)


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Resolved absolute paths used by the application."""

    data_root: Path
    machine_config_file: Path
    install_dir: Path

    # ---- derived paths -------------------------------------------------
    @property
    def database_file(self) -> Path:
        return self.data_root / "dentivapro.db"

    @property
    def activation_file(self) -> Path:
        return self.data_root / "activation.dat"

    @property
    def attachments_dir(self) -> Path:
        return self.data_root / "attachments"

    @property
    def backups_dir(self) -> Path:
        return self.data_root / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.data_root / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_root / "logs"

    @property
    def restore_staging_dir(self) -> Path:
        return self.data_root / "restore-staging"

    @property
    def locks_dir(self) -> Path:
        return self.data_root / ".locks"

    @property
    def trash_dir(self) -> Path:
        return self.data_root / ".trash"

    @property
    def all_directories(self) -> tuple[Path, ...]:
        return (
            self.data_root,
            self.attachments_dir,
            self.backups_dir,
            self.exports_dir,
            self.logs_dir,
            self.restore_staging_dir,
            self.locks_dir,
            self.trash_dir,
        )

    # ---- operations ----------------------------------------------------
    def ensure_directories(self) -> None:
        """Create every directory the application needs, with clear errors on failure."""
        for directory in self.all_directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:  # pragma: no cover - depends on host permissions
                raise StorageError(
                    f"The folder '{directory}' could not be created.",
                    context={"path": str(directory), "os_error": exc.strerror},
                    cause=exc,
                ) from exc

    def is_usable_data_root(self) -> bool:
        """Return True when the data root can be written to."""
        return directory_is_writable(
            self.data_root if self.data_root.exists() else self.data_root.parent
        )


def directory_is_writable(directory: Path) -> bool:
    """Return True if *directory* exists and accepts new files."""
    if not directory.exists() or not directory.is_dir():
        return False
    probe = directory / ".dentivapro-write-probe"
    try:
        probe.write_text("probe", encoding="utf-8")
    except OSError:
        return False
    finally:
        with suppress(OSError):  # pragma: no cover - best effort cleanup
            probe.unlink(missing_ok=True)
    return True


def default_machine_config_file() -> Path:
    """Return the machine configuration location (``%PROGRAMDATA%`` first, user dir as fallback)."""
    override = os.environ.get(ENV_MACHINE_CONFIG)
    if override:
        return Path(override).expanduser()

    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        candidate_dir = Path(program_data) / APP_SLUG
        if candidate_dir.exists() and directory_is_writable(candidate_dir):
            return candidate_dir / "machine.json"
        if not candidate_dir.exists():
            try:  # the installer normally creates this; create it if the clinic user may write it
                candidate_dir.mkdir(parents=True, exist_ok=True)
                if directory_is_writable(candidate_dir):
                    return candidate_dir / "machine.json"
            except OSError:
                pass

    dirs = PlatformDirs(appname=APP_SLUG, appauthor=False, roaming=False)
    return Path(dirs.user_data_dir) / "machine.json"


def default_data_root(machine_data_root: Path | None = None) -> Path:
    """Resolve the data root following the documented order."""
    override = os.environ.get(ENV_DATA_ROOT)
    if override:
        return Path(override).expanduser().resolve()

    if machine_data_root is not None:
        return Path(machine_data_root).expanduser()

    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        candidate = Path(program_data) / APP_SLUG / "data"
        parent = candidate.parent
        parent_usable = parent.exists() and directory_is_writable(parent)
        if candidate.exists() and directory_is_writable(candidate):
            return candidate
        if parent_usable:
            return candidate

    dirs = PlatformDirs(appname=APP_SLUG, appauthor=False, roaming=False)
    return Path(dirs.user_data_dir) / "data"


def install_dir() -> Path:
    """Return the directory the application was launched from (works frozen and from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def build_paths(
    machine_data_root: Path | None = None, machine_config_file: Path | None = None
) -> AppPaths:
    """Build an :class:`AppPaths` from the machine configuration and the environment."""
    config_file = machine_config_file or default_machine_config_file()
    return AppPaths(
        data_root=default_data_root(machine_data_root),
        machine_config_file=config_file,
        install_dir=install_dir(),
    )
