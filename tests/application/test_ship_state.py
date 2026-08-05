"""Tests for the active-ship fold over journal events.

The ship is a level: it holds from the event that named it until one moves it
on. These cover the closing state the header uses, the state in force at an
arbitrary instant, the localised naming rules and the empty cases.
"""

from __future__ import annotations

from o7debrief.application.services.ship_state import ship_history
from tests.application.fakes import at, event

# Instants used across the cases, named so a lookup reads as a point in time.
_LOGIN = 0
_SWAP = 10
_AFTER_SWAP = 20
_NO_SHIP = ("", "")


def _epoch(second: int) -> float:
    return at(second).epoch_s


def test_closing_state_is_the_latest_ship_and_name() -> None:
    events = (
        event("LoadGame", _LOGIN, Ship="Cutter", Ship_Localised="Imperial Cutter"),
        event("Loadout", _LOGIN, Ship="cutter", ShipName="Majestic Darkness"),
    )
    assert ship_history(events).latest() == ("Imperial Cutter", "Majestic Darkness")


def test_state_at_an_instant_predates_a_later_swap() -> None:
    # The hull at the moment asked about, not the one the session ended in.
    events = (
        event(
            "LoadGame",
            _LOGIN,
            Ship="Cutter",
            Ship_Localised="Imperial Cutter",
            ShipName="Majestic Darkness",
        ),
        event(
            "ShipyardSwap",
            _SWAP,
            ShipType="sidewinder",
            ShipType_Localised="Sidewinder",
        ),
    )
    history = ship_history(events)
    assert history.at(_epoch(_LOGIN)) == ("Imperial Cutter", "Majestic Darkness")
    assert history.at(_epoch(_AFTER_SWAP)) == ("Sidewinder", "")
    assert history.latest() == ("Sidewinder", "")


def test_state_before_the_first_ship_event_is_unknown() -> None:
    events = (event("LoadGame", _SWAP, Ship="Cutter"),)
    assert ship_history(events).at(_epoch(_LOGIN)) == _NO_SHIP


def test_no_ship_events_gives_no_state() -> None:
    history = ship_history((event("FSDJump", _LOGIN, StarSystem="Sol"),))
    assert history.states == ()
    assert history.latest() == _NO_SHIP
    assert history.at(_epoch(_LOGIN)) == _NO_SHIP


def test_a_ship_named_only_later_is_still_named_at_the_earlier_instant() -> None:
    # A Loadout that spells the hull readably is naming it, not changing it, so
    # the earlier state reads the same rather than falling back to the symbol.
    events = (
        event("LoadGame", _LOGIN, Ship="Cutter"),
        event("Loadout", _SWAP, Ship="cutter", Ship_Localised="Imperial Cutter"),
    )
    assert ship_history(events).at(_epoch(_LOGIN)) == ("Imperial Cutter", "")


def test_internal_symbol_stands_in_when_no_localised_form_appears() -> None:
    events = (event("LoadGame", _LOGIN, Ship="Cutter"),)
    assert ship_history(events).latest() == ("Cutter", "")


def test_repeated_boarding_of_one_ship_records_a_single_state() -> None:
    events = tuple(
        event("Loadout", second, Ship="cutter", ShipName="Majestic Darkness")
        for second in (_LOGIN, _SWAP, _AFTER_SWAP)
    )
    assert len(ship_history(events).states) == 1


def test_a_custom_name_does_not_follow_the_commander_to_a_new_hull() -> None:
    events = (
        event("Loadout", _LOGIN, Ship="cutter", ShipName="Majestic Darkness"),
        event("ShipyardSwap", _SWAP, ShipType="sidewinder"),
    )
    assert ship_history(events).latest() == ("sidewinder", "")


def test_an_event_naming_no_ship_leaves_the_state_alone() -> None:
    # A Loadout without a Ship field carries a name for the ship already in use.
    events = (
        event("LoadGame", _LOGIN, Ship="Cutter"),
        event("Loadout", _SWAP, ShipName="Majestic Darkness"),
    )
    assert ship_history(events).latest() == ("Cutter", "Majestic Darkness")


def test_a_blank_ship_field_is_treated_as_absent() -> None:
    events = (event("LoadGame", _LOGIN, Ship="   "),)
    assert ship_history(events).latest() == _NO_SHIP
