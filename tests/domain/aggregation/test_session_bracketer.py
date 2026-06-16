"""Tests for session isolation: the bracketer keystone."""

from __future__ import annotations

import pytest

from o7debrief.domain.aggregation.session_bracketer import (
    LOAD_GAME,
    SHUTDOWN,
    latest_session,
    window_of,
)
from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), ())


def test_no_load_game_returns_empty() -> None:
    events = (_ev("FSDJump", 0), _ev("Bounty", 1))
    assert latest_session(events) == ()


def test_two_sessions_plus_rollover_returns_only_the_last_whole_session() -> None:
    # Session one (clean), session two interrupted by a mid-session rollover
    # (a second LoadGame), then the real final session ending in Shutdown.
    events = (
        _ev(LOAD_GAME, 0),  # session 1
        _ev("FSDJump", 1),
        _ev(SHUTDOWN, 2),  # session 1 ends cleanly
        _ev(LOAD_GAME, 3),  # session 2 begins
        _ev("FSDJump", 4),
        _ev(LOAD_GAME, 5),  # ROLLOVER: this is the last LoadGame
        _ev("Bounty", 6),
        _ev("FSDJump", 7),
        _ev(SHUTDOWN, 8),  # final session ends cleanly
    )
    result = latest_session(events)
    # Only the slice from the last LoadGame (sec 5) through Shutdown (sec 8).
    assert [e.event_type for e in result] == [
        LOAD_GAME,
        "Bounty",
        "FSDJump",
        SHUTDOWN,
    ]
    assert result[0].event_time.iso_utc == "2024-01-01T10:00:05Z"
    assert result[-1].event_time.iso_utc == "2024-01-01T10:00:08Z"


def test_session_without_trailing_shutdown_runs_to_end() -> None:
    events = (
        _ev(LOAD_GAME, 0),
        _ev("FSDJump", 1),
        _ev("Bounty", 2),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [LOAD_GAME, "FSDJump", "Bounty"]


def test_shutdown_before_last_load_game_is_ignored() -> None:
    # A Shutdown that precedes the last LoadGame must not terminate the slice.
    events = (
        _ev(SHUTDOWN, 0),
        _ev(LOAD_GAME, 1),
        _ev("FSDJump", 2),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [LOAD_GAME, "FSDJump"]


def test_defensive_sorting_of_unordered_input() -> None:
    # Feed events out of chronological order; bracketer must sort first.
    events = (
        _ev(SHUTDOWN, 8),
        _ev("Bounty", 6),
        _ev(LOAD_GAME, 5),
        _ev("FSDJump", 7),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [
        LOAD_GAME,
        "Bounty",
        "FSDJump",
        SHUTDOWN,
    ]


def test_window_of_clean_shutdown() -> None:
    session = (_ev(LOAD_GAME, 0), _ev("FSDJump", 5), _ev(SHUTDOWN, 10))
    window = window_of(session)
    assert window.start.iso_utc == "2024-01-01T10:00:00Z"
    assert window.end.iso_utc == "2024-01-01T10:00:10Z"
    assert window.clean_shutdown is True
    assert window.duration_s == 10.0


def test_window_of_crash_no_shutdown() -> None:
    session = (_ev(LOAD_GAME, 0), _ev("FSDJump", 5))
    window = window_of(session)
    assert window.clean_shutdown is False
    assert window.end.iso_utc == "2024-01-01T10:00:05Z"


def test_window_of_sorts_defensively() -> None:
    session = (_ev(SHUTDOWN, 10), _ev(LOAD_GAME, 0))
    window = window_of(session)
    assert window.start.iso_utc == "2024-01-01T10:00:00Z"
    assert window.end.iso_utc == "2024-01-01T10:00:10Z"
    assert window.clean_shutdown is True


def test_window_of_empty_raises() -> None:
    with pytest.raises(AggregationError):
        window_of(())
