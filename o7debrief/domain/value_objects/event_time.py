"""EventTime value object: an event-time instant parsed from the journal.

This is the single place in the domain permitted to touch ``datetime`` for
parsing the journal "timestamp" string. It NEVER reads the wall clock; it
only converts a recorded event-time string into a comparable instant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from o7debrief.domain.errors import InvalidEventTimeError

__all__ = ["EventTime"]

# Elite Dangerous journal timestamps are UTC and use a trailing "Z" to
# denote Zulu (UTC). ``datetime.fromisoformat`` accepts "+00:00" but not a
# bare "Z" on older parsers, so we normalise it to a numeric offset.
_ZULU_SUFFIX = "Z"
_UTC_OFFSET = "+00:00"


@dataclass(frozen=True, slots=True)
class EventTime:
    """An instant in event-time: the original ISO string plus epoch seconds."""

    iso_utc: str
    epoch_s: float

    def __post_init__(self) -> None:
        if not self.iso_utc:
            raise InvalidEventTimeError("Event time iso_utc must not be empty.")

    @classmethod
    def parse(cls, timestamp: str) -> EventTime:
        """Parse a journal timestamp string into an EventTime.

        Accepts a trailing "Z"; assumes UTC when the parsed value is naive.
        The original string is preserved verbatim as ``iso_utc``.
        """
        if not timestamp:
            raise InvalidEventTimeError("Timestamp must not be empty.")
        normalised = timestamp
        if normalised.endswith(_ZULU_SUFFIX):
            normalised = normalised[: -len(_ZULU_SUFFIX)] + _UTC_OFFSET
        try:
            parsed = datetime.fromisoformat(normalised)
        except ValueError as exc:
            raise InvalidEventTimeError(
                f"Unparseable timestamp: {timestamp!r}"
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return cls(iso_utc=timestamp, epoch_s=parsed.timestamp())

    def __lt__(self, other: EventTime) -> bool:
        return self.epoch_s < other.epoch_s

    def __le__(self, other: EventTime) -> bool:
        return self.epoch_s <= other.epoch_s
