"""SessionRecorder: hold and poll the current play-session recording state.

The recorder tails the journal through the ``JournalSource`` port. It keeps
the events seen so far for the latest session and a read offset so each
poll picks up only what was appended since the last one. A small status
snapshot reports whether anything has been recorded and how much.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from o7debrief.domain.aggregation.session_bracketer import latest_session

if TYPE_CHECKING:
    from o7debrief.application.ports.journal_source import JournalSource
    from o7debrief.domain.model.raw_event import RawEvent

__all__ = ["SessionStatus", "SessionRecorder"]

# Starting read offset before any incremental poll has happened.
_START_OFFSET = 0
# Headline text shown depending on whether any events have been recorded.
_IDLE_HEADLINE = "No session recorded yet."
_RECORDING_HEADLINE = "Recording session: {count} events."


@dataclass(frozen=True, slots=True)
class SessionStatus:
    """A snapshot of the recorder's state for display."""

    is_recording: bool
    event_count: int
    headline: str


class SessionRecorder:
    """Tails the journal and tracks the latest session's events."""

    def __init__(self, journal_source: JournalSource) -> None:
        self._journal_source = journal_source
        self._events: tuple[RawEvent, ...] = ()
        self._offset = _START_OFFSET

    def latest_session_events(self) -> tuple[RawEvent, ...]:
        """Return the most recent session's events, refreshed from source."""
        self._events = self._journal_source.read_latest_session()
        return self._events

    def poll(self) -> tuple[RawEvent, ...]:
        """Append newly written events, trim to the current session, return it.

        Uses the source's incremental read so each poll only fetches what was
        appended since the last one, then keeps only the latest session's
        events. Trimming on every poll bounds the recorder to a single session
        for the life of the always-on tray app: without it the held events
        would grow without limit, accumulating every event across every session
        and journal-file rotation until the app was restarted.
        """
        new_events, new_offset = self._journal_source.read_new(self._offset)
        self._offset = new_offset
        self._events = latest_session(self._events + new_events)
        return self._events

    def status(self) -> SessionStatus:
        """Return a snapshot describing the current recording state."""
        count = len(self._events)
        is_recording = count > _START_OFFSET
        if is_recording:
            headline = _RECORDING_HEADLINE.format(count=count)
        else:
            headline = _IDLE_HEADLINE
        return SessionStatus(
            is_recording=is_recording,
            event_count=count,
            headline=headline,
        )
