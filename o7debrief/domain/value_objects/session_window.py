"""SessionWindow value object: the time span of a single play session."""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import InvalidSessionWindowError
from o7debrief.domain.value_objects.event_time import EventTime

__all__ = ["SessionWindow"]


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """The bounded interval of a session, with a clean-shutdown flag."""

    start: EventTime
    end: EventTime
    clean_shutdown: bool

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvalidSessionWindowError(
                "Session end must not precede session start."
            )

    @property
    def duration_s(self) -> float:
        """Length of the session in seconds (always non-negative)."""
        return self.end.epoch_s - self.start.epoch_s
