"""Tests for the SessionWindow value object."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidSessionWindowError
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow


def _at(sec: int) -> EventTime:
    return EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z")


def test_valid_window_duration() -> None:
    window = SessionWindow(start=_at(0), end=_at(30), clean_shutdown=True)
    assert window.duration_s == 30.0
    assert window.clean_shutdown is True


def test_zero_length_window_allowed() -> None:
    instant = _at(5)
    window = SessionWindow(start=instant, end=instant, clean_shutdown=False)
    assert window.duration_s == 0.0


def test_end_before_start_raises() -> None:
    with pytest.raises(InvalidSessionWindowError):
        SessionWindow(start=_at(30), end=_at(0), clean_shutdown=False)
