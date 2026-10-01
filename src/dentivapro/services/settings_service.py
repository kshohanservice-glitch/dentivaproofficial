"""Typed access to clinic settings.

The service is the only supported way to read or write a business setting:

* every value is validated against :mod:`dentivapro.core.settings_schema` before it is stored;
* unknown keys are rejected, so a typo cannot silently create a setting nothing reads;
* typed values are cached in memory and refreshed when a change is made here or reported from another
  part of the application;
* changes are reported through the ``on_change`` hook, which the audit subsystem subscribes to once
  the audit trail is available (Phase 2), and are logged immediately either way.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from dentivapro.core.errors import PermissionDenied, ValidationError
from dentivapro.core.logging import get_logger, log_event
from dentivapro.core.settings_schema import REGISTRY, SettingSpec, SettingsRegistry

if TYPE_CHECKING:
    from dentivapro.data.repos.settings_repo import SettingsRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SettingChange:
    """A single applied settings change (used for auditing and cache invalidation)."""

    key: str
    group: str
    old_value: Any
    new_value: Any
    requires_audit: bool


ChangeHook = Callable[[list[SettingChange]], None]


class SettingsService:
    """Read and write clinic settings with validation, caching and change notification."""

    def __init__(
        self,
        repository: SettingsRepository,
        *,
        registry: SettingsRegistry | None = None,
        on_change: ChangeHook | None = None,
    ) -> None:
        self._repo = repository
        self._registry = registry or REGISTRY
        self._cache: dict[str, Any] = {}
        self._on_change = on_change

    # ---- reading ---------------------------------------------------------
    def get(self, key: str) -> Any:
        """Return the current value of *key* (typed, with the default applied)."""
        spec = self._registry.get(key)
        if key in self._cache:
            return self._cache[key]
        raw = self._repo.get_raw(key)
        value = spec.coerce(spec.default) if raw is None else self._decode(spec, raw)
        self._cache[key] = value
        return value

    def get_bool(self, key: str) -> bool:
        """Return a boolean setting."""
        return bool(self.get(key))

    def get_int(self, key: str) -> int:
        """Return an integer setting."""
        return int(self.get(key))

    def get_str(self, key: str) -> str:
        """Return a text setting."""
        return str(self.get(key))

    def get_all(self, group: str | None = None) -> dict[str, Any]:
        """Return every setting (optionally filtered to one group)."""
        keys = (
            self._registry.keys()
            if group is None
            else tuple(spec.key for spec in self._registry.by_group(group))
        )
        return {key: self.get(key) for key in keys}

    def describe_all(self) -> dict[str, dict[str, Any]]:
        """Return the declaration plus current value of every setting (diagnostics)."""
        description: dict[str, dict[str, Any]] = {}
        for spec in self._registry:
            entry = spec.describe()
            entry["value"] = self.get(spec.key)
            description[spec.key] = entry
        return description

    def spec(self, key: str) -> SettingSpec:
        """Return the declaration for *key*."""
        return self._registry.get(key)

    # ---- writing ---------------------------------------------------------
    def set(
        self,
        key: str,
        value: Any,
        *,
        updated_by: int | None = None,
        permitted: bool = True,
    ) -> SettingChange | None:
        """Validate and store a single setting.

        ``permitted`` carries the result of the permission check performed by the caller's session.
        The default of ``True`` exists so the setup wizard (which runs before any session exists) and
        tests can write settings; every interactive caller passes a real decision.
        """
        spec = self._registry.get(key)
        if not permitted:
            raise PermissionDenied(
                f"You do not have permission to change {spec.label.lower()}.",
                permission=spec.permission or "settings.manage",
                context={"setting": key},
            )
        typed = spec.coerce(value)
        previous = self.get(key)
        if previous == typed:
            return None
        self._repo.set_raw(key, spec.serialise(typed), updated_by=updated_by)
        self._cache[key] = typed
        change = SettingChange(
            key=key,
            group=spec.group,
            old_value=previous,
            new_value=typed,
            requires_audit=spec.audit,
        )
        log_event(
            logger,
            20,
            "settings.changed",
            group=spec.group,
            setting=key,
            audit=spec.audit,
        )
        if self._on_change is not None:
            self._on_change([change])
        return change

    def set_many(
        self, values: Mapping[str, Any], *, updated_by: int | None = None, permitted: bool = True
    ) -> list[SettingChange]:
        """Validate and store several settings, reporting each change once."""
        changes: list[SettingChange] = []
        for key, value in values.items():
            change = self.set(key, value, updated_by=updated_by, permitted=permitted)
            if change is not None:
                changes.append(change)
        return changes

    def set_and_notify_batch(
        self, values: Mapping[str, Any], *, updated_by: int | None = None, permitted: bool = True
    ) -> list[SettingChange]:
        """Apply several changes but emit a single change notification."""
        collected: list[SettingChange] = []
        hook = self._on_change
        self._on_change = None
        try:
            collected = self.set_many(values, updated_by=updated_by, permitted=permitted)
        finally:
            self._on_change = hook
        if collected and hook is not None:
            hook(collected)
        return collected

    def reset(
        self, key: str, *, updated_by: int | None = None, permitted: bool = True
    ) -> SettingChange | None:
        """Remove a stored value so the declared default applies again."""
        spec = self._registry.get(key)
        if not permitted:
            raise PermissionDenied(
                f"You do not have permission to reset {spec.label.lower()}.",
                permission=spec.permission or "settings.manage",
                context={"setting": key},
            )
        previous = self.get(key)
        self._repo.delete(key)
        self._cache.pop(key, None)
        default = spec.coerce(spec.default)
        if previous == default:
            return None
        change = SettingChange(key, spec.group, previous, default, spec.audit)
        actor = None if updated_by is None else str(updated_by)
        log_event(logger, 20, "settings.reset", setting=key, audit=spec.audit, user=actor)
        if self._on_change is not None:
            self._on_change([change])
        return change

    # ---- cache ------------------------------------------------------------
    def invalidate(self, keys: Iterable[str] | None = None) -> None:
        """Drop cached values (all, or the listed keys) so the next read hits the database."""
        if keys is None:
            self._cache.clear()
            return
        for key in keys:
            self._cache.pop(key, None)

    def subscribe(self, hook: ChangeHook) -> None:
        """Register an additional change listener (e.g. the audit service in Phase 2)."""
        existing = self._on_change
        if existing is None:
            self._on_change = hook
            return

        def _chained(changes: list[SettingChange]) -> None:
            existing(changes)
            hook(changes)

        self._on_change = _chained

    # ---- helpers ----------------------------------------------------------
    def _decode(self, spec: SettingSpec, raw: str) -> Any:
        try:
            return spec.coerce(raw)
        except ValidationError:
            log_event(
                logger,
                30,
                "settings.invalid_stored_value",
                setting=spec.key,
                fallback=spec.default,
            )
            return spec.coerce(spec.default)

    def validate(self, key: str, value: Any) -> Any:
        """Validate a value without storing it (used by settings forms for live feedback)."""
        return self._registry.get(key).coerce(value)
