"""Tests for the moment factory's where-filters, which pick between rules.

One journal event can mean several different things. A ``ModuleBuy`` is a
Vessel Hangar purchase or an ordinary outfitting purchase; a ``LaunchFighter``
is a Nomad deployment or a genuine fighter; an ``EngineerCraft`` is an
experimental effect being applied or a grade being rolled. The taxonomy tells
them apart with a filter on the payload. The first rule whose filter passes
wins, so declaration order decides precedence.

Split out of the moment-factory tests as its own subject.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.moment_factory import build_moments
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


def _spec(rules: tuple[MomentRule, ...], labels: tuple = ()) -> RollupSpec:
    return RollupSpec(
        schema_version="1.0.0",
        rules=rules,
        thresholds=ThresholdSet(
            long_jump_ly=20.0,
            big_payout_credits=1000000,
            high_value_exobio_credits=5000000,
        ),
        labels=labels,
    )


_HANGAR_BUY_RULE = MomentRule(
    event_type="ModuleBuy",
    kind=MomentKind.VESSEL_HANGAR_BUY,
    domain=ActivityDomain.SLV,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
    where_field="BuyItem",
    where_contains=("fighterbay",),
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


def test_where_filter_matches_when_field_contains_token() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    # The Mk II Vessel Hangar is the Int_FighterBayMk2 module internally.
    item = "$int_fighterbaymk2_size5_class1_name;"
    moments = build_moments((_ev("ModuleBuy", 0, (("BuyItem", item),)),), spec)
    assert len(moments) == 1
    assert moments[0].kind is MomentKind.VESSEL_HANGAR_BUY


def test_where_filter_is_case_insensitive() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    moments = build_moments(
        (_ev("ModuleBuy", 0, (("BuyItem", "Int_FighterBay"),)),), spec
    )
    assert len(moments) == 1


def test_where_filter_rejects_when_token_absent() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    moments = build_moments(
        (_ev("ModuleBuy", 0, (("BuyItem", "int_hyperdrive"),)),), spec
    )
    assert moments == ()


def test_where_filter_rejects_when_field_missing_or_not_string() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    assert build_moments((_ev("ModuleBuy", 0, ()),), spec) == ()
    assert build_moments((_ev("ModuleBuy", 0, (("BuyItem", 42),)),), spec) == ()


_EXPERIMENTAL_RULE = MomentRule(
    event_type="EngineerCraft",
    kind=MomentKind.ENGINEER_EXPERIMENTAL,
    domain=ActivityDomain.ENGINEERING,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
    where_present="ApplyExperimentalEffect",
)
_CRAFT_RULE = MomentRule(
    event_type="EngineerCraft",
    kind=MomentKind.ENGINEER_CRAFT,
    domain=ActivityDomain.ENGINEERING,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
)


def test_a_present_field_tells_two_rules_on_one_event_apart() -> None:
    """An experimental application and a grade roll are the same event type.

    Both carry the blueprint and grade, so no value distinguishes them. Only
    the event that applies the effect carries ApplyExperimentalEffect.
    """
    spec = _spec((_EXPERIMENTAL_RULE, _CRAFT_RULE))
    applied = _ev(
        "EngineerCraft",
        0,
        (("BlueprintName", "Engine_Dirty"), ("ApplyExperimentalEffect", "special_x")),
    )
    rolled = _ev("EngineerCraft", 1, (("BlueprintName", "Engine_Dirty"),))

    moments = build_moments((applied, rolled), spec)

    assert [moment.kind for moment in moments] == [
        MomentKind.ENGINEER_EXPERIMENTAL,
        MomentKind.ENGINEER_CRAFT,
    ]


def test_a_restated_effect_is_not_a_fresh_application() -> None:
    """Every roll after an effect is attached restates ExperimentalEffect.

    Matching on that field would have counted each of those rolls as another
    experimental, so the rule reads the applying field instead.
    """
    spec = _spec((_EXPERIMENTAL_RULE, _CRAFT_RULE))
    rolled = _ev(
        "EngineerCraft",
        0,
        (("ExperimentalEffect", "special_x"), ("BlueprintName", "Engine_Dirty")),
    )

    moments = build_moments((rolled,), spec)

    assert [moment.kind for moment in moments] == [MomentKind.ENGINEER_CRAFT]


def test_nomad_deploy_matches_any_loadout_variant_and_tags_slv_mode() -> None:
    spec = _spec((_NOMAD_DEPLOY_RULE,))
    for loadout in ("galactic", "stellar", "standard"):
        moments = build_moments(
            (_ev("LaunchFighter", 0, (("Loadout", loadout),)),), spec
        )
        assert len(moments) == 1
        assert moments[0].kind is MomentKind.SLV_DEPLOY
        # The phase tracker, driven by the same rule, tags it as the vessel mode.
        assert moments[0].mode is ActivityMode.SLV


def test_genuine_fighter_launch_is_not_a_nomad_deploy() -> None:
    spec = _spec((_NOMAD_DEPLOY_RULE,))
    moments = build_moments((_ev("LaunchFighter", 0, (("Loadout", "gu97"),)),), spec)
    assert moments == ()
