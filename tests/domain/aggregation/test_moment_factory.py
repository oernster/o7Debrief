"""Tests for the moment factory."""

from __future__ import annotations

from o7debrief.domain.aggregation.moment_factory import (
    SELF_DESTRUCT_MARK,
    VESSEL_TYPE_MARK,
    build_moments,
)
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import MomentRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.credits import Credits
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


_JUMP_RULE = MomentRule(
    event_type="FSDJump",
    kind=MomentKind.JUMP,
    domain=ActivityDomain.TRAVEL,
    mode=ActivityMode.SHIP,
    magnitude_field="JumpDist",
    credits_field=None,
)
_BOUNTY_RULE = MomentRule(
    event_type="Bounty",
    kind=MomentKind.BOUNTY,
    domain=ActivityDomain.COMBAT,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field="Reward",
)
_EXOBIO_SELL_RULE = MomentRule(
    event_type="SellOrganicData",
    kind=MomentKind.EXOBIO_SELL,
    domain=ActivityDomain.EXOBIOLOGY,
    mode=ActivityMode.ON_FOOT,
    magnitude_field=None,
    credits_field=None,
    credits_array_field="BioData",
    credits_item_fields=("Value", "Bonus"),
)


def test_event_without_matching_rule_is_skipped() -> None:
    spec = _spec((_JUMP_RULE,))
    moments = build_moments((_ev("Unmapped", 0),), spec)
    assert moments == ()


def test_matching_event_becomes_moment_with_configured_label() -> None:
    spec = _spec((_JUMP_RULE,), (("FSDJump", "Hyperspace jump"),))
    moments = build_moments((_ev("FSDJump", 0, (("JumpDist", 12),)),), spec)
    assert len(moments) == 1
    assert moments[0].kind is MomentKind.JUMP
    assert moments[0].label == "Hyperspace jump"
    assert moments[0].magnitude == 12
    assert moments[0].credits_delta.value == 0
    assert moments[0].occurred_at.iso_utc == "2024-01-01T10:00:00Z"
    assert moments[0].detail == (("JumpDist", 12),)


def test_label_falls_back_to_event_type_when_unlabelled() -> None:
    spec = _spec((_JUMP_RULE,))
    moments = build_moments((_ev("FSDJump", 0, (("JumpDist", 5),)),), spec)
    assert moments[0].label == "FSDJump"


def test_magnitude_field_none_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    moments = build_moments((_ev("Bounty", 0, (("Reward", 5000),)),), spec)
    assert moments[0].magnitude == 0


def test_magnitude_field_absent_yields_zero() -> None:
    spec = _spec((_JUMP_RULE,))
    moments = build_moments((_ev("FSDJump", 0, ()),), spec)
    assert moments[0].magnitude == 0


def test_magnitude_field_non_int_yields_zero() -> None:
    spec = _spec((_JUMP_RULE,))
    moments = build_moments((_ev("FSDJump", 0, (("JumpDist", "far"),)),), spec)
    assert moments[0].magnitude == 0


def test_magnitude_field_bool_is_rejected_as_zero() -> None:
    # bool is an int subclass; it must NOT be treated as a magnitude.
    spec = _spec((_JUMP_RULE,))
    moments = build_moments((_ev("FSDJump", 0, (("JumpDist", True),)),), spec)
    assert moments[0].magnitude == 0


def test_credits_field_reads_value() -> None:
    spec = _spec((_BOUNTY_RULE,))
    moments = build_moments((_ev("Bounty", 0, (("Reward", 75000),)),), spec)
    assert moments[0].credits_delta == Credits(75000)


def test_credits_field_absent_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    moments = build_moments((_ev("Bounty", 0, ()),), spec)
    assert moments[0].credits_delta.value == 0


def test_credits_field_non_int_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    moments = build_moments((_ev("Bounty", 0, (("Reward", "lots"),)),), spec)
    assert moments[0].credits_delta.value == 0


def test_credits_field_bool_is_rejected_as_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    moments = build_moments((_ev("Bounty", 0, (("Reward", True),)),), spec)
    assert moments[0].credits_delta.value == 0


def test_mode_is_taken_from_phase_tracker() -> None:
    # After LaunchSRV the bounty moment should be tagged SRV mode.
    launch_rule = MomentRule(
        event_type="LaunchSRV",
        kind=MomentKind.SRV_DEPLOY,
        domain=ActivityDomain.SRV,
        mode=ActivityMode.SRV,
        magnitude_field=None,
        credits_field=None,
    )
    spec = _spec((launch_rule, _BOUNTY_RULE))
    events = (
        _ev("LaunchSRV", 0),
        _ev("Bounty", 1, (("Reward", 1000),)),
    )
    moments = build_moments(events, spec)
    assert moments[0].mode is ActivityMode.SRV
    assert moments[1].mode is ActivityMode.SRV


def test_credits_array_sums_item_fields_across_entries() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    bio = [{"Value": 100, "Bonus": 50}, {"Value": 200, "Bonus": 0}]
    moments = build_moments((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert moments[0].credits_delta == Credits(350)


def test_credits_array_absent_yields_zero() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    moments = build_moments((_ev("SellOrganicData", 0, ()),), spec)
    assert moments[0].credits_delta.value == 0


def test_credits_array_non_list_yields_zero() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    moments = build_moments((_ev("SellOrganicData", 0, (("BioData", "nope"),)),), spec)
    assert moments[0].credits_delta.value == 0


def test_credits_array_skips_non_dict_entries() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    bio = [{"Value": 100, "Bonus": 0}, "junk", 42]
    moments = build_moments((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert moments[0].credits_delta == Credits(100)


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
    moments = build_moments((_ev("ModuleBuy", 0, (("BuyItem", "Int_FighterBay"),)),), spec)
    assert len(moments) == 1


def test_where_filter_rejects_when_token_absent() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    moments = build_moments((_ev("ModuleBuy", 0, (("BuyItem", "int_hyperdrive"),)),), spec)
    assert moments == ()


def test_where_filter_rejects_when_field_missing_or_not_string() -> None:
    spec = _spec((_HANGAR_BUY_RULE,))
    assert build_moments((_ev("ModuleBuy", 0, ()),), spec) == ()
    assert build_moments((_ev("ModuleBuy", 0, (("BuyItem", 42),)),), spec) == ()


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


_SLV_DOCK_RULE = MomentRule(
    event_type="DockSRV",
    kind=MomentKind.SLV_DOCK,
    domain=ActivityDomain.SLV,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
    where_field="SRVType",
    where_contains=("lander",),
)
_DEATH_RULE = MomentRule(
    event_type="Died",
    kind=MomentKind.DEATH,
    domain=ActivityDomain.COMBAT,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
)


_SLV_DESTROYED_RULE = MomentRule(
    event_type="SRVDestroyed",
    kind=MomentKind.SLV_DESTROYED,
    domain=ActivityDomain.SLV,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field=None,
    where_field="SRVType",
    where_contains=("lander",),
)


def test_nomad_dock_is_a_moment_but_the_buggy_dock_is_not() -> None:
    spec = _spec((_SLV_DOCK_RULE,))
    nomad = build_moments((_ev("DockSRV", 0, (("SRVType", "lander01"),)),), spec)
    assert len(nomad) == 1
    assert nomad[0].kind is MomentKind.SLV_DOCK
    buggy = build_moments((_ev("DockSRV", 0, (("SRVType", "scarab"),)),), spec)
    assert buggy == ()


def test_dock_and_loss_name_the_vessel_type_from_the_event() -> None:
    spec = _spec((_SLV_DOCK_RULE, _SLV_DESTROYED_RULE))
    fields = (("SRVType", "lander01"), ("SRVType_Localised", "Nomad"), ("ID", 7))
    dock = build_moments((_ev("DockSRV", 0, fields),), spec)
    assert dict(dock[0].detail).get(VESSEL_TYPE_MARK) == "Nomad"
    lost = build_moments((_ev("SRVDestroyed", 0, fields),), spec)
    assert dict(lost[0].detail).get(VESSEL_TYPE_MARK) == "Nomad"


def test_deploy_recovers_its_vessel_type_by_id_from_the_dock() -> None:
    spec = _spec((_NOMAD_DEPLOY_RULE, _SLV_DOCK_RULE))
    events = (
        _ev("LaunchFighter", 0, (("Loadout", "galactic"), ("ID", 42))),
        _ev(
            "DockSRV",
            1,
            (("SRVType", "lander01"), ("SRVType_Localised", "Nomad"), ("ID", 42)),
        ),
    )
    moments = build_moments(events, spec)
    deploy = next(m for m in moments if m.kind is MomentKind.SLV_DEPLOY)
    assert dict(deploy.detail).get(VESSEL_TYPE_MARK) == "Nomad"


def test_deploy_without_a_matching_dock_has_no_vessel_type() -> None:
    spec = _spec((_NOMAD_DEPLOY_RULE,))
    events = (_ev("LaunchFighter", 0, (("Loadout", "galactic"), ("ID", 42))),)
    moments = build_moments(events, spec)
    assert VESSEL_TYPE_MARK not in dict(moments[0].detail)




def test_self_destruct_marks_the_following_death() -> None:
    spec = _spec((_DEATH_RULE,))
    events = (_ev("SelfDestruct", 0), _ev("Died", 1))
    moments = build_moments(events, spec)
    # SelfDestruct is a signal, not a moment of its own.
    assert len(moments) == 1
    assert moments[0].kind is MomentKind.DEATH
    assert dict(moments[0].detail).get(SELF_DESTRUCT_MARK) is True


def test_death_without_self_destruct_carries_no_marker() -> None:
    spec = _spec((_DEATH_RULE,))
    moments = build_moments((_ev("Died", 0),), spec)
    assert SELF_DESTRUCT_MARK not in dict(moments[0].detail)


def test_self_destruct_without_a_death_produces_no_moment() -> None:
    spec = _spec((_DEATH_RULE,))
    assert build_moments((_ev("SelfDestruct", 0),), spec) == ()


def test_credits_array_ignores_non_int_and_bool_items() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    # True is a bool (an int subclass) and "x" is a string: both rejected. The
    # second entry's Bonus is absent, so only its Value of 100 contributes.
    bio = [{"Value": True, "Bonus": "x"}, {"Value": 100}]
    moments = build_moments((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert moments[0].credits_delta == Credits(100)
