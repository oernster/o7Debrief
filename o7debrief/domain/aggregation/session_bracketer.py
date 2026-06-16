"""Session isolation: extract the single latest play session from a log.

This is the session-isolation keystone. A journal file can contain many
sessions (the game was started, played, quit, started again). The debrief
must describe ONLY the most recent session. A session is one game run,
bounded by ``Shutdown`` events, so we slice the run ending at the last
``Shutdown`` (or at the end of the log when the game crashed without one),
starting just after the previous ``Shutdown``. Every ``LoadGame`` inside
that run, including the ones a main-menu return fires, stays in the session.
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
    """Return the slice covering only the most recent game run.

    A session is one game run, bounded by ``Shutdown`` events: every
    ``Shutdown`` ends the run it belongs to. Elite fires a fresh ``LoadGame``
    whenever the commander drops to the main menu and back (a mode switch, a
    death to the menu or a relog), so anchoring on ``LoadGame`` would shrink a
    run that touched the menu down to its final leg. Anchoring on ``Shutdown``
    instead keeps every ``LoadGame`` of the run in one session.

    The most recent session ends at the last ``Shutdown`` when the log finishes
    there, otherwise it runs to the end of the log (the game crashed before a
    clean shutdown or none was recorded). It starts just after the previous
    ``Shutdown`` (or at the start of the log when there is no earlier one).
    Returns an empty tuple only when there are no events at all.
    """
    ordered = _sorted_by_time(events)
    if not ordered:
        return ()
    shutdowns = tuple(
        index for index, event in enumerate(ordered) if event.event_type == SHUTDOWN
    )
    if not shutdowns:
        return ordered
    last_shutdown = shutdowns[-_NEXT]
    after_last_shutdown = ordered[last_shutdown + _NEXT :]
    if after_last_shutdown:
        return after_last_shutdown
    earlier_shutdowns = shutdowns[:-_NEXT]
    start = earlier_shutdowns[-_NEXT] + _NEXT if earlier_shutdowns else _FIRST
    return ordered[start : last_shutdown + _NEXT]


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
