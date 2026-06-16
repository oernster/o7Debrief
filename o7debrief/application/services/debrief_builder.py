"""DebriefBuilder: fold a session's raw events into a SessionDebrief.

The builder is the application-side composition of three domain steps: it
derives the session window, turns events into conceptual beats under the
configured spec, and assembles the final debrief. It holds the spec so the
caller passes only the per-session inputs.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.beat_factory import build_beats
from o7debrief.domain.aggregation.debrief_assembler import assemble
from o7debrief.domain.aggregation.session_bracketer import window_of
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.domain.rules.rollup_spec import RollupSpec
from o7debrief.domain.value_objects.commander_id import CommanderId

__all__ = ["DebriefBuilder"]

# Journal event and fields naming the ship the commander is flying. The
# localised name is preferred; the internal symbol is the fallback. These are
# the journal's own vocabulary, declared here so the builder is their reader.
_LOAD_GAME_EVENT = "LoadGame"
_SHIP_DISPLAY_FIELD = "Ship_Localised"
_SHIP_FIELD = "Ship"


def _ship_of(events: tuple[RawEvent, ...]) -> str:
    """Return the ship from the latest LoadGame event, or an empty string.

    The localised name (for example "Panther Clipper Mk II") is preferred; the
    internal symbol is the fallback. The latest LoadGame wins, so a ship swap
    across an all-history read reports the most recent vessel.
    """
    ship = ""
    for event in events:
        if event.event_type != _LOAD_GAME_EVENT:
            continue
        display = event.get(_SHIP_DISPLAY_FIELD)
        internal = event.get(_SHIP_FIELD)
        if isinstance(display, str) and display.strip():
            ship = display
        elif isinstance(internal, str) and internal.strip():
            ship = internal
    return ship


class DebriefBuilder:
    """Builds a SessionDebrief from a single session's events and ranks."""

    def __init__(self, spec: RollupSpec) -> None:
        self._spec = spec

    def build(
        self,
        commander: CommanderId,
        events: tuple[RawEvent, ...],
        rank_progression: tuple[RankDelta, ...],
    ) -> SessionDebrief:
        """Derive the window, build beats and assemble the debrief.

        ``events`` are the already-isolated events of one session. The
        domain validates emptiness and ordering, so the builder simply
        chains the three aggregation steps in order.
        """
        window = window_of(events)
        beats = build_beats(events, self._spec)
        return assemble(
            commander, window, beats, rank_progression, self._spec, _ship_of(events)
        )
