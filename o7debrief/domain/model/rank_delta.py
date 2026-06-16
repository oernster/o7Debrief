"""RankDelta: the change in a single rank ladder across a session.

Captures both kinds of progress: discrete tier-ups (promotions) and
continuous percentage growth toward the next tier. ``end_pct`` and
``growth_pct`` are optional because the closing percentage is not always
known at the moment the delta is computed (it depends on a later event).
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.value_objects.enums import RankLadder

__all__ = ["RankDelta"]


@dataclass(frozen=True, slots=True)
class RankDelta:
    """How one rank ladder moved during the session."""

    ladder: RankLadder
    from_tier: int
    to_tier: int
    promoted: bool
    start_pct: int
    end_pct: int | None
    growth_pct: int | None
    tier_ups: int

    def __post_init__(self) -> None:
        if self.to_tier < self.from_tier:
            raise AggregationError("Rank delta to_tier must not be below from_tier.")
