"""Tests for rank-progression delta computation (full standing)."""

from __future__ import annotations

from o7debrief.domain.aggregation.rank_progression import compute_rank_deltas
from o7debrief.domain.value_objects.enums import RankLadder


def test_no_current_tiers_returns_empty() -> None:
    # With no current tiers there is no standing to report.
    assert compute_rank_deltas((), (), (), None) == ()


def test_steady_ladder_without_snapshot_reads_as_unchanged() -> None:
    # No snapshot: the opening tier defaults to the current one, so a ladder
    # at King reads as unchanged rather than a promotion from zero.
    result = compute_rank_deltas(
        start_tiers=(),
        start_pcts=(),
        end_tiers=((RankLadder.EMPIRE, 14),),
        end_pcts=None,
    )
    assert len(result) == 1
    delta = result[0]
    assert delta.ladder is RankLadder.EMPIRE
    assert delta.from_tier == 14
    assert delta.to_tier == 14
    assert delta.promoted is False
    assert delta.tier_ups == 0


def test_current_tier_above_snapshot_is_a_promotion() -> None:
    result = compute_rank_deltas(
        start_tiers=((RankLadder.COMBAT, 2),),
        start_pcts=((RankLadder.COMBAT, 90),),
        end_tiers=((RankLadder.COMBAT, 4),),
        end_pcts=((RankLadder.COMBAT, 10),),
    )
    delta = result[0]
    assert delta.promoted is True
    assert delta.from_tier == 2
    assert delta.to_tier == 4
    assert delta.tier_ups == 2
    # A promoted ladder crosses a tier boundary, so growth stays None.
    assert delta.end_pct == 10
    assert delta.growth_pct is None


def test_steady_tier_computes_percentage_growth() -> None:
    result = compute_rank_deltas(
        start_tiers=((RankLadder.TRADE, 3),),
        start_pcts=((RankLadder.TRADE, 10),),
        end_tiers=((RankLadder.TRADE, 3),),
        end_pcts=((RankLadder.TRADE, 45),),
    )
    delta = result[0]
    assert delta.promoted is False
    assert delta.from_tier == 3
    assert delta.to_tier == 3
    assert delta.start_pct == 10
    assert delta.end_pct == 45
    assert delta.growth_pct == 35


def test_steady_tier_without_end_pcts_leaves_growth_none() -> None:
    result = compute_rank_deltas(
        start_tiers=((RankLadder.TRADE, 3),),
        start_pcts=((RankLadder.TRADE, 10),),
        end_tiers=((RankLadder.TRADE, 3),),
        end_pcts=None,
    )
    delta = result[0]
    assert delta.promoted is False
    assert delta.end_pct is None
    assert delta.growth_pct is None


def test_full_standing_reports_every_ladder_in_order() -> None:
    result = compute_rank_deltas(
        start_tiers=((RankLadder.COMBAT, 1),),
        start_pcts=(),
        end_tiers=(
            (RankLadder.COMBAT, 2),
            (RankLadder.EMPIRE, 14),
            (RankLadder.FEDERATION, 14),
        ),
        end_pcts=None,
    )
    assert [d.ladder for d in result] == [
        RankLadder.COMBAT,
        RankLadder.EMPIRE,
        RankLadder.FEDERATION,
    ]
    by_ladder = {d.ladder: d for d in result}
    # Combat rose from the snapshot; the navy ranks have no snapshot baseline.
    assert by_ladder[RankLadder.COMBAT].promoted is True
    assert by_ladder[RankLadder.EMPIRE].promoted is False
    assert by_ladder[RankLadder.EMPIRE].to_tier == 14
