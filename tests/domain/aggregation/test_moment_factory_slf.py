"""Tests for ship-launched-fighter moments in the factory.

Fighters share ``LaunchFighter`` with the Nomad, so the factory must try the
Nomad rule first and fall through to the fighter rule. The fighter type is named
from the launch loadout; a dock or loss carries only an ID and recovers the
loadout by matching it against the launch.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.moment_factory import (
    VESSEL_TYPE_MARK,
    build_moments,
)
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import MomentRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int, fields: tuple = ()) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), fields)


def _spec(rules: tuple[MomentRule, ...]) -> RollupSpec:
    return RollupSpec(
        schema_version="1.0.0",
        rules=rules,
        thresholds=ThresholdSet(
            long_jump_ly=20.0,
            big_payout_credits=1000000,
            high_value_exobio_credits=5000000,
        ),
        labels=(),
    )


_NOMAD_DEPLOY_RULE = MomentRule(
    event_type="LaunchFighter",
    kind=MomentKind.SLV_DEPLOY,
    domain=ActivityDomain.SLV,
    mode=ActivityMode.SLV,
    magnitude_field=None,
    credits_field=None,
    where_field="Loadout",
    where_contains=("galactic", "stellar", "standard"),
)
_SLF_DEPLOY_RULE = MomentRule(
    event_type="LaunchFighter",
    kind=MomentKind.SLF_DEPLOY,
    domain=ActivityDomain.SLF,
    mode=ActivityMode.SLF,
    magnitude_field=None,
    credits_field=None,
)
_SLF_DOCK_RULE = MomentRule(
    event_type="DockFighter",
    kind=MomentKind.SLF_DOCK,
    domain=ActivityDomain.SLF,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
)
_SLF_DESTROYED_RULE = MomentRule(
    event_type="FighterDestroyed",
    kind=MomentKind.SLF_DESTROYED,
    domain=ActivityDomain.SLF,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
)


def test_launch_fighter_prefers_the_nomad_rule_then_the_fighter_rule() -> None:
    # Order matters: the Nomad rule (filtered) is tried before the fighter rule.
    spec = _spec((_NOMAD_DEPLOY_RULE, _SLF_DEPLOY_RULE))
    nomad = build_moments((_ev("LaunchFighter", 0, (("Loadout", "galactic"),)),), spec)
    assert nomad[0].kind is MomentKind.SLV_DEPLOY
    fighter = build_moments((_ev("LaunchFighter", 0, (("Loadout", "gu97"),)),), spec)
    assert fighter[0].kind is MomentKind.SLF_DEPLOY


def test_fighter_deploy_names_the_type_from_its_loadout() -> None:
    spec = _spec((_NOMAD_DEPLOY_RULE, _SLF_DEPLOY_RULE))
    moments = build_moments(
        (_ev("LaunchFighter", 0, (("Loadout", "gelid"), ("ID", 5))),), spec
    )
    assert dict(moments[0].detail).get(VESSEL_TYPE_MARK) == "Gelid"


def test_fighter_dock_and_loss_recover_the_loadout_by_id() -> None:
    spec = _spec(
        (_NOMAD_DEPLOY_RULE, _SLF_DEPLOY_RULE, _SLF_DOCK_RULE, _SLF_DESTROYED_RULE)
    )
    events = (
        _ev("LaunchFighter", 0, (("Loadout", "taipan"), ("ID", 5))),
        _ev("DockFighter", 1, (("ID", 5),)),
        _ev("LaunchFighter", 2, (("Loadout", "trident"), ("ID", 6))),
        _ev("FighterDestroyed", 3, (("ID", 6),)),
    )
    by_kind = {m.kind: m for m in build_moments(events, spec)}
    assert dict(by_kind[MomentKind.SLF_DOCK].detail).get(VESSEL_TYPE_MARK) == "Taipan"
    lost = dict(by_kind[MomentKind.SLF_DESTROYED].detail)
    assert lost.get(VESSEL_TYPE_MARK) == "Trident"


def test_nomad_launch_is_excluded_from_the_fighter_loadout_map() -> None:
    # A Nomad launch must not name a fighter dock that reuses its ID.
    spec = _spec((_NOMAD_DEPLOY_RULE, _SLF_DOCK_RULE))
    events = (
        _ev("LaunchFighter", 0, (("Loadout", "galactic"), ("ID", 9))),
        _ev("DockFighter", 1, (("ID", 9),)),
    )
    dock = next(
        m for m in build_moments(events, spec) if m.kind is MomentKind.SLF_DOCK
    )
    assert VESSEL_TYPE_MARK not in dict(dock.detail)


def test_fighter_launch_without_a_loadout_is_not_a_nomad_and_is_unnamed() -> None:
    # A LaunchFighter with no Loadout exercises the non-string guard and falls
    # through the Nomad rule to the fighter rule, unnamed.
    spec = _spec((_NOMAD_DEPLOY_RULE, _SLF_DEPLOY_RULE))
    moments = build_moments((_ev("LaunchFighter", 0, (("ID", 1),)),), spec)
    assert moments[0].kind is MomentKind.SLF_DEPLOY
    assert VESSEL_TYPE_MARK not in dict(moments[0].detail)
