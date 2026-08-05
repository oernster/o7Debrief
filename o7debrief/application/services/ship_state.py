"""Active-ship tracking across a set of journal events.

The ship a commander flies is a level rather than an event: it persists until a
journal event moves it on, so the ship in effect at any instant is whatever the
latest ship-naming event before that instant stated. This module owns that
tracking for the whole application, both the closing state the report header
names and the state at an arbitrary instant, which a death row needs so it
names the hull that was actually lost rather than the one the session ended in.

``LoadGame`` names the ship at login; ``Loadout`` names it whenever the
commander boards one (including after a swap or purchase); ``ShipyardSwap`` and
``ShipyardNew`` name the ship swapped or bought into. LoadGame and Loadout use
Ship (with Ship_Localised); the shipyard events use ShipType (with
ShipType_Localised). ShipName carries the commander's own name for the ship.

Internal symbols are matched case-insensitively: the journal writes the same
ship as "Cutter" in LoadGame yet "cutter" in Loadout and ShipyardSwap, so a
case-sensitive match would lose the localised name on an unswapped ship. The
display type is resolved once every event has been seen rather than as each
arrives, because a later event that spells the same hull readably is naming the
ship rather than changing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.model.raw_event import RawEvent

__all__ = ["SHIP_EVENTS", "ShipHistory", "ship_history"]

# Journal events that establish or change the active ship.
SHIP_EVENTS = ("LoadGame", "Loadout", "ShipyardSwap", "ShipyardNew")

_INTERNAL_FIELDS = ("Ship", "ShipType")
_DISPLAY_FIELDS = ("Ship_Localised", "ShipType_Localised")
_NAME_FIELDS = ("ShipName",)

# What an unknown ship reads as: a blank type and a blank custom name. Blank
# rather than a placeholder, so every caller decides for itself how to say
# "not known" in its own wording.
_NO_SHIP = ("", "")


@dataclass(frozen=True, slots=True)
class ShipHistory:
    """The ship states a set of events passed through, oldest first.

    Each state is ``(epoch_s, display type, custom name)`` and holds from its
    own instant until the next one, so a lookup answers with the state in
    force rather than the nearest change.
    """

    states: tuple[tuple[float, str, str], ...]

    def at(self, epoch_s: float) -> tuple[str, str]:
        """Return the (type, custom name) in effect at an instant, else blanks."""
        found = _NO_SHIP
        for state_s, ship_type, ship_name in self.states:
            if state_s <= epoch_s:
                found = (ship_type, ship_name)
        return found

    def latest(self) -> tuple[str, str]:
        """Return the (type, custom name) the events ended on, else blanks."""
        if not self.states:
            return _NO_SHIP
        _, ship_type, ship_name = self.states[-1]
        return ship_type, ship_name


def _first_str(event: RawEvent, fields: tuple[str, ...]) -> str:
    """Return the first of ``fields`` that holds a non-empty string, else blank."""
    for field in fields:
        value = event.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def ship_history(events: tuple[RawEvent, ...]) -> ShipHistory:
    """Fold the ship-naming events into the states they passed through.

    A state is recorded only where the hull or its custom name actually
    changed, so a session that boards the same ship two hundred times keeps one
    entry. The custom name resets when the hull changes, so an old name never
    shows on a new one.
    """
    localised_by_key: dict[str, str] = {}
    folded: list[tuple[float, str, str, str]] = []
    current_key = ""
    current_symbol = ""
    ship_name = ""
    for event in events:
        if event.event_type not in SHIP_EVENTS:
            continue
        symbol = _first_str(event, _INTERNAL_FIELDS)
        key = symbol.lower()
        localised = _first_str(event, _DISPLAY_FIELDS)
        if key and localised:
            localised_by_key[key] = localised
        if key and key != current_key:
            current_key = key
            current_symbol = symbol
            ship_name = ""
        name = _first_str(event, _NAME_FIELDS)
        if name:
            ship_name = name
        state = (current_key, current_symbol, ship_name)
        if not folded or folded[-1][1:] != state:
            folded.append((event.event_time.epoch_s,) + state)
    return ShipHistory(
        states=tuple(
            (state_s, localised_by_key.get(key, symbol), name)
            for state_s, key, symbol, name in folded
        )
    )
