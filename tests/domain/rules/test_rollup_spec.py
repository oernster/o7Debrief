"""Tests for the RollupSpec data-only specification."""

from __future__ import annotations

from o7debrief.domain.rules.rollup_spec import BeatRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
)


def _spec() -> RollupSpec:
    return RollupSpec(
        schema_version="2.0.0",
        rules=(
            BeatRule(
                event_type="FSDJump",
                kind=BeatKind.JUMP,
                domain=ActivityDomain.TRAVEL,
                mode=ActivityMode.SHIP,
                magnitude_field="JumpDist",
                credits_field=None,
            ),
            BeatRule(
                event_type="Bounty",
                kind=BeatKind.BOUNTY,
                domain=ActivityDomain.COMBAT,
                mode=ActivityMode.SHIP,
                magnitude_field=None,
                credits_field="Reward",
            ),
        ),
        thresholds=ThresholdSet(
            long_jump_ly=20.0,
            big_payout_credits=1000000,
            high_value_exobio_credits=5000000,
        ),
        labels=(("FSDJump", "Hyperspace jump"),),
    )


def test_rule_for_hit() -> None:
    rule = _spec().rule_for("Bounty")
    assert rule is not None
    assert rule.kind is BeatKind.BOUNTY


def test_rule_for_miss_returns_none() -> None:
    assert _spec().rule_for("Unknown") is None


def test_label_for_hit() -> None:
    assert _spec().label_for("FSDJump", "default") == "Hyperspace jump"


def test_label_for_miss_returns_default() -> None:
    assert _spec().label_for("Nope", "default") == "default"


def test_threshold_values_exposed() -> None:
    thresholds = _spec().thresholds
    assert thresholds.long_jump_ly == 20.0
    assert thresholds.big_payout_credits == 1000000
    assert thresholds.high_value_exobio_credits == 5000000
