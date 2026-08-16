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
from o7debrief.domain.value_objects.event_time import EventTime
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
    # The signed change in the commander's balance across the session, else
    # None when the journal stated too few balances to measure one. Signed and
    # so not a Credits, which is non-negative by construction: a session that
    # ends poorer than it started is ordinary and must be reportable. None is
    # deliberately not zero, for the same reason credits_balance below is.
    net_credits_delta: int | None
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
    # When ``credits_balance`` was read, else None when there was no reading.
    # The journal states the balance only at a login, never again, so on a long
    # session the level above is the level the commander had when they sat
    # down, not when they got up. The report has to be able to say when it was
    # taken; otherwise a figure hours old reads as the balance now.
    credits_balance_at: EventTime | None = None
    # What the session's priced events came to, income less outgoings. Unlike
    # every level above it this IS folded from the moments, because it is a
    # property of the events rather than a state the journal states. It exists
    # because "change unread" is true and useless: the journal prices a great
    # deal of what a session did even when it never restates the balance. That
    # total is worth having provided it is never mistaken for the change.
    priced_change: int = 0
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
