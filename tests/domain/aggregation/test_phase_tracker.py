"""Tests for the phase tracker control-mode fold."""

from __future__ import annotations

from o7debrief.domain.aggregation.phase_tracker import (
    DISEMBARK,
    DOCK_SRV,
    EMBARK,
    LAUNCH_SRV,
    SRV_DESTROYED,
    SRV_FLAG,
    mode_at_each,
)
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.enums import ActivityMode
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int, fields: tuple = ()) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), fields)


def test_empty_events_yields_empty() -> None:
    assert mode_at_each(()) == ()


def test_default_mode_is_ship() -> None:
    modes = mode_at_each((_ev("FSDJump", 0),))
    assert modes == (ActivityMode.SHIP,)


def test_launch_srv_enters_srv_then_dock_returns_to_ship() -> None:
    events = (
        _ev("FSDJump", 0),
        _ev(LAUNCH_SRV, 1),
        _ev("FSDJump", 2),
        _ev(DOCK_SRV, 3),
        _ev("FSDJump", 4),
    )
    modes = mode_at_each(events)
    assert modes == (
        ActivityMode.SHIP,
        ActivityMode.SRV,
        ActivityMode.SRV,
        ActivityMode.SHIP,
        ActivityMode.SHIP,
    )


def test_srv_destroyed_returns_to_ship() -> None:
    events = (_ev(LAUNCH_SRV, 0), _ev(SRV_DESTROYED, 1))
    modes = mode_at_each(events)
    assert modes == (ActivityMode.SRV, ActivityMode.SHIP)


def test_disembark_enters_on_foot() -> None:
    events = (_ev(DISEMBARK, 0),)
    assert mode_at_each(events) == (ActivityMode.ON_FOOT,)


def test_embark_without_srv_flag_returns_to_ship() -> None:
    events = (_ev(DISEMBARK, 0), _ev(EMBARK, 1))
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SHIP)


def test_embark_with_srv_flag_returns_to_srv() -> None:
    events = (
        _ev(DISEMBARK, 0),
        _ev(EMBARK, 1, ((SRV_FLAG, True),)),
    )
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SRV)


def test_embark_with_srv_flag_false_returns_to_ship() -> None:
    events = (
        _ev(DISEMBARK, 0),
        _ev(EMBARK, 1, ((SRV_FLAG, False),)),
    )
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SHIP)
