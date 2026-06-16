"""Tests for AutoDebriefTrigger: prime-once, then fire once per Shutdown."""

from __future__ import annotations

from o7debrief.application.services.auto_debrief_trigger import AutoDebriefTrigger
from o7debrief.domain.aggregation.session_bracketer import LOAD_GAME, SHUTDOWN
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), ())


def test_first_observation_primes_without_firing() -> None:
    # A completed session already in the journal at startup is recorded, not
    # debriefed, so launching the app never reopens an old debrief.
    trigger = AutoDebriefTrigger()
    events = (_ev(LOAD_GAME, 0), _ev(SHUTDOWN, 1))
    assert trigger.debrief_due(events) is False


def test_fires_once_when_a_new_session_ends() -> None:
    trigger = AutoDebriefTrigger()
    trigger.debrief_due(())  # prime with an empty journal
    events = (_ev(LOAD_GAME, 0), _ev("FSDJump", 1), _ev(SHUTDOWN, 2))
    assert trigger.debrief_due(events) is True


def test_does_not_fire_twice_for_the_same_shutdown() -> None:
    trigger = AutoDebriefTrigger()
    trigger.debrief_due(())
    events = (_ev(LOAD_GAME, 0), _ev(SHUTDOWN, 2))
    assert trigger.debrief_due(events) is True
    assert trigger.debrief_due(events) is False


def test_does_not_fire_while_the_session_is_in_progress() -> None:
    trigger = AutoDebriefTrigger()
    trigger.debrief_due(())
    events = (_ev(LOAD_GAME, 0), _ev("FSDJump", 1))  # no Shutdown yet
    assert trigger.debrief_due(events) is False


def test_re_arms_for_a_later_session() -> None:
    trigger = AutoDebriefTrigger()
    trigger.debrief_due(())
    first = (_ev(LOAD_GAME, 0), _ev(SHUTDOWN, 1))
    assert trigger.debrief_due(first) is True
    # A later run appends and ends with its own Shutdown.
    second = first + (_ev(LOAD_GAME, 2), _ev(SHUTDOWN, 3))
    assert trigger.debrief_due(second) is True


def test_primes_to_an_in_progress_session_then_fires_on_its_shutdown() -> None:
    trigger = AutoDebriefTrigger()
    in_progress = (_ev(LOAD_GAME, 0), _ev("FSDJump", 1))
    assert trigger.debrief_due(in_progress) is False  # primes (no completed run)
    ended = in_progress + (_ev(SHUTDOWN, 2),)
    assert trigger.debrief_due(ended) is True
