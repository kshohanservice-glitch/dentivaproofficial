"""Machine-level configuration.

Business settings live in the database (they belong to the clinic and travel with a backup), while
*machine* configuration is bound to the PC: where the data lives, which installation this is, and
whether activation has been completed. This module owns that second kind of state.
"""

from __future__ import annotations

import json
import platform
import socket
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from dentivapro.core.errors import StorageError
from dentivapro.core.logging import get_logger
from dentivapro.version import __version__

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

CONFIG_FORMAT_VERSION = 1


def default_machine_label() -> str:
    """Return a human-readable label for this PC (NetBIOS/computer name)."""
    try:
        return socket.gethostname() or platform.node() or "CLINIC-PC"
    except OSError:  # pragma: no cover - defensive
        return "CLINIC-PC"


@dataclass(slots=True)
class MachineConfig:
    """Machine-bound configuration stored next to (or above) the data root."""

    format_version: int = CONFIG_FORMAT_VERSION
    installation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_root: str | None = None
    machine_label: str = field(default_factory=default_machine_label)
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(timespec="seconds")
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(timespec="seconds")
    )
    app_version_seen: str = __version__
    first_run_completed: bool = False
    activated: bool = False
    locale: str = "en"
    last_backup_at: str | None = None

    # ---- serialisation -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable mapping."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MachineConfig:
        """Build a configuration from stored JSON, ignoring unknown keys defensively."""
        known = set(cls.__dataclass_fields__)
        filtered = {k: v for k, v in payload.items() if k in known}
        return cls(**filtered)

    def with_updates(self, **changes: Any) -> MachineConfig:
        """Return a copy with *changes* applied and the update timestamp refreshed."""
        changes.setdefault("updated_at", datetime.now(tz=UTC).isoformat(timespec="seconds"))
        return replace(self, **changes)


class MachineConfigStore:
    """Loads and saves :class:`MachineConfig` atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> MachineConfig:
        """Load the configuration, returning defaults when the file is absent or unreadable."""
        if not self.path.exists():
            return MachineConfig()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "machine config unreadable; falling back to defaults",
                extra={"event": "config.machine.unreadable", "payload": {"error": str(exc)}},
            )
            return MachineConfig()
        if not isinstance(payload, dict):  # pragma: no cover - defensive
            return MachineConfig()
        config = MachineConfig.from_dict(payload)
        if config.format_version > CONFIG_FORMAT_VERSION:
            logger.warning(
                "machine config written by a newer version",
                extra={
                    "event": "config.machine.newer_format",
                    "payload": {"found": config.format_version, "supported": CONFIG_FORMAT_VERSION},
                },
            )
        return config

    def save(self, config: MachineConfig) -> None:
        """Persist the configuration atomically (write to a temporary file, then replace)."""
        directory = self.path.parent
        try:
            directory.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(self.path)
        except OSError as exc:
            raise StorageError(
                f"The application settings file could not be written to '{self.path}'.",
                context={"path": str(self.path), "os_error": exc.strerror},
                cause=exc,
            ) from exc

    def update(self, **changes: Any) -> MachineConfig:
        """Load, update and save in one step, returning the new configuration."""
        updated = self.load().with_updates(**changes)
        self.save(updated)
        return updated
