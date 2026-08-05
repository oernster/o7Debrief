"""Tests for the location fold and the systems it reports.

Location is read from the events rather than from the derived moments, since
most location-bearing events produce no moment. These cover the endpoints, the
visit count, the events that must not be read as the commander's position and
the carry-forward for a session that names no system at all.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.location_state import location_history
from tests.application.fakes import commander, event, spec

_FIRST = 0
_SECOND = 10
_THIRD = 20


def _builder() -> DebriefBuilder:
    return DebriefBuilder(spec())


def test_endpoints_are_the_first_and_last_systems_named() -> None:
    events = (
        event("Location", _FIRST, StarSystem="Sol"),
        event("FSDJump", _SECOND, StarSystem="Lave"),
        event("SupercruiseExit", _THIRD, StarSystem="Diso"),
    )
    history = location_history(events)
    assert history.endpoints() == ("Sol", "Diso")
    assert history.distinct_count() == 3


def test_any_event_naming_a_system_is_a_reading() -> None:
    # No whitelist of event types: a market screen states a position too.
    history = location_history((event("Market", _FIRST, StarSystem="Sol"),))
    assert history.latest() == "Sol"


def test_a_carrier_location_is_not_the_commanders_position() -> None:
    events = (
        event("Location", _FIRST, StarSystem="Sol"),
        event("CarrierLocation", _SECOND, StarSystem="Colonia"),
    )
    assert location_history(events).endpoints() == ("Sol", "Sol")


def test_repeated_readings_of_one_system_count_as_one_visit() -> None:
    events = tuple(
        event("Docked", second, StarSystem="Sol")
        for second in (_FIRST, _SECOND, _THIRD)
    )
    history = location_history(events)
    assert history.systems == ("Sol",)
    assert history.distinct_count() == 1


def test_a_system_returned_to_is_an_endpoint_but_not_a_second_visit() -> None:
    events = (
        event("Location", _FIRST, StarSystem="Sol"),
        event("FSDJump", _SECOND, StarSystem="Lave"),
        event("FSDJump", _THIRD, StarSystem="Sol"),
    )
    history = location_history(events)
    assert history.endpoints() == ("Sol", "Sol")
    assert history.distinct_count() == 2


def test_a_blank_or_non_string_system_is_not_a_reading() -> None:
    events = (
        event("Location", _FIRST, StarSystem="   "),
        event("FSDJump", _SECOND, StarSystem=1234),
        event("Docked", _THIRD, Other="value"),
    )
    assert location_history(events).endpoints() is None


def test_a_session_that_names_a_system_reports_it_and_its_count() -> None:
    events = (
        event("Location", _FIRST, StarSystem="Sol"),
        event("FSDJump", _SECOND, StarSystem="Lave"),
    )
    debrief = _builder().build(commander(), events, ())
    assert str(debrief.start_system) == "Sol"
    assert str(debrief.end_system) == "Lave"
    assert debrief.systems_visited == 2


def test_a_session_naming_none_carries_the_last_known_system_forward() -> None:
    # The commander did not move, so the carried system is both endpoints and
    # the single system visited. Never zero: they were somewhere.
    events = (event("LoadGame", _FIRST, Ship="Cutter"),)
    debrief = _builder().build(commander(), events, (), "Achenar")
    assert str(debrief.start_system) == "Achenar"
    assert str(debrief.end_system) == "Achenar"
    assert debrief.systems_visited == 1


def test_a_session_with_no_system_and_no_history_reports_nothing_known() -> None:
    events = (event("LoadGame", _FIRST, Ship="Cutter"),)
    debrief = _builder().build(commander(), events, ())
    assert debrief.start_system is None
    assert debrief.end_system is None
    assert debrief.systems_visited is None
