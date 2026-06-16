"""Rank progression: compute per-ladder rank deltas for a session.

The full standing is reported: one delta per ladder that has a current tier,
comparing the opening tier (from the saved snapshot) with the current one
(from the journal's ``Rank`` event, raised by any ``Promotion``). A ladder
whose tier rose is promoted; one that held steady is reported unchanged so the
report can still show it.

A promoted ladder crosses a tier boundary, so its end percentage belongs
to the new tier and a raw end-minus-start delta would be meaningless. We
therefore leave ``growth_pct`` as ``None`` for promoted ladders and only
compute it for ladders whose tier held steady.
"""

from __future__ import annotations

from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.value_objects.enums import RankLadder

__all__ = ["compute_rank_deltas"]

# Default percentage when a ladder is absent from a snapshot.
_DEFAULT_PCT = 0
# Number of tier-ups for a ladder that was not promoted.
_NO_TIER_UPS = 0


def _value_for(
    pairs: tuple[tuple[RankLadder, int], ...],
    ladder: RankLadder,
    default: int,
) -> int:
    """Return the integer paired with ``ladder``, or ``default``."""
    for key, value in pairs:
        if key == ladder:
            return value
    return default


def _delta_for(
    ladder: RankLadder,
    to_tier: int,
    start_tiers: tuple[tuple[RankLadder, int], ...],
    start_pcts: tuple[tuple[RankLadder, int], ...],
    end_pcts: tuple[tuple[RankLadder, int], ...] | None,
) -> RankDelta:
    """Build the RankDelta for a single ladder at its current tier.

    The opening tier comes from the saved snapshot; when the ladder is absent
    from it (a first run, or a ladder never recorded before) the opening tier
    defaults to the current one, so the ladder reads as unchanged rather than
    as a spurious promotion from zero.
    """
    from_tier = _value_for(start_tiers, ladder, to_tier)
    promoted = to_tier > from_tier
    start_pct = _value_for(start_pcts, ladder, _DEFAULT_PCT)
    end_pct = (
        _value_for(end_pcts, ladder, _DEFAULT_PCT) if end_pcts is not None else None
    )
    tier_ups = to_tier - from_tier if promoted else _NO_TIER_UPS
    if promoted:
        growth_pct = None
    elif end_pct is not None:
        growth_pct = end_pct - start_pct
    else:
        growth_pct = None
    return RankDelta(
        ladder=ladder,
        from_tier=from_tier,
        to_tier=to_tier,
        promoted=promoted,
        start_pct=start_pct,
        end_pct=end_pct,
        growth_pct=growth_pct,
        tier_ups=tier_ups,
    )


def compute_rank_deltas(
    start_tiers: tuple[tuple[RankLadder, int], ...],
    start_pcts: tuple[tuple[RankLadder, int], ...],
    end_tiers: tuple[tuple[RankLadder, int], ...],
    end_pcts: tuple[tuple[RankLadder, int], ...] | None,
) -> tuple[RankDelta, ...]:
    """Return a RankDelta for every ladder with a current tier.

    The full standing is reported, in the order ``end_tiers`` supplies, so the
    report can show every ladder. A ladder whose current tier exceeds its
    opening tier is promoted; one that holds steady is reported unchanged.
    """
    return tuple(
        _delta_for(ladder, to_tier, start_tiers, start_pcts, end_pcts)
        for ladder, to_tier in end_tiers
    )
