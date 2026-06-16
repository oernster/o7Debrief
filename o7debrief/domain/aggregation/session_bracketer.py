"""Session isolation: extract the single latest play session from a log.

This is the session-isolation keystone. A journal file can contain many
sessions (the game was started, played, quit, started again). The debrief
must describe ONLY the most recent session, so we slice from the last
``LoadGame`` to the matching ``Shutdown`` (or to the end of the log if the
game crashed without a clean shutdown). Everything before that last
``LoadGame`` is discarded.
"""

from __future__ import annotations

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow

__all__ = ["LOAD_GAME", "SHUTDOWN", "latest_session", "window_of"]

LOAD_GAME = "LoadGame"
SHUTDOWN = "Shutdown"

# Offset added to a found index to advance past it. Structural, not domain.
_NEXT = 1
# Index of the first element of a non-empty ordered sequence.
_FIRST = 0


def _sorted_by_time(events: tuple[RawEvent, ...]) -> tuple[RawEvent, ...]:
    """Return events ordered non-decreasing by event-time (defensive)."""
    return tuple(sorted(events, key=lambda event: event.event_time.epoch_s))


def latest_session(events: tuple[RawEvent, ...]) -> tuple[RawEvent, ...]:
    """Return the slice covering only the most recent session.

    The slice runs from the last ``LoadGame`` event up to and including the
    first ``Shutdown`` that follows it; if no such ``Shutdown`` exists the
    slice runs to the end of the log. Returns an empty tuple when there is
    no ``LoadGame`` at all.
    """
    ordered = _sorted_by_time(events)
    last_load_index: int | None = None
    for index, event in enumerate(ordered):
        if event.event_type == LOAD_GAME:
            last_load_index = index
    if last_load_index is None:
        return ()
    session = ordered[last_load_index:]
    for offset, event in enumerate(session):
        if event.event_type == SHUTDOWN:
            return session[: offset + _NEXT]
    return session


def window_of(session_events: tuple[RawEvent, ...]) -> SessionWindow:
    """Build the SessionWindow spanning the given session events.

    Start is the first event-time, end is the last; the session counts as a
    clean shutdown when its final event is a ``Shutdown``. Raises
    ``AggregationError`` on empty input (there is no window to describe).
    """
    if not session_events:
        raise AggregationError("Cannot build a window from no events.")
    ordered = _sorted_by_time(session_events)
    start: EventTime = ordered[_FIRST].event_time
    last_event = ordered[-_NEXT]
    end: EventTime = last_event.event_time
    clean_shutdown = last_event.event_type == SHUTDOWN
    return SessionWindow(start=start, end=end, clean_shutdown=clean_shutdown)
