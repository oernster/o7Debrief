"""JournalSource port: supplies parsed journal events to the application.

The concrete implementation lives in infrastructure and parses the Elite
Dangerous journal files into ``RawEvent`` tuples. The application reads
events only through this port, so it never depends on the file format.
"""

from __future__ import annotations

from typing import Iterator, Protocol

from o7debrief.domain.model.raw_event import RawEvent

__all__ = ["JournalSource"]


class JournalSource(Protocol):
    """A source of parsed journal events."""

    def read_all(self) -> tuple[RawEvent, ...]:
        """Return every event across the whole journal, in time order."""
        ...

    def read_latest_session(self) -> tuple[RawEvent, ...]:
        """Return only the events of the most recent play session."""
        ...

    def read_new(self, since_offset: int) -> tuple[tuple[RawEvent, ...], int]:
        """Return events appended since ``since_offset`` and the new offset.

        The returned offset is passed back on the next call so the source
        can resume from where it left off (a tail-style incremental read).
        """
        ...

    def iter_event_batches(self) -> Iterator[tuple[RawEvent, ...]]:
        """Yield the whole history one file's events at a time, oldest first.

        Lets the application fold an all-history debrief without ever holding
        every event in memory at once.
        """
        ...
