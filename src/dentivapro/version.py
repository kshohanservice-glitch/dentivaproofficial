"""Single source of truth for product identity and version information.

The installer, About screen, diagnostics pack and release tooling all read these values, and CI fails
the build when the git tag does not match :data:`__version__`.
"""

from __future__ import annotations

APP_NAME = "Dentiva Pro"
APP_SLUG = "DentivaPro"
APP_EXECUTABLE = "DentivaPro.exe"
APP_ID = "com.shohankhan.dentivapro"

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
__version__ = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

RELEASE_CHANNEL = "stable"

CREATOR_NAME = "Shohan Khan"
CREATOR_EMAIL = "helloiamshohan@gmail.com"

PRODUCT_DESCRIPTION = "Premium offline dental clinic management for Bangladesh"

#: Minimum schema version this build can operate on, and the version it ships with.
SCHEMA_VERSION = 1
SUPPORTED_MIN_SCHEMA_VERSION = 1


def version_tuple() -> tuple[int, int, int]:
    """Return the version as a comparable tuple."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def user_agent() -> str:
    """Return a descriptive user agent string (used only in diagnostics text)."""
    return f"{APP_SLUG}/{__version__}"
