"""Tests for the EventTime value object."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from o7debrief.domain.errors import InvalidEventTimeError
from o7debrief.domain.value_objects.event_time import EventTime


def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()


def test_parse_with_trailing_z_preserves_original_and_computes_epoch() -> None:
    stamp = "2024-01-01T10:00:00Z"
    result = EventTime.parse(stamp)
    assert result.iso_utc == stamp
    assert result.epoch_s == _epoch("2024-01-01T10:00:00+00:00")


def test_parse_with_explicit_offset() -> None:
    stamp = "2024-01-01T12:00:00+02:00"
    result = EventTime.parse(stamp)
    assert result.iso_utc == stamp
    assert result.epoch_s == _epoch(stamp)


def test_parse_naive_input_is_assumed_utc() -> None:
    stamp = "2024-01-01T10:00:00"
    result = EventTime.parse(stamp)
    expected = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    assert result.epoch_s == expected
    assert result.iso_utc == stamp


def test_parse_empty_string_raises() -> None:
    with pytest.raises(InvalidEventTimeError):
        EventTime.parse("")


def test_parse_unparseable_string_raises() -> None:
    with pytest.raises(InvalidEventTimeError):
        EventTime.parse("not-a-timestamp")


def test_post_init_rejects_empty_iso_utc() -> None:
    with pytest.raises(InvalidEventTimeError):
        EventTime(iso_utc="", epoch_s=0.0)


def test_post_init_accepts_nonempty_iso_utc() -> None:
    instant = EventTime(iso_utc="x", epoch_s=1.5)
    assert instant.epoch_s == 1.5


def test_lt_true_and_false() -> None:
    earlier = EventTime.parse("2024-01-01T10:00:00Z")
    later = EventTime.parse("2024-01-01T10:00:01Z")
    assert earlier < later
    assert not (later < earlier)


def test_le_true_for_equal_and_less() -> None:
    a = EventTime.parse("2024-01-01T10:00:00Z")
    b = EventTime.parse("2024-01-01T10:00:00Z")
    c = EventTime.parse("2024-01-01T10:00:05Z")
    assert a <= b
    assert a <= c


def test_le_false_when_greater() -> None:
    a = EventTime.parse("2024-01-01T10:00:05Z")
    b = EventTime.parse("2024-01-01T10:00:00Z")
    assert not (a <= b)
