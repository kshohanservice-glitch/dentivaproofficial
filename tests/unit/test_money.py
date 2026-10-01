"""Money arithmetic must be exact — these tests are the guarantee behind every financial figure."""

from __future__ import annotations

from decimal import Decimal

import pytest

from dentivapro.core.errors import ValidationError
from dentivapro.core.money import (
    BENGALI_DIGITS,
    Money,
    clamp_non_negative,
    normalise_digits,
    sum_money,
    to_ascii_digits,
    to_bengali_digits,
)


class TestConstruction:
    def test_from_minor_round_trips(self) -> None:
        assert Money.from_minor(1245075).amount == Decimal("12450.75")
        assert Money.from_minor(1245075).to_minor() == 1245075

    def test_quantises_to_paisa(self) -> None:
        assert Money(Decimal("10.005")).amount == Decimal("10.01")
        assert Money(Decimal("10.004")).amount == Decimal("10.00")

    def test_rejects_binary_float_input(self) -> None:
        with pytest.raises(TypeError):
            Money(10.5)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1250", Decimal("1250.00")),
            ("1,250.50", Decimal("1250.50")),
            ("৳ 1,250.50", Decimal("1250.50")),
            ("১২৫০.৫০", Decimal("1250.50")),
            ("  99.9  ", Decimal("99.90")),
            (1250, Decimal("1250.00")),
            (Decimal("0.01"), Decimal("0.01")),
        ],
    )
    def test_from_input_accepts_real_world_formats(self, raw: object, expected: Decimal) -> None:
        assert Money.from_input(raw).amount == expected

    @pytest.mark.parametrize("raw", ["", "  ", "abc", "12.3.4", None, 12.5])
    def test_from_input_rejects_invalid(self, raw: object) -> None:
        with pytest.raises(ValidationError):
            Money.from_input(raw)

    def test_error_message_names_the_field(self) -> None:
        with pytest.raises(ValidationError) as info:
            Money.from_input("abc", field="discount")
        assert "discount" in info.value.fields


class TestArithmetic:
    def test_addition_is_exact(self) -> None:
        total = Money.zero()
        for _ in range(1000):
            total = total + Money(Decimal("0.07"))
        assert total.amount == Decimal("70.00")

    def test_naive_float_would_drift_but_money_does_not(self) -> None:
        float_total = sum(0.1 for _ in range(10))
        money_total = sum_money([Money(Decimal("0.10"))] * 10)
        assert float_total != 1.0  # documents why floats are banned from the money path
        assert money_total.amount == Decimal("1.00")

    def test_subtraction_can_go_negative(self) -> None:
        assert (Money(Decimal("10.00")) - Money(Decimal("25.50"))).amount == Decimal("-15.50")

    def test_multiply_by_quantity_milli(self) -> None:
        price = Money(Decimal("450.50"))
        assert price.multiply_by_quantity(2500).amount == Decimal("1126.25")

    def test_percent_rounds_half_up(self) -> None:
        assert Money(Decimal("12450.75")).percent(Decimal(10)).amount == Decimal("1245.08")
        assert Money(Decimal("999.99")).percent(Decimal(100)).amount == Decimal("999.99")

    def test_split_preserves_the_total_exactly(self) -> None:
        parts = Money(Decimal("100.00")).split(3)
        assert sum_money(parts).amount == Decimal("100.00")
        assert [part.amount for part in parts] == [
            Decimal("33.34"),
            Decimal("33.33"),
            Decimal("33.33"),
        ]

    def test_split_rejects_zero_parts(self) -> None:
        with pytest.raises(ValidationError):
            Money(Decimal("10.00")).split(0)

    def test_comparisons_are_exact(self) -> None:
        assert Money(Decimal("1.10")) > Money(Decimal("1.09"))
        assert Money(Decimal("1.10")) == Money(Decimal("1.1"))

    def test_clamp_non_negative_hides_overpayment_only_for_display(self) -> None:
        assert clamp_non_negative(Money(Decimal("-5.00"))).amount == Decimal("0.00")
        assert clamp_non_negative(Money(Decimal("5.00"))).amount == Decimal("5.00")


class TestFormatting:
    def test_formats_with_symbol_and_separators(self) -> None:
        assert Money(Decimal("12450.75")).format() == "৳ 12,450.75"
        assert Money(Decimal("0.00")).format() == "৳ 0.00"
        assert Money(Decimal("-15.50")).format() == "৳ -15.50"

    def test_formats_bengali_digits_on_request(self) -> None:
        assert Money(Decimal("12450.75")).format(bengali_digits=True) == "৳ ১২,৪৫০.৭৫"

    def test_formats_without_symbol_or_separators(self) -> None:
        assert Money(Decimal("12450.75")).format(with_symbol=False) == "12,450.75"
        assert Money(Decimal("12450.75")).format(thousands=False) == "৳ 12450.75"

    def test_zero_decimals_for_summary_tiles(self) -> None:
        assert Money(Decimal("12450.75")).format(decimals=0) == "৳ 12,451"


class TestDigitHelpers:
    def test_bengali_digit_conversion(self) -> None:
        assert to_bengali_digits("2026") == "২০২৬"
        assert to_ascii_digits("২০২৬") == "2026"
        assert len(BENGALI_DIGITS) == 10

    def test_normalise_digits_strips_symbols_and_separators(self) -> None:
        assert normalise_digits("৳ ১,২৫০.৫০") == "1250.50"
