"""Tests for the beat factory."""

from __future__ import annotations

from o7debrief.domain.aggregation.beat_factory import build_beats
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import BeatRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
)
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int, fields: tuple = ()) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), fields)


def _spec(rules: tuple[BeatRule, ...], labels: tuple = ()) -> RollupSpec:
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


_JUMP_RULE = BeatRule(
    event_type="FSDJump",
    kind=BeatKind.JUMP,
    domain=ActivityDomain.TRAVEL,
    mode=ActivityMode.SHIP,
    magnitude_field="JumpDist",
    credits_field=None,
)
_BOUNTY_RULE = BeatRule(
    event_type="Bounty",
    kind=BeatKind.BOUNTY,
    domain=ActivityDomain.COMBAT,
    mode=ActivityMode.SHIP,
    magnitude_field=None,
    credits_field="Reward",
)
_EXOBIO_SELL_RULE = BeatRule(
    event_type="SellOrganicData",
    kind=BeatKind.EXOBIO_SELL,
    domain=ActivityDomain.EXOBIOLOGY,
    mode=ActivityMode.ON_FOOT,
    magnitude_field=None,
    credits_field=None,
    credits_array_field="BioData",
    credits_item_fields=("Value", "Bonus"),
)


def test_event_without_matching_rule_is_skipped() -> None:
    spec = _spec((_JUMP_RULE,))
    beats = build_beats((_ev("Unmapped", 0),), spec)
    assert beats == ()


def test_matching_event_becomes_beat_with_configured_label() -> None:
    spec = _spec((_JUMP_RULE,), (("FSDJump", "Hyperspace jump"),))
    beats = build_beats((_ev("FSDJump", 0, (("JumpDist", 12),)),), spec)
    assert len(beats) == 1
    assert beats[0].kind is BeatKind.JUMP
    assert beats[0].label == "Hyperspace jump"
    assert beats[0].magnitude == 12
    assert beats[0].credits_delta.value == 0
    assert beats[0].occurred_at.iso_utc == "2024-01-01T10:00:00Z"
    assert beats[0].detail == (("JumpDist", 12),)


def test_label_falls_back_to_event_type_when_unlabelled() -> None:
    spec = _spec((_JUMP_RULE,))
    beats = build_beats((_ev("FSDJump", 0, (("JumpDist", 5),)),), spec)
    assert beats[0].label == "FSDJump"


def test_magnitude_field_none_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    beats = build_beats((_ev("Bounty", 0, (("Reward", 5000),)),), spec)
    assert beats[0].magnitude == 0


def test_magnitude_field_absent_yields_zero() -> None:
    spec = _spec((_JUMP_RULE,))
    beats = build_beats((_ev("FSDJump", 0, ()),), spec)
    assert beats[0].magnitude == 0


def test_magnitude_field_non_int_yields_zero() -> None:
    spec = _spec((_JUMP_RULE,))
    beats = build_beats((_ev("FSDJump", 0, (("JumpDist", "far"),)),), spec)
    assert beats[0].magnitude == 0


def test_magnitude_field_bool_is_rejected_as_zero() -> None:
    # bool is an int subclass; it must NOT be treated as a magnitude.
    spec = _spec((_JUMP_RULE,))
    beats = build_beats((_ev("FSDJump", 0, (("JumpDist", True),)),), spec)
    assert beats[0].magnitude == 0


def test_credits_field_reads_value() -> None:
    spec = _spec((_BOUNTY_RULE,))
    beats = build_beats((_ev("Bounty", 0, (("Reward", 75000),)),), spec)
    assert beats[0].credits_delta == Credits(75000)


def test_credits_field_absent_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    beats = build_beats((_ev("Bounty", 0, ()),), spec)
    assert beats[0].credits_delta.value == 0


def test_credits_field_non_int_yields_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    beats = build_beats((_ev("Bounty", 0, (("Reward", "lots"),)),), spec)
    assert beats[0].credits_delta.value == 0


def test_credits_field_bool_is_rejected_as_zero() -> None:
    spec = _spec((_BOUNTY_RULE,))
    beats = build_beats((_ev("Bounty", 0, (("Reward", True),)),), spec)
    assert beats[0].credits_delta.value == 0


def test_mode_is_taken_from_phase_tracker() -> None:
    # After LaunchSRV the bounty beat should be tagged SRV mode.
    launch_rule = BeatRule(
        event_type="LaunchSRV",
        kind=BeatKind.SRV_DEPLOY,
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
    beats = build_beats(events, spec)
    assert beats[0].mode is ActivityMode.SRV
    assert beats[1].mode is ActivityMode.SRV


def test_credits_array_sums_item_fields_across_entries() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    bio = [{"Value": 100, "Bonus": 50}, {"Value": 200, "Bonus": 0}]
    beats = build_beats((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert beats[0].credits_delta == Credits(350)


def test_credits_array_absent_yields_zero() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    beats = build_beats((_ev("SellOrganicData", 0, ()),), spec)
    assert beats[0].credits_delta.value == 0


def test_credits_array_non_list_yields_zero() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    beats = build_beats((_ev("SellOrganicData", 0, (("BioData", "nope"),)),), spec)
    assert beats[0].credits_delta.value == 0


def test_credits_array_skips_non_dict_entries() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    bio = [{"Value": 100, "Bonus": 0}, "junk", 42]
    beats = build_beats((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert beats[0].credits_delta == Credits(100)


def test_credits_array_ignores_non_int_and_bool_items() -> None:
    spec = _spec((_EXOBIO_SELL_RULE,))
    # True is a bool (an int subclass) and "x" is a string: both rejected. The
    # second entry's Bonus is absent, so only its Value of 100 contributes.
    bio = [{"Value": True, "Bonus": "x"}, {"Value": 100}]
    beats = build_beats((_ev("SellOrganicData", 0, (("BioData", bio),)),), spec)
    assert beats[0].credits_delta == Credits(100)
