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
# localised type name is preferred over the internal symbol; the player's own
# ship name is a separate field. These are the journal's own vocabulary,
# declared here so the builder is their reader.
_LOAD_GAME_EVENT = "LoadGame"
_SHIP_DISPLAY_FIELD = "Ship_Localised"
_SHIP_FIELD = "Ship"
_SHIP_NAME_FIELD = "ShipName"


def _ship_type_and_name(events: tuple[RawEvent, ...]) -> tuple[str, str]:
    """Return the (type, name) of the ship from the latest LoadGame event.

    The localised type name (for example "Panther Clipper Mk II") is preferred
    over the internal symbol, and the player's custom ship name (``ShipName``)
    is read alongside it. The latest LoadGame wins, so a ship swap across an
    all-history read reports the most recent vessel. Either part is an empty
    string when the journal does not carry it.
    """
    ship_type = ""
    ship_name = ""
    for event in events:
        if event.event_type != _LOAD_GAME_EVENT:
            continue
        display = event.get(_SHIP_DISPLAY_FIELD)
        internal = event.get(_SHIP_FIELD)
        if isinstance(display, str) and display.strip():
            ship_type = display
        elif isinstance(internal, str) and internal.strip():
            ship_type = internal
        name = event.get(_SHIP_NAME_FIELD)
        if isinstance(name, str) and name.strip():
            ship_name = name
    return ship_type, ship_name


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
        ship_type, ship_name = _ship_type_and_name(events)
        return assemble(
            commander,
            window,
            beats,
            rank_progression,
            self._spec,
            ship_type,
            ship_name,
        )
