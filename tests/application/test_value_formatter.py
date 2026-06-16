"""Tests for the ValueFormatter and NumberFormat config."""

from __future__ import annotations

from tests.application.fakes import number_format

from o7debrief.application.services.value_formatter import (
    NumberFormat,
    ValueFormatter,
)


def _grouped() -> ValueFormatter:
    return ValueFormatter(number_format())


def _ungrouped() -> ValueFormatter:
    fmt = number_format()
    plain = NumberFormat(
        credits_suffix=fmt.credits_suffix,
        distance_suffix=fmt.distance_suffix,
        thousands=False,
        duration_format=fmt.duration_format,
        time_format=fmt.time_format,
        datetime_format=fmt.datetime_format,
    )
    return ValueFormatter(plain)


def test_integer_groups_thousands_when_enabled() -> None:
    assert _grouped().integer(1234567) == "1,234,567"


def test_integer_does_not_group_when_disabled() -> None:
    assert _ungrouped().integer(1234567) == "1234567"


def test_credits_and_distance_carry_suffixes() -> None:
    fmt = _grouped()

    assert fmt.credits(14320500) == "14,320,500 Cr"
    assert fmt.distance(120) == "120 ly"


def test_signed_credits_prefixes_sign_both_ways() -> None:
    fmt = _grouped()

    assert fmt.signed_credits(2500) == "+2,500 Cr"
    assert fmt.signed_credits(0) == "+0 Cr"
    assert fmt.signed_credits(-2500) == "-2,500 Cr"


def test_percent_prefixes_sign_both_ways() -> None:
    fmt = _grouped()

    assert fmt.percent(12) == "+12%"
    assert fmt.percent(0) == "+0%"
    assert fmt.percent(-5) == "-5%"


def test_duration_uses_configured_format() -> None:
    fmt = _grouped()

    # Two hours, three minutes and a few trailing seconds.
    seconds = (2 * 3600) + (3 * 60) + 12
    assert fmt.duration(float(seconds)) == "2h 3m"


def test_time_formats_zulu_timestamp() -> None:
    assert _grouped().time("2026-06-15T10:30:45Z") == "10:30:45"


def test_datetime_formats_zulu_timestamp() -> None:
    assert _grouped().datetime("2026-06-15T10:30:45Z") == "2026-06-15 10:30:45"


def test_parse_handles_explicit_offset_without_z() -> None:
    # An explicit +00:00 offset exercises the non-Zulu, aware branch.
    assert _grouped().time("2026-06-15T10:30:45+00:00") == "10:30:45"


def test_parse_handles_naive_timestamp() -> None:
    # No offset and no Z exercises the tzinfo-None branch (assumed UTC).
    assert _grouped().datetime("2026-06-15T10:30:45") == "2026-06-15 10:30:45"
