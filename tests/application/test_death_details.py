"""Tests for gathering what the journal knows about each death.

The ``Died`` event carries almost nothing, so the readings come from the
events around it. These cover the victim, the SRV that supersedes the
mothership when one was lost, the killer's ship named properly from the scan
that preceded the kill, then the rebuy stated by the resurrection after it.
"""

from __future__ import annotations

from o7debrief.application.services.death_details import (
    KILLER_SHIP_FIELD,
    KILLER_SQUADRON_FIELD,
    REBUY_COST_FIELD,
    VICTIM_NAME_FIELD,
    VICTIM_SHIP_FIELD,
    VICTIM_SHIP_NAME_FIELD,
    deaths_in,
    stamp_deaths,
)
from o7debrief.application.services.ship_state import ship_history
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from tests.application import domain_builders as build
from tests.application.fakes import commander, event

# Instants for the fixtures, ordered as the journal writes them.
_LOGIN = 0
_SCAN = 5
_LOSS = 9
_DEATH = 10
_RESURRECT = 20
_SECOND_DEATH = 30

# The journal's scan stage for a fully identified target.
_FULL_SCAN = 3
_REBUY_COST = 11312783


def _login() -> tuple:
    return (
        event(
            "LoadGame",
            _LOGIN,
            Ship="Cutter",
            Ship_Localised="Imperial Cutter",
            ShipName="Majestic Darkness",
        ),
    )


def _death_moment(second: int = _DEATH):
    return build.moment(MomentKind.DEATH, ActivityDomain.COMBAT, second)


def _stamp(moments: tuple, events: tuple) -> tuple:
    return stamp_deaths(moments, deaths_in(events), ship_history(events), commander())


def test_a_death_names_the_commander_and_the_ship_of_that_moment() -> None:
    events = _login() + (event("Died", _DEATH),)
    detail = dict(_stamp((_death_moment(),), events)[0].detail)
    assert detail[VICTIM_NAME_FIELD] == "Jameson"
    assert detail[VICTIM_SHIP_FIELD] == "Imperial Cutter"
    assert detail[VICTIM_SHIP_NAME_FIELD] == "Majestic Darkness"


def test_an_srv_lost_supersedes_the_mothership_it_launched_from() -> None:
    # Four of six real deaths were SRV losses; naming the ship would be wrong.
    events = _login() + (
        event(
            "SRVDestroyed", _LOSS, SRVType="testbuggy", SRVType_Localised="SRV Scarab"
        ),
        event("Died", _DEATH),
    )
    detail = dict(_stamp((_death_moment(),), events)[0].detail)
    assert detail[VICTIM_SHIP_FIELD] == "SRV Scarab"
    # An SRV carries no custom name, so the ship's must not follow it across.
    assert VICTIM_SHIP_NAME_FIELD not in detail


def test_an_srv_lost_before_a_resurrection_is_not_blamed_for_a_later_death() -> None:
    events = _login() + (
        event("SRVDestroyed", _LOSS, SRVType_Localised="SRV Scarab"),
        event("Died", _DEATH),
        event("Resurrect", _RESURRECT, Option="rejoin", Cost=0),
        event("Died", _SECOND_DEATH),
    )
    stamped = _stamp((_death_moment(), _death_moment(_SECOND_DEATH)), events)
    assert dict(stamped[0].detail)[VICTIM_SHIP_FIELD] == "SRV Scarab"
    assert dict(stamped[1].detail)[VICTIM_SHIP_FIELD] == "Imperial Cutter"


def test_the_killers_ship_is_named_from_the_scan_that_preceded_the_kill() -> None:
    # Died gives the raw "cobramkv"; the scan gives "Cobra Mk V" and a squadron.
    events = _login() + (
        event(
            "ShipTargeted",
            _SCAN,
            ScanStage=_FULL_SCAN,
            Ship="cobramkv",
            Ship_Localised="Cobra Mk V",
            PilotName_Localised="CMDR Russet Meles",
            SquadronID="JOME",
        ),
        event("Died", _DEATH, KillerName="Cmdr Russet Meles", KillerShip="cobramkv"),
    )
    detail = dict(_stamp((_death_moment(),), events)[0].detail)
    assert detail[KILLER_SHIP_FIELD] == "Cobra Mk V"
    assert detail[KILLER_SQUADRON_FIELD] == "JOME"


def test_a_scan_of_a_different_pilot_does_not_name_the_killers_ship() -> None:
    events = _login() + (
        event(
            "ShipTargeted",
            _SCAN,
            ScanStage=_FULL_SCAN,
            Ship_Localised="Krait Phantom",
            PilotName_Localised="Someone Else",
        ),
        event("Died", _DEATH, KillerName="Cmdr Russet Meles"),
    )
    assert KILLER_SHIP_FIELD not in dict(_stamp((_death_moment(),), events)[0].detail)


def test_a_partial_scan_names_nothing_because_it_identifies_nobody() -> None:
    events = _login() + (
        event("ShipTargeted", _SCAN, ScanStage=1, Ship_Localised="Krait Phantom"),
        event(
            "ShipTargeted",
            _SCAN,
            ScanStage=_FULL_SCAN,
            Ship_Localised="Krait Phantom",
        ),
        event("Died", _DEATH, KillerName="Cmdr Russet Meles"),
    )
    assert KILLER_SHIP_FIELD not in dict(_stamp((_death_moment(),), events)[0].detail)


def test_the_rebuy_comes_from_the_resurrection_that_follows() -> None:
    events = _login() + (
        event("Died", _DEATH),
        event("Resurrect", _RESURRECT, Option="rebuy", Cost=_REBUY_COST),
    )
    detail = dict(_stamp((_death_moment(),), events)[0].detail)
    assert detail[REBUY_COST_FIELD] == _REBUY_COST


def test_a_resurrection_that_cost_nothing_records_no_rebuy() -> None:
    events = _login() + (
        event("Died", _DEATH),
        event("Resurrect", _RESURRECT, Option="rejoin", Cost=0),
    )
    assert REBUY_COST_FIELD not in dict(_stamp((_death_moment(),), events)[0].detail)


def test_a_non_integer_cost_is_not_read_as_a_rebuy() -> None:
    events = _login() + (
        event("Died", _DEATH),
        event("Resurrect", _RESURRECT, Option="rebuy", Cost="lots"),
    )
    assert REBUY_COST_FIELD not in dict(_stamp((_death_moment(),), events)[0].detail)


def test_a_resurrection_with_no_death_before_it_is_ignored() -> None:
    events = _login() + (event("Resurrect", _RESURRECT, Cost=_REBUY_COST),)
    assert deaths_in(events) == ()


def test_a_death_moment_with_no_matching_event_still_names_the_victim() -> None:
    # The moment stands even where the gathered readings cannot be matched.
    detail = dict(_stamp((_death_moment(),), _login())[0].detail)
    assert detail[VICTIM_NAME_FIELD] == "Jameson"
    assert REBUY_COST_FIELD not in detail


def test_other_kinds_of_moment_are_returned_untouched() -> None:
    jump = build.moment(MomentKind.JUMP, ActivityDomain.TRAVEL, _LOGIN)
    assert _stamp((jump,), _login())[0] is jump


def test_a_stale_reading_already_on_the_detail_is_replaced_not_repeated() -> None:
    stale = ((VICTIM_SHIP_FIELD, "Sidewinder"),)
    moment = build.moment(MomentKind.DEATH, ActivityDomain.COMBAT, _DEATH, detail=stale)
    stamped = _stamp((moment,), _login() + (event("Died", _DEATH),))
    ships = [value for key, value in stamped[0].detail if key == VICTIM_SHIP_FIELD]
    assert ships == ["Imperial Cutter"]
