"""DebriefBuilder: fold a session's raw events into a SessionDebrief.

The builder is the application-side composition of three domain steps: it
derives the session window, turns events into conceptual moments under the
configured spec, then assembles the final debrief. It holds the spec so the
caller passes only the per-session inputs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from o7debrief.application.services.death_details import (
    Death,
    deaths_in,
    stamp_deaths,
)
from o7debrief.application.services.location_state import (
    LocationHistory,
    extended,
    location_history,
)
from o7debrief.application.services.ship_state import SHIP_EVENTS, ship_history
from o7debrief.domain.aggregation.debrief_assembler import assemble
from o7debrief.domain.aggregation.moment_factory import build_moments
from o7debrief.domain.aggregation.session_bracketer import window_of
from o7debrief.domain.aggregation.ship_changes import ship_change_moments
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.domain.rules.rollup_spec import RollupSpec
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.system_name import SystemName

__all__ = ["DebriefBuilder", "HistoryCollection"]

# A session that never left one system still visited it. Used only when the
# session named no system of its own and a carried-forward reading supplies it.
_ONE_SYSTEM = 1

# The credit balance is a level rather than a delta: the journal states it
# outright at every login, in LoadGame's Credits. The latest reading in whatever
# events the builder was given is the one used, so the last-session path reports
# that session's reading and the all-history path reports the most recent one in
# the whole journal. LoadGame is already retained by _HISTORY_STATE_EVENTS
# (through SHIP_EVENTS), so the all-history fold needs no extra retention.
_BALANCE_EVENTS = ("LoadGame",)
_BALANCE_FIELD = "Credits"

# Journal events that name the commander, rank standing or active ship. The
# streaming history fold keeps only these (with the derived moments and the
# window endpoints), never the whole event history, so an all-history debrief
# stays bounded in memory. It must cover every type read by
# RankAnalyzer.extract_commander/analyse and by the ship-state fold; the
# streaming-equivalence test guards that this stays complete.
_HISTORY_STATE_EVENTS = (
    "Commander",
    "Rank",
    "Promotion",
    "Progress",
) + SHIP_EVENTS


@dataclass(frozen=True, slots=True)
class HistoryCollection:
    """The bounded data folded from streaming the whole journal history.

    Holds only the light, derived data an all-history debrief needs: the
    conceptual moments, the few state-bearing events that name the commander,
    rank and ship, the folded location history, plus the earliest and latest
    events seen (for the session window). The bulky raw events are never all
    held at once. Location and the death readings are folded rather than
    retained because the events behind them are among the most numerous in the
    journal, while the systems and deaths themselves are few. A death and the
    resurrection that prices it always fall in the same journal file, so
    folding a batch at a time loses nothing.
    """

    moments: tuple[ConceptualMoment, ...]
    state_events: tuple[RawEvent, ...]
    window_events: tuple[RawEvent, ...]
    location: LocationHistory = field(default_factory=LocationHistory)
    deaths: tuple[Death, ...] = ()


def _is_before(earlier: RawEvent, later: RawEvent) -> bool:
    """Return whether ``earlier`` occurred strictly before ``later``."""
    return earlier.event_time.epoch_s < later.event_time.epoch_s


def _latest_balance(events: tuple[RawEvent, ...]) -> Credits | None:
    """Return the newest credit balance stated in ``events``, else None.

    None means the journal offered no reading, which the report has to be able
    to say. Returning zero instead would make "no reading" indistinguishable
    from "no money", which is exactly the confusion this exists to remove. A
    boolean is rejected explicitly because bool is a subclass of int and a
    stray True would otherwise read as a balance of one credit.
    """
    balance: Credits | None = None
    for event in events:
        if event.event_type not in _BALANCE_EVENTS:
            continue
        value = event.get(_BALANCE_FIELD)
        if isinstance(value, int) and not isinstance(value, bool):
            balance = Credits(value)
    return balance


def _location_readings(
    events: tuple[RawEvent, ...], carried: str | None
) -> tuple[SystemName | None, SystemName | None, int | None]:
    """Return the (start, end, count) location readings for a set of events.

    A session that named a system reports its first and last plus how many
    distinct ones it named. One that named none falls back to the system
    carried forward from earlier history: the commander did not move, so that
    system is both endpoints and the single system visited. When neither
    states anything, all three are None and the report says so.
    """
    history = location_history(events)
    endpoints = history.endpoints()
    if endpoints is not None:
        start, end = endpoints
        return SystemName(start), SystemName(end), history.distinct_count()
    if carried is not None:
        return SystemName(carried), SystemName(carried), _ONE_SYSTEM
    return None, None, None


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
        carried_system: str | None = None,
    ) -> SessionDebrief:
        """Derive the window, build moments and assemble the debrief.

        ``events`` are the already-isolated events of one session. The
        domain validates emptiness and ordering, so the builder simply
        chains the three aggregation steps in order. The ship history is
        folded once and used twice: for the closing ship the header names, then
        to name the hull the commander was flying at each death.

        ``carried_system`` is the last system known from earlier history, used
        only when this session named none of its own.
        """
        window = window_of(events)
        history = ship_history(events)
        moments = _ordered_by_time(
            build_moments(events, self._spec) + ship_change_moments(events)
        )
        ship_type, ship_name = history.latest()
        start_system, end_system, visited = _location_readings(events, carried_system)
        return assemble(
            commander,
            window,
            stamp_deaths(moments, deaths_in(events), history, commander),
            rank_progression,
            self._spec,
            ship_type,
            ship_name,
            _latest_balance(events),
            start_system,
            end_system,
            visited,
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
        location = LocationHistory(systems=())
        deaths: list[Death] = []
        earliest: RawEvent | None = None
        latest: RawEvent | None = None
        for batch in batches:
            moments.extend(build_moments(batch, self._spec))
            location = extended(location, batch)
            deaths.extend(deaths_in(batch))
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
            location=location,
            deaths=tuple(deaths),
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
        history = ship_history(collection.state_events)
        ship_type, ship_name = history.latest()
        endpoints = collection.location.endpoints()
        start_system = None if endpoints is None else SystemName(endpoints[0])
        end_system = None if endpoints is None else SystemName(endpoints[1])
        visited = None if endpoints is None else collection.location.distinct_count()
        return assemble(
            commander,
            window,
            stamp_deaths(collection.moments, collection.deaths, history, commander),
            rank_progression,
            self._spec,
            ship_type,
            ship_name,
            _latest_balance(collection.state_events),
            start_system,
            end_system,
            visited,
        )
