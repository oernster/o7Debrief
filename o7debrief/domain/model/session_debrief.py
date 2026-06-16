"""SessionDebrief: the assembled, ordered summary of one play session.

This is the domain's top-level output: who played, the session window,
the systems they started and ended in, their net credit change, every
conceptual beat (kept in chronological order), the activity rollups and
any rank progression. The ordering invariant is enforced here so no
consumer ever has to re-sort.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.conceptual_beat import ConceptualBeat
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
    beats: tuple[ConceptualBeat, ...]
    activity: ActivityRollup
    rank_progression: tuple[RankDelta, ...]
    config_schema_version: str
    ship: str = ""
    ship_name: str = ""

    def __post_init__(self) -> None:
        previous: float | None = None
        for beat in self.beats:
            current = beat.occurred_at.epoch_s
            if previous is not None and current < previous:
                raise AggregationError(
                    "Beats must be sorted non-decreasing by occurred_at."
                )
            previous = current
