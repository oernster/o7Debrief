"""Tests for the debrief assembler."""

from __future__ import annotations

from o7debrief.domain.aggregation.debrief_assembler import (
    STAR_SYSTEM_FIELD,
    assemble,
)
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.rules.rollup_spec import RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow

_SCHEMA = "9.9.9"


def _at(sec: int) -> EventTime:
    return EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z")


def _moment(
    kind: MomentKind,
    domain: ActivityDomain,
    sec: int,
    *,
    mode: ActivityMode = ActivityMode.SHIP,
    magnitude: int = 0,
    credits: int = 0,
    detail: tuple = (),
) -> ConceptualMoment:
    return ConceptualMoment(
        kind=kind,
        domain=domain,
        mode=mode,
        occurred_at=_at(sec),
        label=kind.name,
        magnitude=magnitude,
        credits_delta=Credits(credits),
        detail=detail,
    )


def _spec() -> RollupSpec:
    return RollupSpec(
        schema_version=_SCHEMA,
        rules=(),
        thresholds=ThresholdSet(
            long_jump_ly=20.0,
            big_payout_credits=1000000,
            high_value_exobio_credits=5000000,
        ),
        labels=(),
    )


def _window() -> SessionWindow:
    return SessionWindow(start=_at(0), end=_at(59), clean_shutdown=True)


def _commander() -> CommanderId:
    return CommanderId(fid="F1", name="Jameson")


def test_empty_session_has_no_domains_no_systems_zero_credits() -> None:
    debrief = assemble(_commander(), _window(), (), (), _spec())
    assert debrief.activity.active_domains == ()
    assert debrief.activity.modes_used == ()
    assert debrief.start_system is None
    assert debrief.end_system is None
    assert debrief.net_credits_delta.value == 0
    assert debrief.config_schema_version == _SCHEMA
    assert debrief.commander == _commander()


def test_schema_version_taken_from_spec() -> None:
    debrief = assemble(_commander(), _window(), (), (), _spec())
    assert debrief.config_schema_version == _SCHEMA


def test_full_session_populates_every_rollup() -> None:
    moments = (
        _moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 0, magnitude=8),
        _moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 1, magnitude=12),
        _moment(MomentKind.SCAN_BODY, ActivityDomain.EXPLORATION, 2),
        _moment(MomentKind.MAP_BODY, ActivityDomain.EXPLORATION, 3),
        _moment(MomentKind.HONK, ActivityDomain.EXPLORATION, 4),
        _moment(
            MomentKind.SELL_EXPLORATION,
            ActivityDomain.EXPLORATION,
            5,
            credits=30000,
        ),
        _moment(MomentKind.BOUNTY, ActivityDomain.COMBAT, 6, credits=50000),
        _moment(MomentKind.BOND, ActivityDomain.COMBAT, 7, credits=20000),
        _moment(MomentKind.MARKET_BUY, ActivityDomain.TRADE, 8, credits=1000),
        _moment(MomentKind.MARKET_SELL, ActivityDomain.TRADE, 9, credits=4000),
        _moment(MomentKind.REFINE, ActivityDomain.MINING, 10),
        _moment(
            MomentKind.MISSION_COMPLETE,
            ActivityDomain.MISSIONS,
            11,
            credits=15000,
        ),
        _moment(MomentKind.ENGINEER_CRAFT, ActivityDomain.ENGINEERING, 12),
        _moment(MomentKind.CARRIER_JUMP, ActivityDomain.CARRIER, 13),
        _moment(MomentKind.EXOBIO_SAMPLE, ActivityDomain.EXOBIOLOGY, 14),
        _moment(
            MomentKind.EXOBIO_SELL,
            ActivityDomain.EXOBIOLOGY,
            15,
            credits=9000,
        ),
        _moment(
            MomentKind.SRV_DEPLOY,
            ActivityDomain.SRV,
            16,
            mode=ActivityMode.SRV,
        ),
        _moment(
            MomentKind.DISEMBARK,
            ActivityDomain.ON_FOOT,
            17,
            mode=ActivityMode.ON_FOOT,
        ),
        _moment(
            MomentKind.SETTLEMENT_VISIT,
            ActivityDomain.ON_FOOT,
            18,
            mode=ActivityMode.ON_FOOT,
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    activity = debrief.activity

    assert activity.flight.jumps == 2
    assert activity.flight.distance_ly == 20
    assert activity.exploration.bodies_scanned == 1
    assert activity.exploration.bodies_mapped == 1
    assert activity.exploration.honks == 1
    assert activity.exploration.data_sold.value == 30000
    assert activity.combat.kills == 2
    assert activity.combat.bounties.value == 50000
    assert activity.combat.bonds.value == 20000
    assert activity.trade.buys == 1
    assert activity.trade.sells == 1
    assert activity.trade.spent.value == 1000
    assert activity.trade.earned.value == 4000
    assert activity.mining.refined == 1
    assert activity.missions.completed == 1
    assert activity.missions.rewards.value == 15000
    assert activity.engineering.crafted == 1
    assert activity.carrier.jumps == 1
    assert activity.exobiology.samples == 1
    assert activity.exobiology.sold.value == 9000
    assert activity.srv.deployments == 1
    assert activity.on_foot.disembarks == 1
    assert activity.on_foot.settlements == 1

    assert activity.active_domains == (
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
    assert activity.modes_used == (
        ActivityMode.SHIP,
        ActivityMode.SRV,
        ActivityMode.ON_FOOT,
    )
    expected_net = 30000 + 50000 + 20000 + 1000 + 4000 + 15000 + 9000
    assert debrief.net_credits_delta.value == expected_net


def test_partial_session_leaves_unused_rollups_none() -> None:
    moments = (_moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 0, magnitude=5),)
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    activity = debrief.activity
    assert activity.flight is not None
    assert activity.exploration is None
    assert activity.combat is None
    assert activity.trade is None
    assert activity.mining is None
    assert activity.missions is None
    assert activity.engineering is None
    assert activity.carrier is None
    assert activity.exobiology is None
    assert activity.srv is None
    assert activity.on_foot is None
    assert activity.active_domains == (ActivityDomain.TRAVEL,)


def test_start_and_end_systems_from_first_and_last_located_moments() -> None:
    moments = (
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            0,
            detail=((STAR_SYSTEM_FIELD, "Sol"),),
        ),
        _moment(MomentKind.SCAN_BODY, ActivityDomain.EXPLORATION, 1),
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            2,
            detail=((STAR_SYSTEM_FIELD, "Lave"),),
        ),
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            3,
            detail=((STAR_SYSTEM_FIELD, "Diso"),),
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert str(debrief.start_system) == "Sol"
    assert str(debrief.end_system) == "Diso"


def test_system_field_non_string_is_ignored() -> None:
    moments = (
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            0,
            detail=((STAR_SYSTEM_FIELD, 1234),),
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert debrief.start_system is None
    assert debrief.end_system is None


def test_system_field_empty_string_is_ignored() -> None:
    moments = (
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            0,
            detail=((STAR_SYSTEM_FIELD, "   "),),
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert debrief.start_system is None


def test_moment_detail_without_system_field_is_ignored() -> None:
    moments = (
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            0,
            detail=(("Other", "value"),),
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert debrief.start_system is None


def test_single_located_moment_is_both_start_and_end() -> None:
    moments = (
        _moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            0,
            detail=((STAR_SYSTEM_FIELD, "Sol"),),
        ),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert str(debrief.start_system) == "Sol"
    assert str(debrief.end_system) == "Sol"
