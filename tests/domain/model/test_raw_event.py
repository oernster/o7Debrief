"""Tests for the RawEvent model."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidRawEventError
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.event_time import EventTime


def _at() -> EventTime:
    return EventTime.parse("2024-01-01T10:00:00Z")


def test_get_returns_value_on_hit() -> None:
    event = RawEvent("LoadGame", _at(), (("Commander", "Jameson"),))
    assert event.get("Commander") == "Jameson"


def test_get_returns_default_on_miss() -> None:
    event = RawEvent("LoadGame", _at(), (("Commander", "Jameson"),))
    assert event.get("Missing", "fallback") == "fallback"


def test_get_default_is_none_when_unspecified() -> None:
    event = RawEvent("LoadGame", _at(), ())
    assert event.get("anything") is None


def test_get_scans_past_non_matching_fields() -> None:
    event = RawEvent("X", _at(), (("a", 1), ("b", 2), ("c", 3)))
    assert event.get("c") == 3


def test_empty_event_type_raises() -> None:
    with pytest.raises(InvalidRawEventError):
        RawEvent("", _at(), ())
