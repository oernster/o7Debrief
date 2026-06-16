"""Tests for the per-domain rollups and the ActivityRollup aggregate."""

from __future__ import annotations

from o7debrief.domain.model.rollups import (
    ActivityRollup,
    CarrierRollup,
    CombatRollup,
    EngineeringRollup,
    ExobiologyRollup,
    ExplorationRollup,
    FlightRollup,
    MiningRollup,
    MissionRollup,
    OnFootRollup,
    SrvRollup,
    TradeRollup,
)
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import ActivityDomain, ActivityMode


def test_rollup_defaults_are_empty() -> None:
    assert FlightRollup().jumps == 0
    assert FlightRollup().distance_ly == 0
    assert ExplorationRollup().data_sold.value == 0
    assert CombatRollup().bounties.value == 0
    assert CombatRollup().bonds.value == 0
    assert TradeRollup().spent.value == 0
    assert TradeRollup().earned.value == 0
    assert MiningRollup().refined == 0
    assert MissionRollup().rewards.value == 0
    assert EngineeringRollup().crafted == 0
    assert CarrierRollup().jumps == 0
    assert ExobiologyRollup().sold.value == 0
    assert SrvRollup().deployments == 0
    assert OnFootRollup().disembarks == 0
    assert OnFootRollup().settlements == 0


def test_empty_activity_rollup_has_no_active_domains() -> None:
    rollup = ActivityRollup()
    assert rollup.active_domains == ()
    assert rollup.modes_used == ()


def test_active_domains_lists_only_present_in_canonical_order() -> None:
    rollup = ActivityRollup(
        combat=CombatRollup(kills=1),
        flight=FlightRollup(jumps=1),
    )
    assert rollup.active_domains == (
        ActivityDomain.TRAVEL,
        ActivityDomain.COMBAT,
    )


def test_active_domains_with_all_present_covers_every_branch() -> None:
    rollup = ActivityRollup(
        flight=FlightRollup(),
        exploration=ExplorationRollup(),
        combat=CombatRollup(),
        trade=TradeRollup(),
        mining=MiningRollup(),
        missions=MissionRollup(),
        engineering=EngineeringRollup(),
        carrier=CarrierRollup(),
        exobiology=ExobiologyRollup(),
        srv=SrvRollup(),
        on_foot=OnFootRollup(),
        modes_used=(ActivityMode.SHIP,),
    )
    assert rollup.active_domains == (
        ActivityDomain.TRAVEL,
        ActivityDomain.EXPLORATION,
        ActivityDomain.COMBAT,
        ActivityDomain.TRADE,
        ActivityDomain.MINING,
        ActivityDomain.MISSIONS,
        ActivityDomain.ENGINEERING,
        ActivityDomain.CARRIER,
        ActivityDomain.EXOBIOLOGY,
        ActivityDomain.SRV,
        ActivityDomain.ON_FOOT,
    )
    assert rollup.modes_used == (ActivityMode.SHIP,)


def test_explicit_credits_fields_round_trip() -> None:
    rollup = ExplorationRollup(data_sold=Credits(1234))
    assert rollup.data_sold.value == 1234
