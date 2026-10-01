"""Business identifier formatting.

Codes are human-readable, stable and never reused. Allocation itself happens inside the owning
database transaction (see ``data/repos/sequence_repo.py``); this module owns the *format* so patient
codes, invoice numbers and similar identifiers are consistent across the product, printed documents
and exports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from dentivapro.core.errors import ValidationError

if TYPE_CHECKING:
    from datetime import date


@dataclass(frozen=True, slots=True)
class CodeFormat:
    """Describes how a business code is rendered."""

    name: str
    prefix: str
    padding: int = 5
    monthly: bool = False
    include_year: bool = False

    def render(self, value: int, *, on: date | None = None) -> str:
        """Render a code for the given sequence *value*."""
        parts = [self.prefix]
        if self.monthly and on is not None:
            parts.append(f"{on.year % 100:02d}{on.month:02d}")
        elif self.include_year and on is not None:
            parts.append(f"{on.year:04d}")
        number = str(value).zfill(self.padding)
        return "-".join([*parts, number])


CODE_FORMATS: dict[str, CodeFormat] = {
    "patient": CodeFormat(name="patient", prefix="P", padding=6),
    "appointment": CodeFormat(name="appointment", prefix="AP", padding=5, monthly=True),
    "visit": CodeFormat(name="visit", prefix="V", padding=5, monthly=True),
    "prescription": CodeFormat(name="prescription", prefix="RX", padding=5, monthly=True),
    "invoice": CodeFormat(name="invoice", prefix="INV", padding=5, monthly=True),
    "payment": CodeFormat(name="payment", prefix="PMT", padding=5, monthly=True),
    "expense": CodeFormat(name="expense", prefix="EXP", padding=5, monthly=True),
    "income": CodeFormat(name="income", prefix="INC", padding=5, monthly=True),
    "inventory_movement": CodeFormat(
        name="inventory_movement", prefix="IMV", padding=6, monthly=True
    ),
    "referral": CodeFormat(name="referral", prefix="REF", padding=4, monthly=True),
    "dentist": CodeFormat(name="dentist", prefix="DR", padding=3),
    "staff": CodeFormat(name="staff", prefix="ST", padding=3),
    "user": CodeFormat(name="user", prefix="USR", padding=3),
}

#: Digit range any declared format emits for its counter (``DR-012`` … ``P-000123``).
_CODE_MIN_DIGITS: Final[int] = min(format_.padding for format_ in CODE_FORMATS.values())
_CODE_MAX_DIGITS: Final[int] = max(format_.padding for format_ in CODE_FORMATS.values())

#: ``PREFIX-NUMBER`` or ``PREFIX-YYMM-NUMBER`` (monthly codes carry a four-digit month block).
_CODE_PATTERN = re.compile(
    rf"^[A-Z]{{1,4}}(?:-\d{{4}})?-\d{{{_CODE_MIN_DIGITS},{_CODE_MAX_DIGITS}}}$"
)


def format_code(kind: str, value: int, *, on: date | None = None) -> str:
    """Render a business code of the requested kind.

    Raises :class:`ValidationError` when the kind is unknown or the value is not a positive integer.
    """
    if kind not in CODE_FORMATS:
        raise ValidationError(f"Unknown identifier type '{kind}'.")
    if value <= 0:
        raise ValidationError(
            "Identifier values must be positive.", fields={"value": "Must be > 0"}
        )
    return CODE_FORMATS[kind].render(value, on=on)


def looks_like_code(text: str) -> bool:
    """Return True when *text* resembles a Dentiva Pro business code."""
    return bool(_CODE_PATTERN.match(text.strip().upper()))


def normalise_code(text: str) -> str:
    """Normalise user-typed codes for search (upper case, single spaces removed)."""
    return re.sub(r"\s+", "", text.strip().upper())


def patient_codes_batch(first_value: int, count: int, *, width: int | None = None) -> list[str]:
    """Render a contiguous batch of patient codes (used by seeding and bulk import)."""
    padding = width or CODE_FORMATS["patient"].padding
    return [f"P-{value:0{padding}d}" for value in range(first_value, first_value + count)]
