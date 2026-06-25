"""FileJournalSource: the concrete ``JournalSource`` over real journal files.

This adapter ties the journal building blocks together. ``read_all`` parses
every ``Journal.*.log`` file in the directory into domain ``RawEvent`` tuples in
time order; it backs the explicit all-history debrief alone. The everyday
``read_latest_session`` instead reads the files newest first and stops once it
has seen enough Shutdown events to bound the most recent run, then delegates to
the domain's ``session_bracketer.latest_session`` to slice it, so it never
parses the whole history into memory. ``read_new`` performs an incremental tail
read of the latest file using the byte-offset reader, so a long-running caller
resumes exactly where it left off.

The adapter only ever reads the journal; it never writes it (single-writer is
Elite Dangerous, multi-reader is us).

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from o7debrief.domain.aggregation.session_bracketer import SHUTDOWN, latest_session
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.infrastructure.journal.event_mapper import map_records
from o7debrief.infrastructure.journal.line_parser import parse_file, parse_lines
from o7debrief.infrastructure.journal.paths import (
    get_journal_files,
    get_latest_journal_file,
)
from o7debrief.infrastructure.journal.tail_reader import (
    NO_PARTIAL,
    read_new_bytes,
)

__all__ = ["FileJournalSource"]


# How many Shutdown events the backward scan must see before the latest session
# is fully bounded: one closes the latest run, and the one before it ends the
# previous run and so marks where the latest run began. Reading back only this
# far keeps a last-session debrief to the newest file or two rather than parsing
# the entire journal folder into memory, even when a run is split across a file
# rotation.
_SHUTDOWNS_TO_BOUND_LATEST = 2


# Sort key for ordering events non-decreasing by event-time.
def _by_time(event: RawEvent) -> float:
    """Return an event's epoch seconds, used to order events in time."""
    return event.event_time.epoch_s


class FileJournalSource:
    """A ``JournalSource`` backed by Elite Dangerous journal files on disk.

    The journal directory is injected; the adapter never discovers it on its
    own, so the composition root decides whether to auto-detect or use a
    configured path. A carried-over partial line from an incremental read is
    held on the instance so successive ``read_new`` calls remain correct across
    a line that was still being written.
    """

    def __init__(self, directory: Path | str) -> None:
        self._directory = Path(directory)
        self._partial: bytes = NO_PARTIAL

    def _all_files(self) -> list[Path]:
        """Return every journal file in the directory, oldest to newest."""
        return get_journal_files(self._directory)

    def _events_in_file(self, path: Path) -> tuple[RawEvent, ...]:
        """Parse and map one journal file's events, ordered by event-time."""
        events = list(map_records(parse_file(path)))
        events.sort(key=_by_time)
        return tuple(events)

    def read_all(self) -> tuple[RawEvent, ...]:
        """Return every event across all journal files, in time order.

        Materialises the whole history at once, so it backs only the explicit
        all-history debrief; everyday paths use ``read_latest_session`` or
        ``iter_event_batches`` to stay bounded.
        """
        events: list[RawEvent] = []
        for path in self._all_files():
            events.extend(self._events_in_file(path))
        events.sort(key=_by_time)
        return tuple(events)

    def iter_event_batches(self) -> Iterator[tuple[RawEvent, ...]]:
        """Yield each journal file's events as a batch, oldest file first.

        Lets a caller fold the whole history one file at a time, so the entire
        event history is never resident in memory at once. Each batch is
        ordered by event-time; the caller orders across batches if it needs to.
        """
        for path in self._all_files():
            yield self._events_in_file(path)

    def read_latest_session(self) -> tuple[RawEvent, ...]:
        """Return only the events of the most recent play session.

        Reads back just far enough to bound the latest run (see
        ``_read_back_to_latest_session``), then delegates to the domain
        bracketer so the file format never leaks into the isolation rule:
        parse and map here, slice in the domain. This never parses the whole
        history, so a debrief stays bounded by the size of the current session
        rather than the size of the journal folder.
        """
        return latest_session(self._read_back_to_latest_session())

    def _read_back_to_latest_session(self) -> tuple[RawEvent, ...]:
        """Parse journal files newest first until the latest session is bounded.

        Stops as soon as ``_SHUTDOWNS_TO_BOUND_LATEST`` Shutdown events have been
        seen, or the files run out. That is enough for the bracketer to isolate
        the most recent run even when it is split across a file rotation. The
        accumulated events are returned unsorted; the bracketer orders them.
        """
        collected: list[RawEvent] = []
        shutdowns_seen = 0
        for path in reversed(self._all_files()):
            events = map_records(parse_file(path))
            collected.extend(events)
            shutdowns_seen += sum(1 for event in events if event.event_type == SHUTDOWN)
            if shutdowns_seen >= _SHUTDOWNS_TO_BOUND_LATEST:
                break
        return tuple(collected)

    def read_new(self, since_offset: int) -> tuple[tuple[RawEvent, ...], int]:
        """Return events appended to the latest file since ``since_offset``.

        Uses the incremental tail reader, carrying any trailing partial line on
        the instance so a line read mid-write is completed on the next call.
        Returns the new events and the byte offset to resume from. When there
        is no journal file yet, returns no events and the offset unchanged.
        """
        latest = get_latest_journal_file(self._directory)
        if latest is None:
            return (), since_offset

        result = read_new_bytes(latest, since_offset, self._partial)
        self._partial = result.new_partial
        records = parse_lines(result.complete_lines)
        events = map_records(records)
        return events, result.new_offset
