"""Application wiring.

:class:`ApplicationContext` is the composition root: it resolves paths, loads machine configuration,
configures logging, opens the database, applies migrations, builds the service objects and exposes the
shared state the shell needs (clinic identity, permissions, status messages).

Keeping construction in one place means every part of the application receives the same services, and
tests can build an isolated context pointing at a temporary data root without touching a real clinic's
data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dentivapro.core.config import MachineConfig, MachineConfigStore
from dentivapro.core.errors import DatabaseError, SchemaVersionError
from dentivapro.core.i18n import t
from dentivapro.core.logging import configure_logging, get_logger, log_event
from dentivapro.core.paths import AppPaths, build_paths
from dentivapro.data.db.connection import Database
from dentivapro.data.db.migrations import MigrationRunner
from dentivapro.data.repos.meta_repo import MetaRepository
from dentivapro.data.repos.sequence_repo import SequenceRepository
from dentivapro.data.repos.settings_repo import SettingsRepository
from dentivapro.domain.permissions import DEVELOPMENT_PREVIEW, PermissionSet
from dentivapro.services.settings_service import SettingsService
from dentivapro.version import __version__

logger = get_logger(__name__)


@dataclass(slots=True)
class ClinicIdentity:
    """What the shell displays about the clinic."""

    name: str = ""
    address: str = ""
    phone: str = ""

    @property
    def is_configured(self) -> bool:
        """True once the clinic has a name (i.e. setup has run)."""
        return bool(self.name.strip())

    def header_meta(self) -> str:
        """A short location line for the header (city / phone)."""
        parts = [part for part in (self.address.strip(), self.phone.strip()) if part]
        return " · ".join(parts)


@dataclass(slots=True)
class AppStatus:
    """Runtime status shown in the status bar and on the dashboard later."""

    setup_complete: bool = False
    activated: bool = False
    schema_version: int = 0
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ApplicationContext:
    """Composition root for a single application process."""

    def __init__(
        self,
        *,
        paths: AppPaths | None = None,
        data_root: Path | None = None,
        console_logging: bool = False,
    ) -> None:
        self.paths: AppPaths = paths or build_paths(machine_data_root=data_root)
        self.console_logging = console_logging
        self.machine_store = MachineConfigStore(self.paths.machine_config_file)
        self.machine: MachineConfig = MachineConfig()
        self.database: Database | None = None
        self.migrations: MigrationRunner | None = None
        self.status = AppStatus()
        self.clinic = ClinicIdentity()
        # Phase 2 replaces this with the permission set of the signed-in session.
        self.permissions: PermissionSet = DEVELOPMENT_PREVIEW
        self.session_user: str = ""
        self.session_role: str = ""

    # ---- startup ------------------------------------------------------------
    def start(self) -> None:
        """Resolve configuration, prepare storage, open and migrate the database."""
        self.paths.ensure_directories()
        log_path = configure_logging(self.paths.logs_dir, console=self.console_logging)
        log_event(
            logger,
            20,
            "app.starting",
            version=__version__,
            data_root=str(self.paths.data_root),
            log_file=str(log_path) if log_path else None,
        )

        self.machine = self.machine_store.load()
        if self.machine.data_root and Path(self.machine.data_root) != self.paths.data_root:
            log_event(
                logger,
                20,
                "app.data_root_from_machine_config",
                configured=self.machine.data_root,
                effective=str(self.paths.data_root),
            )

        self._open_database()
        self._load_status()
        log_event(
            logger,
            20,
            "app.ready",
            schema_version=self.status.schema_version,
            setup_complete=self.status.setup_complete,
            clinic_configured=self.clinic.is_configured,
        )

    def _open_database(self) -> None:
        database = Database(self.paths.database_file).open()
        self.database = database
        runner = MigrationRunner(database)
        self.migrations = runner
        try:
            result = runner.apply_pending()
        except SchemaVersionError:
            database.close()
            self.database = None
            raise
        except Exception:
            database.close()
            self.database = None
            raise
        if result.changed:
            log_event(
                logger,
                20,
                "app.schema_upgraded",
                from_version=result.from_version,
                to_version=result.to_version,
                duration_ms=result.duration_ms,
            )
        self.status.schema_version = runner.current_version()

    def _load_status(self) -> None:
        database = self.require_database()
        meta = MetaRepository(database)
        self.status.setup_complete = meta.is_setup_complete
        self.machine = self.machine_store.load()
        self.machine_store.save(
            self.machine.with_updates(
                app_version_seen=__version__,
                first_run_completed=self.status.setup_complete,
                activated=self.machine.activated,
            )
        )
        if self.machine.installation_id:
            meta.register_machine(
                installation_id=self.machine.installation_id,
                machine_label=self.machine.machine_label,
                app_version=__version__,
            )
        if not self.status.setup_complete:
            self.status.messages.append(t("foundation.banner_title"))

    # ---- services --------------------------------------------------------------
    def require_database(self) -> Database:
        """Return the open database, raising a clear error when startup did not complete."""
        if self.database is None:
            raise DatabaseError(
                "The clinic database is not open. Restart Dentiva Pro; if the problem continues, "
                "check that the data folder is available and not read-only.",
                context={"path": str(self.paths.database_file)},
            )
        return self.database

    def settings_service(self) -> SettingsService:
        """Build the settings service for the open database."""
        return SettingsService(SettingsRepository(self.require_database()))

    def sequence_service(self) -> SequenceRepository:
        """Return the identifier allocator for the open database."""
        return SequenceRepository(self.require_database())

    def meta_service(self) -> MetaRepository:
        """Return the metadata repository for the open database."""
        return MetaRepository(self.require_database())

    def load_clinic_identity(self) -> ClinicIdentity:
        """Read the clinic identity from settings (empty until the setup wizard runs)."""
        settings = self.settings_service()
        self.clinic = ClinicIdentity(
            name=settings.get_str("clinic.display_name"),
            address=settings.get_str("clinic.address").splitlines()[0]
            if settings.get_str("clinic.address")
            else "",
            phone=settings.get_str("clinic.phone"),
        )
        return self.clinic

    # ---- shutdown -------------------------------------------------------------
    def shutdown(self) -> None:
        """Close the database cleanly."""
        if self.database is not None:
            try:
                self.database.checkpoint()
            except Exception:  # noqa: BLE001 - shutdown must not raise
                logger.exception("wal checkpoint failed during shutdown")
            self.database.close()
            self.database = None
        log_event(logger, 20, "app.stopped")

    @property
    def is_ready(self) -> bool:
        """True when the context finished starting and holds an open database."""
        return self.database is not None and self.migrations is not None
