"""Business identifiers and date/time handling."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import pytest

from dentivapro.core.errors import ValidationError
from dentivapro.core.ids import (
    CODE_FORMATS,
    format_code,
    looks_like_code,
    normalise_code,
    patient_codes_batch,
)
from dentivapro.core.timeutil import (
    clinic_now,
    day_bounds,
    format_display_date,
    format_time_range,
    humanise_age,
    minutes_from_midnight,
    month_bounds,
    parse_date,
    parse_utc_iso,
    quarter_bounds,
    range_bounds,
    time_from_minutes,
    to_date_string,
    to_utc_iso,
    today_local,
    utc_now,
    year_bounds,
)


class TestCodes:
    def test_patient_code_is_zero_padded_and_stable(self) -> None:
        assert format_code("patient", 42) == "P-000042"
        assert format_code("patient", 999999) == "P-999999"

    def test_monthly_codes_include_year_and_month(self) -> None:
        assert format_code("invoice", 94, on=date(2026, 10, 1)) == "INV-2610-00094"
        assert format_code("appointment", 7, on=date(2026, 1, 9)) == "AP-2601-00007"

    def test_non_monthly_codes_ignore_the_date(self) -> None:
        assert format_code("dentist", 3, on=date(2026, 5, 5)) == "DR-003"

    @pytest.mark.parametrize("kind", ["clinical_note", "", "PATIENT"])
    def test_unknown_kinds_are_rejected(self, kind: str) -> None:
        with pytest.raises(ValidationError):
            format_code(kind, 1)

    def test_zero_or_negative_values_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            format_code("patient", 0)
        with pytest.raises(ValidationError):
            format_code("patient", -3)

    def test_every_declared_kind_renders(self) -> None:
        for kind in CODE_FORMATS:
            rendered = format_code(kind, 12, on=date(2026, 10, 1))
            assert looks_like_code(rendered), rendered

    def test_normalise_code_removes_spacing(self) -> None:
        assert normalise_code(" inv-2610-00094 ") == "INV-2610-00094"

    def test_batch_generation_is_contiguous(self) -> None:
        assert patient_codes_batch(1, 3) == ["P-000001", "P-000002", "P-000003"]


class TestTimestamps:
    def test_utc_iso_round_trip(self) -> None:
        moment = datetime(2026, 10, 1, 9, 15, 22, tzinfo=__import__("datetime").UTC)
        text = to_utc_iso(moment)
        assert text == "2026-10-01T09:15:22Z"
        assert parse_utc_iso(text) == moment

    def test_utc_iso_accepts_offsets(self) -> None:
        assert parse_utc_iso("2026-10-01T15:15:22+06:00").hour == 9

    def test_naive_datetimes_are_treated_as_utc(self) -> None:
        naive = datetime(2026, 1, 2, 3, 4, 5)  # noqa: DTZ001 - the naive case is the subject
        assert to_utc_iso(naive).endswith("Z")

    def test_clinic_time_is_six_hours_ahead(self) -> None:
        moment = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
        assert clinic_now(moment).hour == 15

    def test_today_local_uses_the_clinic_timezone(self) -> None:
        moment = datetime(2026, 9, 30, 20, 0, tzinfo=__import__("datetime").UTC)
        assert today_local(moment) == date(2026, 10, 1)

    def test_utc_now_is_timezone_aware(self) -> None:
        assert utc_now().tzinfo is not None


class TestBusinessDates:
    def test_date_format_round_trip(self) -> None:
        assert to_date_string(date(2026, 10, 1)) == "2026-10-01"
        assert parse_date("2026-10-01") == date(2026, 10, 1)

    def test_range_bounds_are_inclusive(self) -> None:
        start, end = range_bounds(7, today=date(2026, 10, 10))
        assert start == "2026-10-04"
        assert end == "2026-10-10"

    def test_day_bounds(self) -> None:
        assert day_bounds(date(2026, 10, 1)) == ("2026-10-01", "2026-10-01")

    def test_month_bounds_handle_december(self) -> None:
        assert month_bounds(2026, 12) == ("2026-12-01", "2026-12-31")
        assert month_bounds(2026, 2) == ("2026-02-01", "2026-02-28")

    def test_quarter_bounds(self) -> None:
        assert quarter_bounds(2026, 1) == ("2026-01-01", "2026-03-31")
        assert quarter_bounds(2026, 4) == ("2026-10-01", "2026-12-31")
        with pytest.raises(ValueError):
            quarter_bounds(2026, 5)

    def test_year_bounds(self) -> None:
        assert year_bounds(2026) == ("2026-01-01", "2026-12-31")

    def test_display_date_uses_a_readable_format(self) -> None:
        assert format_display_date(date(2026, 10, 1)) == "01 Oct 2026"
        assert format_display_date(date(2026, 10, 1), locale="bn") == "০১ Oct ২০২৬"


class TestClinicClock:
    def test_minutes_and_time_round_trip(self) -> None:
        assert minutes_from_midnight(time(10, 30)) == 630
        assert time_from_minutes(630) == time(10, 30)

    def test_time_from_minutes_clamps_rather_than_raising(self) -> None:
        assert time_from_minutes(-5) == time(0, 0)
        assert time_from_minutes(24 * 60 + 30) == time(23, 59)

    def test_time_range_formatting(self) -> None:
        assert format_time_range(630, 30) == "10:30 – 11:00"
        assert format_time_range(630, 30, locale="bn") == "১০:৩০ – ১১:০০"

    @pytest.mark.parametrize(
        ("born", "today", "expected"),
        [
            (date(1992, 10, 1), date(2026, 10, 1), "34 years"),
            (date(2026, 10, 1), date(2026, 10, 1), "0 days"),
            (date(2026, 3, 1), date(2026, 10, 1), "7 months"),
            (date(2025, 10, 1), date(2026, 10, 1), "1 year"),
        ],
    )
    def test_humanised_age(self, born: date, today: date, expected: str) -> None:
        assert humanise_age(born, today=today) == expected

    def test_future_birth_dates_do_not_produce_nonsense(self) -> None:
        assert humanise_age(date(2030, 1, 1), today=date(2026, 10, 1)) == "—"

    def test_days_between(self) -> None:
        from dentivapro.core.timeutil import days_between

        assert days_between(date(2026, 10, 1), date(2026, 10, 8)) == 7
        assert days_between(date(2026, 10, 1), date(2026, 10, 1) + timedelta(days=1)) == 1
