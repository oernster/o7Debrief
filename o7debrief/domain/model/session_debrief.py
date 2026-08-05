"""SessionDebrief: the assembled, ordered summary of one play session.

This is the domain's top-level output: who played, the session window,
the systems they started and ended in, their net credit change, every
conceptual moment (kept in chronological order), the activity rollups and
any rank progression. The ordering invariant is enforced here so no
consumer ever has to re-sort.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.session_window import SessionWindow
from o7debrief.domain.value_objects.system_name import SystemName

__all__ = ["SessionDebrief"]


@dataclass(frozen=True, slots=True)
class SessionDebrief:
    """The complete debrief for a single isolated play session."""

    commander: CommanderId
    window: SessionWindow
    start_system: SystemName | None
    end_system: SystemName | None
    net_credits_delta: Credits
    moments: tuple[ConceptualMoment, ...]
    activity: ActivityRollup
    rank_progression: tuple[RankDelta, ...]
    config_schema_version: str
    ship: str = ""
    ship_name: str = ""
    # The commander's credit balance as actually read from the journal, else None
    # when the session carried no reading. A level, not a delta: it answers
    # "how much do I have" where net_credits_delta answers "what changed". None
    # is deliberately not zero, because a report that cannot tell an absent
    # reading from a balance of nothing is the defect this field exists to fix.
    credits_balance: Credits | None = None
    # How many distinct systems the session named, else None when it named
    # none at all and no history stated one either. None is deliberately not
    # zero: a commander is always somewhere, so a count of no systems is never
    # a true reading, only an admission that nothing was recorded.
    systems_visited: int | None = None

    def __post_init__(self) -> None:
        previous: float | None = None
        for moment in self.moments:
            current = moment.occurred_at.epoch_s
            if previous is not None and current < previous:
                raise AggregationError(
                    "Moments must be sorted non-decreasing by occurred_at."
                )
            previous = current
