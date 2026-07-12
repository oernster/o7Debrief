"""ConceptualMoment: one meaningful, classified moment within a session.

A moment is the unit the debrief is built from. It abstracts away from the
raw journal event into a domain-classified happening: its kind, the domain
and mode it belongs to, when it occurred, a human label, a magnitude, any
credit delta and a tuple of supporting detail pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from o7debrief.domain.errors import InvalidRawEventError
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime

__all__ = ["ConceptualMoment"]


@dataclass(frozen=True, slots=True)
class ConceptualMoment:
    """A single classified happening that contributes to the debrief."""

    kind: MomentKind
    domain: ActivityDomain
    mode: ActivityMode
    occurred_at: EventTime
    label: str
    magnitude: int
    credits_delta: Credits
    detail: tuple[tuple[str, object], ...]
    # A second, distinct currency delta (Operations pay Merc Coins). It rides
    # its own channel so it never folds into the session net-credits figure,
    # and defaults to zero for the many moments that carry no coin reward.
    coins_delta: Credits = field(default_factory=Credits.zero)

    def __post_init__(self) -> None:
        if not self.label:
            raise InvalidRawEventError("Moment label must not be empty.")
