"""Tests for the ValueFormatter and NumberFormat config."""

from __future__ import annotations

from o7debrief.application.services.value_formatter import (
    NumberFormat,
    ValueFormatter,
)
from tests.application.fakes import number_format


def _grouped() -> ValueFormatter:
    return ValueFormatter(number_format())


def _ungrouped() -> ValueFormatter:
    fmt = number_format()
    plain = NumberFormat(
        credits_suffix=fmt.credits_suffix,
        coins_suffix=fmt.coins_suffix,
        distance_suffix=fmt.distance_suffix,
        thousands=False,
        duration_format=fmt.duration_format,
        time_format=fmt.time_format,
        datetime_format=fmt.datetime_format,
        date_format=fmt.date_format,
        month_format=fmt.month_format,
        timezone_label=fmt.timezone_label,
    )
    return ValueFormatter(plain)


def test_integer_groups_thousands_when_enabled() -> None:
    assert _grouped().integer(1234567) == "1,234,567"


def test_integer_does_not_group_when_disabled() -> None:
    assert _ungrouped().integer(1234567) == "1234567"


def test_credits_and_distance_carry_suffixes() -> None:
    fmt = _grouped()

    assert fmt.credits(14320500) == "14,320,500 Cr"
    # A distance keeps one decimal place: the journal states jumps as real
    # quantities, so 7.773 must not collapse to 8.
    assert fmt.distance(120) == "120.0 ly"
    assert fmt.distance(7.773) == "7.8 ly"
    assert fmt.distance(3296.15) == "3,296.2 ly"


def test_coins_carry_their_own_suffix() -> None:
    fmt = _grouped()

    assert fmt.coins(2500) == "2,500 Merc Coins"
    assert fmt.coins(0) == "0 Merc Coins"


def test_coins_respect_the_grouping_flag() -> None:
    assert _ungrouped().coins(2500) == "2500 Merc Coins"


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


def test_percent_level_carries_no_sign() -> None:
    # A level says where a standing sits, so a sign would misread as movement.
    fmt = _grouped()

    assert fmt.percent_level(73) == "73%"
    assert fmt.percent_level(0) == "0%"


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


def test_date_returns_an_unambiguous_spelled_day() -> None:
    """The day is spelled, so it cannot be read as either MM/DD or DD/MM."""
    assert _grouped().date("2026-08-13T15:15:30Z") == "Thu 13 Aug 2026"


def test_date_reads_the_instant_in_utc_not_a_local_zone() -> None:
    """An instant late in the UTC day stays on that day, whatever the reader's clock.

    Times are displayed unconverted, so the day must be read the same way or a
    row lands under a heading it does not belong to.
    """
    assert _grouped().date("2026-08-13T23:50:00Z") == "Thu 13 Aug 2026"
    assert _grouped().time("2026-08-13T23:50:00Z") == "23:50:00"


def test_timezone_label_names_the_zone_the_report_quotes() -> None:
    """The formatter carries the label so no renderer holds one of its own."""
    assert _grouped().timezone_label() == "UTC"
