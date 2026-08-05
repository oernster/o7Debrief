"""RankDelta: the change in a single rank ladder across a session.

Captures both kinds of progress: discrete tier-ups (promotions) and
continuous percentage growth toward the next tier. Every percentage here is
optional, because a session does not always state one: the journal reports a
percentage only in a ``Progress`` event; a session carrying none leaves
the reading unknown rather than zero.

A percentage is a level rather than an event, so it persists. ``progress_pct``
is that level: the reading this period stated, else the last known one carried
forward. ``growth_pct`` is the movement between two readings and exists only
when both are known.
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
    start_pct: int | None
    end_pct: int | None
    growth_pct: int | None
    tier_ups: int

    def __post_init__(self) -> None:
        if self.to_tier < self.from_tier:
            raise AggregationError("Rank delta to_tier must not be below from_tier.")

    @property
    def progress_pct(self) -> int | None:
        """Return the percentage in force, else None when none is known.

        A period that stated a reading reports it. One that stated none leaves
        the last known reading valid, so it is carried forward. A promotion is
        the exception: the carried reading was earned in the tier just left, so
        against the new tier it would be a fabrication and the level stays
        unknown until the game states one.
        """
        if self.end_pct is not None:
            return self.end_pct
        if self.promoted:
            return None
        return self.start_pct
