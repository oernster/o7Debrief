"""RawEvent: a single parsed journal line, decoupled from its JSON form.

The infrastructure layer parses each journal line into a RawEvent: an
event type, its event-time and an ordered tuple of (key, value) fields.
The domain reads fields by key without depending on any JSON library.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import InvalidRawEventError
from o7debrief.domain.value_objects.event_time import EventTime

__all__ = ["RawEvent"]


@dataclass(frozen=True, slots=True)
class RawEvent:
    """One journal event: its type, its event-time and its raw fields."""

    event_type: str
    event_time: EventTime
    fields: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if not self.event_type:
            raise InvalidRawEventError("Event type must not be empty.")

    def get(self, key: str, default: object | None = None) -> object | None:
        """Return the value for ``key`` via a linear scan, else ``default``."""
        for field_key, field_value in self.fields:
            if field_key == key:
                return field_value
        return default
