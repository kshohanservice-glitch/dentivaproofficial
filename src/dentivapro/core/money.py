"""Exact monetary arithmetic for BDT amounts.

Accounting values are never represented with binary floating point. The domain type stores a
:class:`decimal.Decimal` quantised to two decimal places, and persistence uses integer **paisa**
(amount × 100), which SQLite can sum exactly.

The module also provides the display and parsing helpers the UI and printed documents need,
including Bengali digit support (``৳ ১২,৪৫০.৭৫``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Final, Self

from dentivapro.core.errors import ValidationError

CURRENCY_CODE: Final[str] = "BDT"
CURRENCY_SYMBOL: Final[str] = "৳"
MINOR_UNITS_PER_UNIT: Final[int] = 100
QUANTITY_SCALE: Final[int] = 1000

_CENT: Final[Decimal] = Decimal("0.01")
_QUANTUM: Final[Decimal] = Decimal(1)

BENGALI_DIGITS: Final[str] = "০১২৩৪৫৬৭৮৯"
_ASCII_TO_BENGALI = str.maketrans("0123456789", BENGALI_DIGITS)
_BENGALI_TO_ASCII = str.maketrans(BENGALI_DIGITS, "0123456789")

_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"-?\d+(?:\.\d+)?")


def to_bengali_digits(text: str) -> str:
    """Return *text* with ASCII digits replaced by Bengali digits."""
    return text.translate(_ASCII_TO_BENGALI)


def to_ascii_digits(text: str) -> str:
    """Return *text* with Bengali digits normalised to ASCII digits."""
    return text.translate(_BENGALI_TO_ASCII)


def normalise_digits(text: str) -> str:
    """Normalise Bengali digits, currency symbols, spaces and separators for parsing."""
    cleaned = to_ascii_digits(text)
    for symbol in (CURRENCY_SYMBOL, "BDT", "Tk", "TK", "৳", "\u00a0"):
        cleaned = cleaned.replace(symbol, "")
    return cleaned.replace(",", "").strip()


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An exact BDT amount with two decimal places."""

    amount: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        quantised = _quantise(self.amount)
        object.__setattr__(self, "amount", quantised)

    # ---- construction --------------------------------------------------
    @classmethod
    def zero(cls) -> Self:
        """Return a zero amount."""
        return cls(Decimal("0.00"))

    @classmethod
    def from_minor(cls, minor: int) -> Self:
        """Build an amount from integer paisa."""
        return cls(Decimal(minor) / Decimal(MINOR_UNITS_PER_UNIT))

    @classmethod
    def from_input(cls, value: object, *, field: str = "amount") -> Money:
        """Parse user input, accepting Bengali digits, separators and a currency symbol.

        Binary floats are rejected outright: an accounting amount must never originate from an
        inexact float, so the caller has to pass text, an integer or a :class:`Decimal`.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"Enter a valid {field}.", fields={field: "A value is required."})
        if isinstance(value, float):
            raise ValidationError(
                f"'{value}' is not a valid amount.",
                fields={field: "Enter a number, for example 1250.00"},
            )
        if isinstance(value, Money):
            return value
        if isinstance(value, int):
            return cls(Decimal(value))
        if isinstance(value, Decimal):
            return cls(value)
        text = normalise_digits(str(value))
        match = _NUMBER_RE.fullmatch(text)
        if not match:
            raise ValidationError(
                f"'{value}' is not a valid amount.",
                fields={field: "Enter a number, for example 1250.00"},
            )
        try:
            return cls(Decimal(match.group(0)))
        except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
            raise ValidationError(
                f"'{value}' is not a valid amount.", fields={field: "Invalid"}
            ) from exc

    # ---- conversion ----------------------------------------------------
    def to_minor(self) -> int:
        """Return the amount as integer paisa (exact)."""
        return int((self.amount * MINOR_UNITS_PER_UNIT).to_integral_value(rounding=ROUND_HALF_UP))

    def to_quantity(self) -> Decimal:
        """Return the amount scaled to 3 decimals (used for average unit prices)."""
        return self.amount.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def is_zero(self) -> bool:
        """Return True when the amount is exactly zero."""
        return self.amount == Decimal("0.00")

    def is_positive(self) -> bool:
        """Return True when the amount is greater than zero."""
        return self.amount > 0

    def is_negative(self) -> bool:
        """Return True when the amount is less than zero."""
        return self.amount < 0

    # ---- arithmetic ----------------------------------------------------
    def __add__(self, other: object) -> Money:
        if isinstance(other, Money):
            return Money(self.amount + other.amount)
        return NotImplemented

    def __sub__(self, other: object) -> Money:
        if isinstance(other, Money):
            return Money(self.amount - other.amount)
        return NotImplemented

    def __mul__(self, factor: object) -> Money:
        """Multiply by an integer, Decimal, or a quantity expressed in thousandths."""
        if isinstance(factor, Money):
            return NotImplemented
        if isinstance(factor, int):
            return Money(self.amount * Decimal(factor))
        if isinstance(factor, Decimal):
            return Money(self.amount * factor)
        if isinstance(factor, str):
            return Money(self.amount * Decimal(factor))
        return NotImplemented

    def __neg__(self) -> Money:
        return Money(-self.amount)

    def __pos__(self) -> Money:
        return self

    def absolute(self) -> Money:
        """Return the magnitude of the amount."""
        return Money(abs(self.amount))

    def percent(self, rate: Decimal | str | int) -> Money:
        """Return ``rate`` percent of this amount, rounded half-up to paisa."""
        rate_decimal = rate if isinstance(rate, Decimal) else Decimal(str(rate))
        return Money(self.amount * rate_decimal / Decimal(100))

    def multiply_by_quantity(self, quantity_milli: int) -> Money:
        """Multiply by a quantity stored in thousandths (2.5 → 2500)."""
        return Money(self.amount * Decimal(quantity_milli) / Decimal(QUANTITY_SCALE))

    def clamp_min(self, floor: Money) -> Money:
        """Return ``max(self, floor)`` (used for balances that must not go below zero silently)."""
        return Money(max(self.amount, floor.amount))

    def split(self, parts: int) -> list[Money]:
        """Split into *parts* whole amounts without losing or inventing a paisa.

        The remainder is distributed one paisa at a time to the first recipients, so the sum of the
        result is always exactly equal to the original amount.
        """
        if parts <= 0:
            raise ValidationError("Cannot split an amount into zero parts.")
        total_minor = self.to_minor()
        base, remainder = divmod(total_minor, parts)
        return [Money.from_minor(base + (1 if index < remainder else 0)) for index in range(parts)]

    # ---- display -------------------------------------------------------
    def format(
        self,
        *,
        with_symbol: bool = True,
        thousands: bool = True,
        bengali_digits: bool = False,
        decimals: int = 2,
    ) -> str:
        """Format the amount for display, e.g. ``৳ 12,450.75``."""
        quantised = self.amount.quantize(
            Decimal(1).scaleb(-decimals) if decimals >= 0 else _QUANTUM, rounding=ROUND_HALF_UP
        )
        if thousands:
            body = f"{quantised:,.{max(decimals, 0)}f}"
        else:
            body = f"{quantised:.{max(decimals, 0)}f}"
        if decimals <= 0:
            body = body.split(".")[0]
        if bengali_digits:
            body = to_bengali_digits(body)
        return f"{CURRENCY_SYMBOL} {body}" if with_symbol else body

    def __str__(self) -> str:
        return self.format()


def sum_money(values: list[Money] | tuple[Money, ...]) -> Money:
    """Sum amounts exactly (never accumulate float error)."""
    total = Decimal("0.00")
    for value in values:
        total += value.amount
    return Money(total)


def clamp_non_negative(value: Money) -> Money:
    """Return zero when an amount is negative (used for display of over-payments)."""
    return Money.zero() if value.is_negative() else value


def _quantise(amount: Decimal) -> Decimal:
    if not isinstance(amount, Decimal):  # pragma: no cover - guarded by callers
        raise TypeError("Money requires a Decimal amount")
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)
