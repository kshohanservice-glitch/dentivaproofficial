"""Consistent date and time handling.

Two distinct kinds of value are used throughout the product and must never be confused:

* **instants** (``*_at``) — stored as UTC ISO-8601 with a trailing ``Z``; used for audit records,
  creation/update stamps and session times;
* **business dates** (``*_on``) — stored as clinic-local calendar dates (``YYYY-MM-DD``); used for
  visit dates, invoice dates, payment dates and expense dates, so that financial periods and reprints
  never shift because of a timezone conversion.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Final

from dentivapro.core.money import to_bengali_digits

DATE_FORMAT: Final[str] = "%Y-%m-%d"
DISPLAY_DATE_FORMAT: Final[str] = "%d %b %Y"
DISPLAY_DATE_TIME_FORMAT: Final[str] = "%d %b %Y %H:%M"

SOUTH_ASIA_TZ_OFFSET_HOURS: Final[int] = 6  # Asia/Dhaka is UTC+6 year round (no DST)

#: December, used when rolling a month range into the next year.
_DECEMBER: Final[int] = 12


def utc_now() -> datetime:
    """Return the current instant as a timezone-aware UTC datetime."""
    return datetime.now(tz=UTC)


def to_utc_iso(moment: datetime | None = None) -> str:
    """Serialise an instant as ``YYYY-MM-DDTHH:MM:SSZ`` (UTC)."""
    value = moment if moment is not None else utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_iso(text: str) -> datetime:
    """Parse an instant produced by :func:`to_utc_iso` (tolerant of a numeric offset)."""
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    moment = datetime.fromisoformat(cleaned)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def clinic_now(reference: datetime | None = None) -> datetime:
    """Return the clinic-local wall clock time (used for display only)."""
    moment = reference if reference is not None else utc_now()
    return moment.astimezone(UTC) + timedelta(hours=SOUTH_ASIA_TZ_OFFSET_HOURS)


def today_local(reference: datetime | None = None) -> date:
    """Return today's clinic-local calendar date."""
    return clinic_now(reference).date()


def to_date_string(value: date) -> str:
    """Serialise a business date as ``YYYY-MM-DD``."""
    return value.strftime(DATE_FORMAT)


def parse_date(text: str) -> date:
    """Parse a stored business date; raises ``ValueError`` for malformed input.

    Business dates are clinic-local calendar dates, not instants, so there is no time zone to carry.
    """
    return datetime.strptime(text.strip(), DATE_FORMAT).date()  # noqa: DTZ007 - calendar date


def format_display_date(value: date, *, locale: str = "en") -> str:
    """Format a business date for display (e.g. ``01 Oct 2026``)."""
    formatted = value.strftime(DISPLAY_DATE_FORMAT)
    return to_bengali_digits(formatted) if locale.startswith("bn") else formatted


def format_display_datetime(moment: datetime, *, locale: str = "en") -> str:
    """Format an instant in clinic-local time for display."""
    formatted = clinic_now(moment).strftime(DISPLAY_DATE_TIME_FORMAT)
    return to_bengali_digits(formatted) if locale.startswith("bn") else formatted


def minutes_from_midnight(moment_time: time) -> int:
    """Return the number of minutes since midnight (used for appointment scheduling)."""
    return moment_time.hour * 60 + moment_time.minute


def time_from_minutes(minutes: int) -> time:
    """Return a ``time`` from minutes-since-midnight, wrapping at 24 hours."""
    clamped = max(0, min(minutes, 24 * 60 - 1))
    return time(hour=clamped // 60, minute=clamped % 60)


def format_time_range(start_minutes: int, duration_minutes: int, *, locale: str = "en") -> str:
    """Format an appointment slot such as ``10:30 – 11:00``."""
    start = time_from_minutes(start_minutes)
    end = time_from_minutes(start_minutes + max(0, duration_minutes))
    text = f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"
    return to_bengali_digits(text) if locale.startswith("bn") else text


def day_bounds(target: date) -> tuple[str, str]:
    """Return the inclusive ``YYYY-MM-DD`` bounds for a single day (used by date filters)."""
    return to_date_string(target), to_date_string(target)


def range_bounds(days: int, *, today: date | None = None) -> tuple[str, str]:
    """Return the ``YYYY-MM-DD`` bounds for a "last N days" filter, inclusive of today."""
    end = today or today_local()
    start = end - timedelta(days=max(0, days - 1))
    return to_date_string(start), to_date_string(end)


def month_bounds(year: int, month: int) -> tuple[str, str]:
    """Return the first and last date of a calendar month."""
    first = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == _DECEMBER else date(year, month + 1, 1)
    return to_date_string(first), to_date_string(next_month - timedelta(days=1))


def quarter_bounds(year: int, quarter: int) -> tuple[str, str]:
    """Return the inclusive bounds of a calendar quarter (1-4)."""
    if quarter not in (1, 2, 3, 4):
        raise ValueError("quarter must be 1-4")
    first_month = (quarter - 1) * 3 + 1
    last_month = first_month + 2
    start, _ = month_bounds(year, first_month)
    _, end = month_bounds(year, last_month)
    return start, end


def year_bounds(year: int) -> tuple[str, str]:
    """Return the inclusive bounds of a calendar year."""
    return f"{year:04d}-01-01", f"{year:04d}-12-31"


def humanise_age(birth_date: date, *, today: date | None = None) -> str:
    """Return an age description such as ``34 years`` or ``7 months`` for infants."""
    reference = today or today_local()
    if birth_date > reference:
        return "—"
    years = (
        reference.year
        - birth_date.year
        - ((reference.month, reference.day) < (birth_date.month, birth_date.day))
    )
    if years == 1:
        return "1 year"
    if years > 1:
        return f"{years} years"
    months = (reference.year - birth_date.year) * 12 + reference.month - birth_date.month
    if reference.day < birth_date.day:
        months -= 1
    months = max(0, months)
    if months >= 1:
        return f"{months} months"
    days = (reference - birth_date).days
    return f"{max(days, 0)} days"


def age_from_years(years: int) -> str:
    """Format an age entered directly as a number of years."""
    return f"{years} years" if years != 1 else "1 year"


def days_between(start: date, end: date) -> int:
    """Return the number of whole days between two business dates."""
    return (end - start).days


def is_within_days(target: date, days: int, *, today: date | None = None) -> bool:
    """Return True when *target* falls within the last *days* days (today included)."""
    reference = today or today_local()
    return 0 <= (reference - target).days <= max(0, days - 1)
