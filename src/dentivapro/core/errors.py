"""Structured error handling for Dentiva Pro.

Every failure that a user could plausibly encounter is represented by a :class:`DentivaError`
subclass carrying:

* ``code`` — a stable machine-readable identifier (used in logs and diagnostics),
* ``message`` — a plain-language, user-safe sentence (never a stack trace, never a secret),
* ``context`` — structured, non-sensitive detail for logs.

Unexpected exceptions are converted by :func:`to_user_error` so the UI always has something
actionable to show, while the technical detail is preserved for the log file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UserFacingError:
    """A safe, presentable description of a failure."""

    code: str
    title: str
    message: str
    action: str | None = None
    correlation_id: str | None = None
    detail: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


class DentivaError(Exception):
    """Base class for all deliberate application failures."""

    code = "DENTIVA_ERROR"
    title = "Something went wrong"

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context or {})
        self.cause = cause

    def to_user_error(self, *, correlation_id: str | None = None) -> UserFacingError:
        return UserFacingError(
            code=self.code,
            title=self.title,
            message=self.message,
            correlation_id=correlation_id,
            context=dict(self.context),
        )

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ValidationError(DentivaError):
    """Input violated a business rule or a database constraint."""

    code = "VALIDATION_ERROR"
    title = "Please check the entered information"

    def __init__(
        self,
        message: str,
        *,
        fields: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, context=context, cause=cause)
        self.fields: dict[str, str] = dict(fields or {})

    def to_user_error(self, *, correlation_id: str | None = None) -> UserFacingError:
        error = super().to_user_error(correlation_id=correlation_id)
        error.detail = "\n".join(f"{name}: {msg}" for name, msg in self.fields.items()) or None
        return error


class PermissionDenied(DentivaError):  # noqa: N818 - reads better in business code
    """The session user lacks the permission required for the requested operation."""

    code = "PERMISSION_DENIED"
    title = "You do not have permission"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        *,
        permission: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        merged = dict(context or {})
        if permission:
            merged.setdefault("permission", permission)
        super().__init__(message, context=merged)
        self.permission = permission

    def to_user_error(self, *, correlation_id: str | None = None) -> UserFacingError:
        error = super().to_user_error(correlation_id=correlation_id)
        error.action = "Ask an administrator to grant the required permission."
        return error


class AuthenticationError(DentivaError):
    """Authentication failed (invalid credentials, locked account, expired session)."""

    code = "AUTHENTICATION_FAILED"
    title = "Sign-in failed"


class SessionLockedError(DentivaError):
    """An operation was attempted while the session was locked."""

    code = "SESSION_LOCKED"
    title = "Session locked"


class ActivationError(DentivaError):
    """Activation is missing, invalid, or the local activation state is not trustworthy."""

    code = "ACTIVATION_ERROR"
    title = "Activation required"


class DatabaseError(DentivaError):
    """A database operation failed in a way the user must know about."""

    code = "DATABASE_ERROR"
    title = "The clinic database could not be used"


class SchemaVersionError(DatabaseError):
    """The database schema is newer or older than this build supports."""

    code = "SCHEMA_VERSION_MISMATCH"
    title = "This data was created by a different version"


class IntegrityError(DentivaError):
    """A stored value fails an integrity rule (constraint, checksum, stock balance)."""

    code = "INTEGRITY_ERROR"
    title = "Data integrity problem detected"


class ConflictError(DentivaError):
    """The requested change conflicts with existing data (duplicate code, double booking)."""

    code = "CONFLICT"
    title = "This conflicts with existing data"


class StorageError(DentivaError):
    """A file-system or storage operation failed (missing folder, permissions, no space)."""

    code = "STORAGE_ERROR"
    title = "A file could not be read or written"


class BackupError(DentivaError):
    """Backup creation or verification failed."""

    code = "BACKUP_ERROR"
    title = "Backup failed"


class RestoreError(DentivaError):
    """Restore failed or was refused for safety reasons."""

    code = "RESTORE_ERROR"
    title = "Restore failed"


class PrintError(DentivaError):
    """Printing or PDF generation failed (no printer, unsupported paper, device error)."""

    code = "PRINT_ERROR"
    title = "Printing failed"


class MigrationError(DatabaseError):
    """A schema migration could not be applied."""

    code = "MIGRATION_ERROR"
    title = "The database could not be upgraded"


def to_user_error(
    exc: BaseException, *, correlation_id: str | None = None, detail_limit: int = 2000
) -> UserFacingError:
    """Convert any exception into a safe, presentable error object."""
    if isinstance(exc, DentivaError):
        return exc.to_user_error(correlation_id=correlation_id)

    text = f"{type(exc).__name__}: {exc}".strip()
    if len(text) > detail_limit:
        text = text[:detail_limit] + "…"
    return UserFacingError(
        code="UNEXPECTED_ERROR",
        title="An unexpected problem occurred",
        message=(
            "The action could not be completed. Your data has not been changed by this failure. "
            "If the problem continues, export diagnostics from the About screen and contact support."
        ),
        correlation_id=correlation_id,
        detail=text,
    )
