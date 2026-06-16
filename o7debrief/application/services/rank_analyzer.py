"""RankAnalyzer: read raw events into rank progression and commander identity.

This collaborator performs the only rank work that needs the domain at
runtime: mapping the journal's per-ladder fields onto the rank ladders and
calling the domain's rank-progression function. It therefore imports the
domain layer and nothing else, and is injected into the one-shot service as
a forward-referenced dependency. Its inputs and outputs use ladder-key
strings so the application orchestrator never has to touch the domain enum.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.rank_progression import compute_rank_deltas
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.enums import RankLadder

__all__ = ["RankAnalyzer"]

# Journal event types and field keys naming the commander identity. These are
# the journal's own vocabulary, not domain values.
_COMMANDER_EVENT = "Commander"
_LOAD_GAME_EVENT = "LoadGame"
_FID_FIELD = "FID"
_NAME_FIELD = "Name"
_COMMANDER_FIELD = "Commander"
_PROMOTION_EVENT = "Promotion"
_PROGRESS_EVENT = "Progress"
_RANK_EVENT = "Rank"

# Mapping from a rank ladder to the journal field key that carries its value
# on Promotion, Progress and Rank events.
_LADDER_FIELDS: tuple[tuple[RankLadder, str], ...] = (
    (RankLadder.COMBAT, "Combat"),
    (RankLadder.TRADE, "Trade"),
    (RankLadder.EXPLORE, "Explore"),
    (RankLadder.CQC, "CQC"),
    (RankLadder.FEDERATION, "Federation"),
    (RankLadder.EMPIRE, "Empire"),
    (RankLadder.SOLDIER, "Soldier"),
    (RankLadder.EXOBIOLOGIST, "Exobiologist"),
)


def _string_field(event: RawEvent, key: str) -> str | None:
    """Return a non-empty string field value, else None."""
    value = event.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _int_fields(event: RawEvent) -> tuple[tuple[RankLadder, int], ...]:
    """Return (ladder, int-value) pairs present on an event by field key."""
    pairs: list[tuple[RankLadder, int]] = []
    for ladder, key in _LADDER_FIELDS:
        value = event.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            pairs.append((ladder, value))
    return tuple(pairs)


def _pairs_from_strings(
    raw: tuple[tuple[str, int], ...],
) -> tuple[tuple[RankLadder, int], ...]:
    """Map ladder-key string pairs onto ladder-keyed pairs, dropping unknowns."""
    by_key = {ladder.name.lower(): ladder for ladder, _ in _LADDER_FIELDS}
    pairs: list[tuple[RankLadder, int]] = []
    for key, value in raw:
        ladder = by_key.get(key)
        if ladder is not None:
            pairs.append((ladder, value))
    return tuple(pairs)


def _to_strings(
    pairs: tuple[tuple[RankLadder, int], ...] | None,
) -> tuple[tuple[str, int], ...] | None:
    """Convert ladder-keyed pairs back to string-keyed pairs (or pass None)."""
    if pairs is None:
        return None
    return tuple((ladder.name.lower(), value) for ladder, value in pairs)


class RankAnalyzer:
    """Reads events into a commander identity and rank progression."""

    def extract_commander(self, events: tuple[RawEvent, ...]) -> CommanderId | None:
        """Return the commander named in the events, or None if none is.

        The first Commander or LoadGame event carrying a name is used; the
        FID falls back to the name when the event omits it.
        """
        for event in events:
            if event.event_type not in (_COMMANDER_EVENT, _LOAD_GAME_EVENT):
                continue
            name = _string_field(event, _NAME_FIELD) or _string_field(
                event, _COMMANDER_FIELD
            )
            if name is None:
                continue
            fid = _string_field(event, _FID_FIELD) or name
            return CommanderId(fid=fid, name=name)
        return None

    def _current_tiers(
        self, events: tuple[RawEvent, ...]
    ) -> tuple[tuple[RankLadder, int], ...]:
        """Return the current tier per ladder, in canonical ladder order.

        The authoritative source is the journal's ``Rank`` event (emitted at
        load); any later ``Promotion`` event overrides it for the ladder it
        raises. Reading events in order means the latest value of either wins,
        so a mid-session promotion is reflected without a fresh ``Rank`` event.
        """
        latest: dict[RankLadder, int] = {}
        for event in events:
            if event.event_type not in (_RANK_EVENT, _PROMOTION_EVENT):
                continue
            for ladder, tier in _int_fields(event):
                latest[ladder] = tier
        return tuple(
            (ladder, latest[ladder]) for ladder, _ in _LADDER_FIELDS if ladder in latest
        )

    def _end_pcts(
        self, events: tuple[RawEvent, ...]
    ) -> tuple[tuple[RankLadder, int], ...] | None:
        """Return the closing percentages from the last Progress event.

        Only ``Progress`` carries percentages; the ``Rank`` event reuses the
        same field keys for tier indices, so it must not be read here.
        """
        found: tuple[tuple[RankLadder, int], ...] | None = None
        for event in events:
            if event.event_type == _PROGRESS_EVENT:
                pairs = _int_fields(event)
                if pairs:
                    found = pairs
        return found

    def analyse(
        self,
        events: tuple[RawEvent, ...],
        start_tiers: tuple[tuple[str, int], ...],
        start_pcts: tuple[tuple[str, int], ...],
    ) -> tuple[tuple[RankDelta, ...], tuple[tuple[str, int], ...] | None]:
        """Compute rank deltas and the closing percentages (string-keyed).

        Start tiers and percentages arrive as ladder-key strings (from the
        saved snapshot); the current tiers and closing percentages come from
        the events. The closing percentages are returned string-keyed so the
        caller can persist them without touching the domain enum.
        """
        end_tiers = self._current_tiers(events)
        end_pcts = self._end_pcts(events)
        deltas = compute_rank_deltas(
            _pairs_from_strings(start_tiers),
            _pairs_from_strings(start_pcts),
            end_tiers,
            end_pcts,
        )
        return deltas, _to_strings(end_pcts)
