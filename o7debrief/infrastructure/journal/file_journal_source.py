"""FileJournalSource: the concrete ``JournalSource`` over real journal files.

This adapter ties the journal building blocks together. ``read_all`` parses
every ``Journal.*.log`` file in the directory into domain ``RawEvent`` tuples in
time order. ``read_latest_session`` then delegates to the domain's
``session_bracketer.latest_session`` so the session-isolation guarantee runs end
to end: parse, map, then slice to the most recent session only.
``read_new`` performs an incremental tail read of the latest file using the
byte-offset reader, so a long-running caller resumes exactly where it left off.

The adapter only ever reads the journal; it never writes it (single-writer is
Elite Dangerous, multi-reader is us).

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.domain.aggregation.session_bracketer import latest_session
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

    def read_all(self) -> tuple[RawEvent, ...]:
        """Return every event across all journal files, in time order."""
        events: list[RawEvent] = []
        for path in self._all_files():
            records = parse_file(path)
            events.extend(map_records(records))
        events.sort(key=_by_time)
        return tuple(events)

    def read_latest_session(self) -> tuple[RawEvent, ...]:
        """Return only the events of the most recent play session.

        Delegates to the domain bracketer so the file format never leaks into
        the isolation rule: parse and map here, slice in the domain.
        """
        return latest_session(self.read_all())

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
