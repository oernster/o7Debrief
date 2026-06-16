"""Tests for the RankDelta model."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.value_objects.enums import RankLadder


def test_valid_tier_up() -> None:
    delta = RankDelta(
        ladder=RankLadder.COMBAT,
        from_tier=2,
        to_tier=4,
        promoted=True,
        start_pct=50,
        end_pct=10,
        growth_pct=None,
        tier_ups=2,
    )
    assert delta.tier_ups == 2
    assert delta.promoted is True


def test_equal_tiers_allowed() -> None:
    delta = RankDelta(
        ladder=RankLadder.TRADE,
        from_tier=3,
        to_tier=3,
        promoted=False,
        start_pct=10,
        end_pct=40,
        growth_pct=30,
        tier_ups=0,
    )
    assert delta.from_tier == delta.to_tier


def test_to_tier_below_from_tier_raises() -> None:
    with pytest.raises(AggregationError):
        RankDelta(
            ladder=RankLadder.EXPLORE,
            from_tier=5,
            to_tier=4,
            promoted=False,
            start_pct=0,
            end_pct=None,
            growth_pct=None,
            tier_ups=0,
        )
