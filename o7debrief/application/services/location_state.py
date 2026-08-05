"""Where the commander was, tracked across a set of journal events.

The star system is a level rather than an event: it holds until something
moves the commander, so the system in force is whatever the latest event
naming one stated. Reading it from the events rather than from the derived
moments matters, because most location-bearing events produce no moment at
all: a session can name four systems and still contribute none to the
timeline, which is how a report came to state "Unknown" for a commander who
was plainly somewhere.

Any event carrying a non-blank ``StarSystem`` is a reading, so no whitelist of
event types has to be kept in step with the game. One exception is excluded by
name: ``CarrierLocation`` states where a fleet carrier is, which is not where
the commander is.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.model.raw_event import RawEvent

__all__ = ["LocationHistory", "extended", "location_history"]

# The journal's own field naming the star system an event occurred in.
_STAR_SYSTEM_FIELD = "StarSystem"

# Events whose StarSystem is not the commander's own position.
_NOT_THE_COMMANDER = ("CarrierLocation",)


@dataclass(frozen=True, slots=True)
class LocationHistory:
    """The systems named across a set of events, in the order they appeared."""

    systems: tuple[str, ...] = ()

    def endpoints(self) -> tuple[str, str] | None:
        """Return the first and last systems named, else None when none was."""
        if not self.systems:
            return None
        return self.systems[0], self.systems[-1]

    def latest(self) -> str | None:
        """Return the last system named, else None when none was."""
        if not self.systems:
            return None
        return self.systems[-1]

    def distinct_count(self) -> int:
        """Return how many distinct systems were named."""
        return len(set(self.systems))


def extended(history: LocationHistory, events: tuple[RawEvent, ...]) -> LocationHistory:
    """Return ``history`` with the readings in ``events`` folded onto its end.

    Streaming the whole journal one file at a time can fold each batch on in
    turn, so the history stays bounded by the systems actually visited rather
    than by the number of events that mention one.

    Consecutive readings of the same system collapse to one entry, so a
    session spent docked in one place records a single visit rather than one
    per market screen opened.
    """
    systems: list[str] = list(history.systems)
    for event in events:
        if event.event_type in _NOT_THE_COMMANDER:
            continue
        value = event.get(_STAR_SYSTEM_FIELD)
        if not (isinstance(value, str) and value.strip()):
            continue
        if not systems or systems[-1] != value:
            systems.append(value)
    return LocationHistory(systems=tuple(systems))


def location_history(events: tuple[RawEvent, ...]) -> LocationHistory:
    """Fold every system reading in ``events`` into a fresh history, in order."""
    return extended(LocationHistory(systems=()), events)
