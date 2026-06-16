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


def test_empty_input_returns_empty() -> None:
    assert latest_session(()) == ()


def test_no_shutdown_runs_to_the_end_of_the_log() -> None:
    # No Shutdown anywhere: the whole log is the single ongoing session, even
    # with no LoadGame (the app may have attached after the game had started).
    events = (_ev("FSDJump", 0), _ev("Bounty", 1))
    result = latest_session(events)
    assert [e.event_type for e in result] == ["FSDJump", "Bounty"]


def test_two_complete_sessions_returns_only_the_latest() -> None:
    # Two clean runs in one log. The latest session is the second run (after
    # the first Shutdown); the first run is discarded entirely.
    events = (
        _ev(LOAD_GAME, 0),
        _ev("FSDJump", 1),
        _ev(SHUTDOWN, 2),
        _ev(LOAD_GAME, 3),
        _ev("Bounty", 4),
        _ev(SHUTDOWN, 5),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [LOAD_GAME, "Bounty", SHUTDOWN]
    assert result[0].event_time.iso_utc == "2024-01-01T10:00:03Z"
    assert result[-1].event_time.iso_utc == "2024-01-01T10:00:05Z"


def test_main_menu_rollover_keeps_the_whole_run_in_one_session() -> None:
    # The micro-session bug this fixes: Elite fires a fresh LoadGame on every
    # main-menu return, so a run that touched the menu must NOT collapse to its
    # final leg. After a first clean run, the latest run reloads twice yet is
    # bracketed as one session, from after the first Shutdown to the last.
    events = (
        _ev(LOAD_GAME, 0),  # first run
        _ev("FSDJump", 1),
        _ev(SHUTDOWN, 2),  # first run ends cleanly
        _ev(LOAD_GAME, 3),  # latest run begins
        _ev("FSDJump", 4),
        _ev(LOAD_GAME, 5),  # main-menu return mid-run (the rollover)
        _ev("Bounty", 6),
        _ev("FSDJump", 7),
        _ev(SHUTDOWN, 8),  # latest run ends cleanly
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [
        LOAD_GAME,
        "FSDJump",
        LOAD_GAME,
        "Bounty",
        "FSDJump",
        SHUTDOWN,
    ]
    assert result[0].event_time.iso_utc == "2024-01-01T10:00:03Z"
    assert result[-1].event_time.iso_utc == "2024-01-01T10:00:08Z"


def test_crash_after_a_clean_session_runs_to_end_of_log() -> None:
    # A clean run, then a second run that crashed (no trailing Shutdown). The
    # latest session is the crashed run, from after the first Shutdown to the
    # end of the log, bundling its own main-menu rollover.
    events = (
        _ev(LOAD_GAME, 0),
        _ev(SHUTDOWN, 1),  # first run ends cleanly
        _ev(LOAD_GAME, 2),  # crashed run begins
        _ev("FSDJump", 3),
        _ev(LOAD_GAME, 4),  # rollover, then a crash with no Shutdown
        _ev("Bounty", 5),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [
        LOAD_GAME,
        "FSDJump",
        LOAD_GAME,
        "Bounty",
    ]
    assert result[0].event_time.iso_utc == "2024-01-01T10:00:02Z"


def test_session_without_trailing_shutdown_runs_to_end() -> None:
    events = (
        _ev(LOAD_GAME, 0),
        _ev("FSDJump", 1),
        _ev("Bounty", 2),
    )
    result = latest_session(events)
    assert [e.event_type for e in result] == [LOAD_GAME, "FSDJump", "Bounty"]


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
