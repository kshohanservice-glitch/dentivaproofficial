"""Typed registry of every business setting.

A setting that is not declared here cannot be stored: the registry is the single source of truth for
the key, its type, its default, its allowed range, who may change it, and whether the change must be
audited. Settings screens, print profiles, backup scheduling and security policy all read from this
registry rather than inventing keys locally, which is what keeps the configuration coherent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

from dentivapro.core.errors import ValidationError


class SettingType(StrEnum):
    """Supported value types for business settings."""

    TEXT = "text"
    MULTILINE = "multiline"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    PATH = "path"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """Declaration of a single setting."""

    key: str
    group: str
    label: str
    description: str = ""
    value_type: SettingType = SettingType.TEXT
    default: Any = ""
    choices: tuple[Any, ...] = ()
    minimum: int | float | Decimal | None = None
    maximum: int | float | Decimal | None = None
    permission: str = "settings.manage"
    audit: bool = True
    visible: bool = True
    unit: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    # ---- conversion ------------------------------------------------------
    def coerce(self, value: Any) -> Any:
        """Convert *value* to the declared type, raising :class:`ValidationError` when invalid."""
        try:
            if self.value_type is SettingType.BOOLEAN:
                return _coerce_bool(value)
            if self.value_type is SettingType.INTEGER:
                return self._check_range(int(str(value).strip()))
            if self.value_type is SettingType.DECIMAL:
                return self._check_range(Decimal(str(value).strip()))
            if self.value_type is SettingType.CHOICE:
                return self._check_choice(value)
            if self.value_type in (SettingType.PATH, SettingType.TEXT, SettingType.MULTILINE):
                return self._check_text(value)
        except ValidationError:
            raise
        except (TypeError, ValueError, InvalidOperation) as exc:
            raise self._invalid(value) from exc
        raise self._invalid(value)

    def _check_range(self, value: int | Decimal) -> int | Decimal:
        if self.minimum is not None and value < self.minimum:
            raise ValidationError(
                f"{self.label} must be at least {self.minimum}{self.unit and ' ' + self.unit or ''}.",
                fields={self.key: f"Minimum {self.minimum}"},
            )
        if self.maximum is not None and value > self.maximum:
            raise ValidationError(
                f"{self.label} must not exceed {self.maximum}{self.unit and ' ' + self.unit or ''}.",
                fields={self.key: f"Maximum {self.maximum}"},
            )
        return value

    def _check_choice(self, value: Any) -> Any:
        for choice in self.choices:
            if str(choice) == str(value):
                return choice
        allowed = ", ".join(str(choice) for choice in self.choices)
        raise ValidationError(
            f"{self.label} must be one of: {allowed}.",
            fields={self.key: f"Allowed values: {allowed}"},
        )

    def _check_text(self, value: Any) -> str:
        text = "" if value is None else str(value)
        text = text.strip()
        if self.value_type is SettingType.PATH and text:
            text = str(Path(text).expanduser())
        if self.minimum is not None and len(text) < int(self.minimum):
            raise ValidationError(
                f"{self.label} must be at least {self.minimum} characters long.",
                fields={self.key: f"Minimum length {self.minimum}"},
            )
        if self.value_type is not SettingType.MULTILINE and "\n" in text:
            text = text.replace("\r\n", " ").replace("\n", " ")
        return text

    def _invalid(self, value: Any) -> ValidationError:
        return ValidationError(
            f"'{value}' is not a valid value for {self.label}.",
            fields={self.key: f"Expected {self.value_type.value}"},
        )

    def serialise(self, value: Any) -> str:
        """Serialise a typed value for storage."""
        if self.value_type is SettingType.BOOLEAN:
            return "1" if value else "0"
        if self.value_type is SettingType.DECIMAL:
            return str(Decimal(str(value)).quantize(Decimal("0.01")))
        return str(value)

    def describe(self) -> dict[str, Any]:
        """Return a diagnostics-friendly description of the setting."""
        return {
            "key": self.key,
            "group": self.group,
            "type": self.value_type.value,
            "default": self.default,
            "choices": list(self.choices),
            "min": self.minimum,
            "max": self.maximum,
            "permission": self.permission,
            "audit": self.audit,
        }


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    raise ValidationError(f"'{value}' is not a yes/no value.", fields={"value": "Use yes or no"})


class SettingsRegistry:
    """A collection of :class:`SettingSpec` objects with lookup helpers."""

    def __init__(self, specs: tuple[SettingSpec, ...]) -> None:
        self._specs = {spec.key: spec for spec in specs}
        duplicates = len(specs) - len(self._specs)
        if duplicates:  # pragma: no cover - guarded by unit tests
            raise ValueError(f"{duplicates} duplicate setting keys were declared")

    def __contains__(self, key: object) -> bool:
        return key in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[SettingSpec]:
        return iter(self._specs.values())

    def get(self, key: str) -> SettingSpec:
        """Return the declaration for *key*."""
        try:
            return self._specs[key]
        except KeyError as exc:
            raise ValidationError(f"'{key}' is not a known setting.") from exc

    def keys(self) -> tuple[str, ...]:
        """All declared keys, sorted."""
        return tuple(sorted(self._specs))

    def groups(self) -> tuple[str, ...]:
        """All groups, in declaration order."""
        seen: list[str] = []
        for spec in self._specs.values():
            if spec.group not in seen:
                seen.append(spec.group)
        return tuple(seen)

    def by_group(self, group: str) -> tuple[SettingSpec, ...]:
        """Return every setting in a group."""
        return tuple(spec for spec in self._specs.values() if spec.group == group)

    def defaults(self) -> dict[str, Any]:
        """Return the default value for every setting."""
        return {spec.key: spec.default for spec in self._specs.values()}

    def invalidate_cache_for(self, key: str) -> bool:
        """Return True when a change to *key* requires caches to be refreshed."""
        spec = self.get(key)
        return bool(spec.tags)


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

CLINIC_GROUP = "clinic"
CLINICAL_GROUP = "clinical"
BILLING_GROUP = "billing"
PRINTING_GROUP = "printing"
INVENTORY_GROUP = "inventory"
SECURITY_GROUP = "security"
BACKUP_GROUP = "backup"
NOTIFICATIONS_GROUP = "notifications"
INTERFACE_GROUP = "interface"

PRINT_PROFILE_CHOICES: Final[tuple[str, ...]] = (
    "a4-portrait",
    "a4-landscape",
    "a5-portrait",
    "a6-portrait",
    "letter-portrait",
    "thermal-80mm",
    "thermal-58mm",
)

SPECS: Final[tuple[SettingSpec, ...]] = (
    # ---- clinic ---------------------------------------------------------
    SettingSpec(
        key="clinic.display_name",
        group=CLINIC_GROUP,
        label="Clinic name",
        description="Shown in the header and on every printed document.",
        default="",
        permission="settings.manage",
    ),
    SettingSpec(
        key="clinic.display_name_bn",
        group=CLINIC_GROUP,
        label="Clinic name (Bengali)",
        description="Optional Bengali clinic name for bilingual letterheads.",
        default="",
    ),
    SettingSpec(
        key="clinic.address",
        group=CLINIC_GROUP,
        label="Address",
        default="",
        value_type=SettingType.MULTILINE,
    ),
    SettingSpec(
        key="clinic.address_bn",
        group=CLINIC_GROUP,
        label="Address (Bengali)",
        default="",
        value_type=SettingType.MULTILINE,
    ),
    SettingSpec(key="clinic.phone", group=CLINIC_GROUP, label="Phone", default=""),
    SettingSpec(key="clinic.phone_alt", group=CLINIC_GROUP, label="Alternate phone", default=""),
    SettingSpec(key="clinic.email", group=CLINIC_GROUP, label="Email", default=""),
    SettingSpec(key="clinic.website", group=CLINIC_GROUP, label="Website", default=""),
    SettingSpec(
        key="clinic.logo_path",
        group=CLINIC_GROUP,
        label="Logo file",
        default="",
        value_type=SettingType.PATH,
    ),
    SettingSpec(
        key="clinic.hours_note",
        group=CLINIC_GROUP,
        label="Clinic hours note",
        default="",
        value_type=SettingType.MULTILINE,
    ),
    SettingSpec(
        key="clinic.footer_note",
        group=CLINIC_GROUP,
        label="Document footer note",
        default="",
        value_type=SettingType.MULTILINE,
    ),
    SettingSpec(
        key="clinic.currency",
        group=CLINIC_GROUP,
        label="Currency",
        default="BDT",
        choices=("BDT",),
        value_type=SettingType.CHOICE,
    ),
    # ---- clinical -------------------------------------------------------
    SettingSpec(
        key="clinical.followup_default_days",
        group=CLINICAL_GROUP,
        label="Default follow-up interval",
        unit="days",
        default=7,
        value_type=SettingType.INTEGER,
        minimum=1,
        maximum=180,
    ),
    SettingSpec(
        key="clinical.signature_height_mm",
        group=CLINICAL_GROUP,
        label="Reserved signature space on prescriptions",
        unit="mm",
        default=25,
        value_type=SettingType.INTEGER,
        minimum=22,
        maximum=45,
    ),
    SettingSpec(
        key="clinical.print_footer_message",
        group=CLINICAL_GROUP,
        label="Prescription footer message",
        default="This prescription is valid for the named patient only.",
        value_type=SettingType.MULTILINE,
    ),
    SettingSpec(
        key="clinical.odontogram_default_dentition",
        group=CLINICAL_GROUP,
        label="Dental chart dentition on open",
        default="permanent",
        choices=("permanent", "primary"),
        value_type=SettingType.CHOICE,
    ),
    # ---- billing --------------------------------------------------------
    SettingSpec(
        key="billing.invoice_number_prefix",
        group=BILLING_GROUP,
        label="Invoice prefix",
        default="INV",
        minimum=1,
        maximum=8,
    ),
    SettingSpec(
        key="billing.allow_partial_payment",
        group=BILLING_GROUP,
        label="Allow partial payments",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="billing.allow_overpayment",
        group=BILLING_GROUP,
        label="Allow payments above the balance",
        default=False,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="billing.default_discount_percent",
        group=BILLING_GROUP,
        label="Default invoice discount",
        unit="%",
        default=Decimal("0.00"),
        value_type=SettingType.DECIMAL,
        minimum=Decimal(0),
        maximum=Decimal(100),
    ),
    SettingSpec(
        key="billing.payment_methods",
        group=BILLING_GROUP,
        label="Enabled payment methods",
        default="cash,bank,card,bkash,nagad,rocket,upay,other",
        tags=("payment_methods",),
    ),
    # ---- printing -------------------------------------------------------
    SettingSpec(
        key="printing.prescription_profile",
        group=PRINTING_GROUP,
        label="Prescription paper profile",
        default="a5-portrait",
        choices=PRINT_PROFILE_CHOICES,
        value_type=SettingType.CHOICE,
    ),
    SettingSpec(
        key="printing.invoice_profile",
        group=PRINTING_GROUP,
        label="Invoice paper profile",
        default="a4-portrait",
        choices=PRINT_PROFILE_CHOICES,
        value_type=SettingType.CHOICE,
    ),
    SettingSpec(
        key="printing.thermal_profile",
        group=PRINTING_GROUP,
        label="Receipt paper profile",
        default="thermal-80mm",
        choices=("thermal-80mm", "thermal-58mm"),
        value_type=SettingType.CHOICE,
    ),
    SettingSpec(
        key="printing.show_letterhead_logo",
        group=PRINTING_GROUP,
        label="Show the clinic logo on documents",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="printing.show_document_qr",
        group=PRINTING_GROUP,
        label="Print a verification QR code",
        default=False,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="printing.watermark_reprints",
        group=PRINTING_GROUP,
        label="Mark reprinted documents as duplicates",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="printing.default_copies",
        group=PRINTING_GROUP,
        label="Default number of copies",
        default=1,
        value_type=SettingType.INTEGER,
        minimum=1,
        maximum=5,
    ),
    # ---- inventory ------------------------------------------------------
    SettingSpec(
        key="inventory.expiry_warning_days",
        group=INVENTORY_GROUP,
        label="Expiry warning window",
        unit="days",
        default=30,
        value_type=SettingType.INTEGER,
        minimum=1,
        maximum=365,
    ),
    SettingSpec(
        key="inventory.qr_scan_enabled",
        group=INVENTORY_GROUP,
        label="Enable barcode/QR entry for stock",
        default=False,
        value_type=SettingType.BOOLEAN,
    ),
    # ---- security -------------------------------------------------------
    SettingSpec(
        key="security.auto_lock_minutes",
        group=SECURITY_GROUP,
        label="Lock the session after inactivity",
        unit="minutes",
        default=15,
        choices=(5, 10, 15, 30),
        value_type=SettingType.CHOICE,
        tags=("session",),
    ),
    SettingSpec(
        key="security.max_failed_attempts",
        group=SECURITY_GROUP,
        label="Failed sign-in attempts before lockout",
        default=5,
        value_type=SettingType.INTEGER,
        minimum=3,
        maximum=10,
    ),
    SettingSpec(
        key="security.lockout_minutes",
        group=SECURITY_GROUP,
        label="Lockout duration",
        unit="minutes",
        default=15,
        value_type=SettingType.INTEGER,
        minimum=5,
        maximum=120,
    ),
    SettingSpec(
        key="security.password_min_length",
        group=SECURITY_GROUP,
        label="Minimum password length",
        default=10,
        value_type=SettingType.INTEGER,
        minimum=10,
        maximum=64,
    ),
    SettingSpec(
        key="security.require_password_to_resume",
        group=SECURITY_GROUP,
        label="Require the password to unlock the session",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    # ---- backup ---------------------------------------------------------
    SettingSpec(
        key="backup.folder",
        group=BACKUP_GROUP,
        label="Backup folder",
        description="Folder used for manual and scheduled backups. A USB drive or network share is recommended.",
        default="",
        value_type=SettingType.PATH,
        tags=("backup",),
    ),
    SettingSpec(
        key="backup.schedule_days",
        group=BACKUP_GROUP,
        label="Automatic backup interval",
        default=7,
        choices=(0, 7, 15, 30),
        value_type=SettingType.CHOICE,
        tags=("backup",),
    ),
    SettingSpec(
        key="backup.keep_last_n",
        group=BACKUP_GROUP,
        label="Automatic backups to keep",
        default=10,
        value_type=SettingType.INTEGER,
        minimum=3,
        maximum=365,
    ),
    SettingSpec(
        key="backup.include_attachments",
        group=BACKUP_GROUP,
        label="Include patient attachments in backups",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="backup.reminder_enabled",
        group=BACKUP_GROUP,
        label="Remind me when a backup is overdue",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    # ---- notifications --------------------------------------------------
    SettingSpec(
        key="notifications.appointment_reminder_minutes",
        group=NOTIFICATIONS_GROUP,
        label="Appointment reminder lead time",
        unit="minutes",
        default=30,
        value_type=SettingType.INTEGER,
        minimum=5,
        maximum=1440,
    ),
    SettingSpec(
        key="notifications.low_stock_alerts",
        group=NOTIFICATIONS_GROUP,
        label="Low-stock alerts",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    SettingSpec(
        key="notifications.expiry_alerts",
        group=NOTIFICATIONS_GROUP,
        label="Expiry alerts",
        default=True,
        value_type=SettingType.BOOLEAN,
    ),
    # ---- interface ------------------------------------------------------
    SettingSpec(
        key="ui.table_density",
        group=INTERFACE_GROUP,
        label="Table density",
        default="comfortable",
        choices=("comfortable", "compact"),
        value_type=SettingType.CHOICE,
        permission="",
    ),
    SettingSpec(
        key="ui.reduce_motion",
        group=INTERFACE_GROUP,
        label="Reduce motion",
        description="Disables non-essential animation for comfort or accessibility.",
        default=False,
        value_type=SettingType.BOOLEAN,
        permission="",
        tags=("motion",),
    ),
    SettingSpec(
        key="ui.default_date_range",
        group=INTERFACE_GROUP,
        label="Default date range on lists",
        default="today",
        choices=("today", "last7", "last30", "last90", "last365", "all"),
        value_type=SettingType.CHOICE,
        permission="",
    ),
    SettingSpec(
        key="ui.appointment_day_start_hour",
        group=INTERFACE_GROUP,
        label="Calendar day start hour",
        default=9,
        value_type=SettingType.INTEGER,
        minimum=0,
        maximum=23,
        permission="",
    ),
    SettingSpec(
        key="ui.appointment_day_end_hour",
        group=INTERFACE_GROUP,
        label="Calendar day end hour",
        default=21,
        value_type=SettingType.INTEGER,
        minimum=1,
        maximum=24,
        permission="",
    ),
)

REGISTRY: Final[SettingsRegistry] = SettingsRegistry(SPECS)


def registry() -> SettingsRegistry:
    """Return the process-wide settings registry."""
    return REGISTRY
