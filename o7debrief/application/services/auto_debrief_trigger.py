"""AutoDebriefTrigger: decide when a finished session should auto-debrief.

A poll of the journal yields the events seen so far. This service inspects
them and reports whether the most recent session has just ended with a
``Shutdown`` that has not been acted on yet, so the tray can fire one debrief
automatically when the commander quits the game.

Two rules keep it from firing at the wrong moment. It primes on its first
observation: whatever completed session already sits in the journal when the
app starts is recorded, not debriefed, so launching the app (it starts with
Windows) never reopens an old debrief. After that it fires once per distinct
``Shutdown``, identified by that shutdown's event-time, so a run that ends is
debriefed exactly once and a later run re-arms it.

The decision is pure application logic over domain objects, so it carries no
Qt, I/O or timing; the tray owns the timer and the side effect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.domain.aggregation.session_bracketer import SHUTDOWN, latest_session

if TYPE_CHECKING:
    from o7debrief.domain.model.raw_event import RawEvent

__all__ = ["AutoDebriefTrigger"]


class AutoDebriefTrigger:
    """Reports when a newly finished session is due an automatic debrief."""

    def __init__(self) -> None:
        self._primed = False
        self._last_completed: str | None = None

    def debrief_due(self, events: tuple[RawEvent, ...]) -> bool:
        """Return whether the latest session just finished and is due a debrief.

        The first call only primes: it records the completed session already in
        the journal (if any) and returns ``False``. Later calls return ``True``
        once for each new ``Shutdown`` and ``False`` while a run is still in
        progress or for a shutdown already debriefed.
        """
        completed = _completed_session_id(events)
        if not self._primed:
            self._primed = True
            self._last_completed = completed
            return False
        if completed is None:
            return False
        if completed == self._last_completed:
            return False
        self._last_completed = completed
        return True


def _completed_session_id(events: tuple[RawEvent, ...]) -> str | None:
    """Return the latest session's closing-shutdown time, else ``None``.

    A finished session is identified by the event-time of the ``Shutdown`` that
    ends the most recent run. Returns ``None`` when there is no session yet or
    the latest run has not ended with a ``Shutdown``.
    """
    session = latest_session(events)
    if not session:
        return None
    last = session[-1]
    if last.event_type != SHUTDOWN:
        return None
    return last.event_time.iso_utc
