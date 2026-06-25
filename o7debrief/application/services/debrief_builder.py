"""DebriefBuilder: fold a session's raw events into a SessionDebrief.

The builder is the application-side composition of three domain steps: it
derives the session window, turns events into conceptual moments under the
configured spec, and assembles the final debrief. It holds the spec so the
caller passes only the per-session inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from o7debrief.domain.aggregation.moment_factory import build_moments
from o7debrief.domain.aggregation.debrief_assembler import assemble
from o7debrief.domain.aggregation.session_bracketer import window_of
from o7debrief.domain.aggregation.ship_changes import ship_change_moments
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.domain.rules.rollup_spec import RollupSpec
from o7debrief.domain.value_objects.commander_id import CommanderId

__all__ = ["DebriefBuilder", "HistoryCollection"]

# Journal events that establish or change the active ship across a session, and
# the fields that name it. LoadGame names the ship at login; Loadout names it
# whenever the commander boards one (including after a swap or purchase);
# ShipyardSwap and ShipyardNew name the ship swapped or bought into. LoadGame and
# Loadout use Ship (with Ship_Localised); the shipyard events use ShipType (with
# ShipType_Localised). ShipName carries the commander's own name for the ship.
_SHIP_EVENTS = ("LoadGame", "Loadout", "ShipyardSwap", "ShipyardNew")
_SHIP_INTERNAL_FIELDS = ("Ship", "ShipType")
_SHIP_DISPLAY_FIELDS = ("Ship_Localised", "ShipType_Localised")
_SHIP_NAME_FIELDS = ("ShipName",)

# Journal events that name the commander, rank standing or active ship. The
# streaming history fold keeps only these (with the derived moments and the
# window endpoints), never the whole event history, so an all-history debrief
# stays bounded in memory. It must cover every type read by
# RankAnalyzer.extract_commander/analyse and by _ship_type_and_name; the
# streaming-equivalence test guards that this stays complete.
_HISTORY_STATE_EVENTS = (
    "Commander",
    "Rank",
    "Promotion",
    "Progress",
) + _SHIP_EVENTS


@dataclass(frozen=True, slots=True)
class HistoryCollection:
    """The bounded data folded from streaming the whole journal history.

    Holds only the light, derived data an all-history debrief needs: the
    conceptual moments, the few state-bearing events that name the commander,
    rank and ship, and the earliest and latest events seen (for the session
    window). The bulky raw events are never all held at once.
    """

    moments: tuple[ConceptualMoment, ...]
    state_events: tuple[RawEvent, ...]
    window_events: tuple[RawEvent, ...]


def _is_before(earlier: RawEvent, later: RawEvent) -> bool:
    """Return whether ``earlier`` occurred strictly before ``later``."""
    return earlier.event_time.epoch_s < later.event_time.epoch_s


def _first_str(event: RawEvent, fields: tuple[str, ...]) -> str:
    """Return the first of ``fields`` that holds a non-empty string, else blank."""
    for field in fields:
        value = event.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _ship_type_and_name(events: tuple[RawEvent, ...]) -> tuple[str, str]:
    """Return the (type, name) of the latest ship the commander is flying.

    The active ship is tracked across the session rather than frozen at login: a
    mid-session change (a Loadout on boarding, a ShipyardSwap or a ShipyardNew)
    moves it on, so a swap is reflected instead of reporting the login vessel.
    The localised type (for example "Imperial Cutter") is preferred over the
    internal symbol and is paired to the active ship from whichever event in the
    session carried it, with the internal symbol as the fallback. The custom name
    resets when the ship changes, so the old name never shows on a new hull.

    Internal symbols are matched case-insensitively: the journal writes the same
    ship as "Cutter" in LoadGame yet "cutter" in Loadout and ShipyardSwap, so a
    case-sensitive match would lose the localised name on an unswapped ship.
    """
    localised_by_key: dict[str, str] = {}
    current_key = ""
    current_symbol = ""
    ship_name = ""
    for event in events:
        if event.event_type not in _SHIP_EVENTS:
            continue
        symbol = _first_str(event, _SHIP_INTERNAL_FIELDS)
        key = symbol.lower()
        localised = _first_str(event, _SHIP_DISPLAY_FIELDS)
        if key and localised:
            localised_by_key[key] = localised
        if key and key != current_key:
            current_key = key
            current_symbol = symbol
            ship_name = ""
        name = _first_str(event, _SHIP_NAME_FIELDS)
        if name:
            ship_name = name
    ship_type = localised_by_key.get(current_key, current_symbol)
    return ship_type, ship_name


def _ordered_by_time(
    moments: tuple[ConceptualMoment, ...],
) -> tuple[ConceptualMoment, ...]:
    """Return the moments in non-decreasing event-time order (stable)."""
    return tuple(sorted(moments, key=lambda moment: moment.occurred_at.epoch_s))


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
        """Derive the window, build moments and assemble the debrief.

        ``events`` are the already-isolated events of one session. The
        domain validates emptiness and ordering, so the builder simply
        chains the three aggregation steps in order.
        """
        window = window_of(events)
        moments = _ordered_by_time(
            build_moments(events, self._spec) + ship_change_moments(events)
        )
        ship_type, ship_name = _ship_type_and_name(events)
        return assemble(
            commander,
            window,
            moments,
            rank_progression,
            self._spec,
            ship_type,
            ship_name,
        )

    def collect_history(
        self, batches: Iterable[tuple[RawEvent, ...]]
    ) -> HistoryCollection:
        """Fold streamed per-file event batches into a bounded collection.

        Each batch's rule-based moments are built straight away and the batch
        discarded; ship-change moments are resolved once from the retained ship
        events. Only the moments, the state-bearing events and the earliest and
        latest events seen are kept, so the whole raw history is never resident
        at once.
        """
        moments: list[ConceptualMoment] = []
        state_events: list[RawEvent] = []
        earliest: RawEvent | None = None
        latest: RawEvent | None = None
        for batch in batches:
            moments.extend(build_moments(batch, self._spec))
            for current in batch:
                if current.event_type in _HISTORY_STATE_EVENTS:
                    state_events.append(current)
                if earliest is None or _is_before(current, earliest):
                    earliest = current
                if latest is None or _is_before(latest, current):
                    latest = current
        kept = tuple(state_events)
        # Ship-change moments are resolved once from the full set of retained
        # ship events, never per file, so a ship renamed across sessions reads
        # exactly as a whole-history build would instead of by the name it held
        # in whichever file the swap fell in.
        all_moments = tuple(moments) + ship_change_moments(kept)
        endpoints = tuple(seen for seen in (earliest, latest) if seen is not None)
        return HistoryCollection(
            moments=_ordered_by_time(all_moments),
            state_events=kept,
            window_events=endpoints,
        )

    def build_collected(
        self,
        commander: CommanderId,
        collection: HistoryCollection,
        rank_progression: tuple[RankDelta, ...],
    ) -> SessionDebrief:
        """Assemble an all-history debrief from a folded HistoryCollection.

        Mirrors ``build`` but takes the pre-folded moments, state events and
        window endpoints, so it never needs the whole event history in hand.
        """
        window = window_of(collection.window_events)
        ship_type, ship_name = _ship_type_and_name(collection.state_events)
        return assemble(
            commander,
            window,
            collection.moments,
            rank_progression,
            self._spec,
            ship_type,
            ship_name,
        )
