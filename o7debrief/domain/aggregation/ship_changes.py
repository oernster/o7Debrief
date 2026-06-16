"""Ship-change records: turn shipyard events into rich change moments.

A debrief should record the ships a commander changed during a session, not
only the one they finished in. Elite names the ship moved into on a
``ShipyardSwap`` or ``ShipyardNew`` and gives a swap the stored ship's id, but
no shipyard event carries a ship's custom name. So this first indexes every
ship id seen this session to its localised type and custom name (gathered from
``LoadGame``, ``Loadout`` and the shipyard events), then walks the session and
emits one moment per change: a swap reads its from and to ships by id, a
purchase names the ship bought. Each is a Shipyard-domain ``ConceptualMoment``,
so it joins the timeline and the Shipyard category alongside every other moment.

The from ship of a swap is the stored ship (``StoreShipID``); the to ship is
the new one (``ShipID``); its custom name is picked up from the ``Loadout`` that
follows. A ship not seen elsewhere this session falls back to its internal
symbol, and an unidentifiable ship to a neutral placeholder.
"""

from __future__ import annotations

from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)

__all__ = ["ship_change_moments"]

# Journal events that name or move the active ship.
_LOAD_GAME = "LoadGame"
_LOADOUT = "Loadout"
_SWAP = "ShipyardSwap"
_NEW = "ShipyardNew"
_NAMING_EVENTS = (_LOAD_GAME, _LOADOUT, _SWAP, _NEW)

# Payload fields. An id identifies the ship; the localised type is preferred for
# display with the internal symbol as the fallback; the name is the custom name.
_ID_FIELDS = ("ShipID", "NewShipID")
_DISPLAY_TYPE_FIELDS = ("Ship_Localised", "ShipType_Localised")
_SYMBOL_TYPE_FIELDS = ("Ship", "ShipType")
_NAME_FIELDS = ("ShipName",)
# A swap names the stored (old) ship by id and internal symbol only.
_OLD_ID_FIELDS = ("StoreShipID",)
_OLD_SYMBOL_FIELDS = ("StoreOldShip",)

# Label templates. The wording defaults live here; {0} is the origin ship and
# {1} the destination, each formatted as "Type (Name)" when a name is known.
_SWAP_LABEL = "Swapped from {0} to {1}."
_PURCHASE_LABEL = "Bought {0}."
_TYPE_WITH_NAME = "{0} ({1})"
_UNKNOWN_SHIP = "an unknown ship"

# A ship change is recorded for its own sake: it carries no magnitude, no credit
# delta (so it never moves net credits) and no location detail.
_NO_MAGNITUDE = 0
_NO_DETAIL: tuple[tuple[str, object], ...] = ()


def _first_str(event: RawEvent, fields: tuple[str, ...]) -> str:
    """Return the first of ``fields`` holding a non-empty string, else blank."""
    for field in fields:
        value = event.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _first_int(event: RawEvent, fields: tuple[str, ...]) -> int | None:
    """Return the first of ``fields`` holding a plain integer, else ``None``."""
    for field in fields:
        value = event.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _index_ships(
    events: tuple[RawEvent, ...],
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    """Index ship id to its localised type, internal symbol and custom name."""
    types: dict[int, str] = {}
    symbols: dict[int, str] = {}
    names: dict[int, str] = {}
    for event in events:
        if event.event_type not in _NAMING_EVENTS:
            continue
        ship_id = _first_int(event, _ID_FIELDS)
        if ship_id is None:
            continue
        localised = _first_str(event, _DISPLAY_TYPE_FIELDS)
        if localised:
            types[ship_id] = localised
        symbol = _first_str(event, _SYMBOL_TYPE_FIELDS)
        if symbol:
            symbols[ship_id] = symbol
        name = _first_str(event, _NAME_FIELDS)
        if name:
            names[ship_id] = name
    return types, symbols, names


def _display(
    ship_id: int | None,
    fallback_symbol: str,
    types: dict[int, str],
    symbols: dict[int, str],
    names: dict[int, str],
) -> str:
    """Format a ship as 'Type (Name)', falling back to symbol then placeholder."""
    type_text = ""
    if ship_id is not None:
        type_text = types.get(ship_id, "") or symbols.get(ship_id, "")
    if not type_text:
        type_text = fallback_symbol or _UNKNOWN_SHIP
    name = names.get(ship_id, "") if ship_id is not None else ""
    if name:
        return _TYPE_WITH_NAME.format(type_text, name)
    return type_text


def _moment(kind: MomentKind, label: str, event: RawEvent) -> ConceptualMoment:
    """Build one Shipyard-domain moment at an event's time with a given label."""
    return ConceptualMoment(
        kind=kind,
        domain=ActivityDomain.SHIPYARD,
        mode=ActivityMode.SHIP,
        occurred_at=event.event_time,
        label=label,
        magnitude=_NO_MAGNITUDE,
        credits_delta=Credits.zero(),
        detail=_NO_DETAIL,
    )


def ship_change_moments(
    events: tuple[RawEvent, ...],
) -> tuple[ConceptualMoment, ...]:
    """Return a moment per ship swap or purchase, in event order.

    A ``ShipyardSwap`` becomes a "Swapped from A to B" moment and a
    ``ShipyardNew`` a "Bought B" moment, each ship resolved to its type and
    custom name from the session. Events that are not ship changes are ignored.
    """
    types, symbols, names = _index_ships(events)
    moments: list[ConceptualMoment] = []
    for event in events:
        if event.event_type == _SWAP:
            origin = _display(
                _first_int(event, _OLD_ID_FIELDS),
                _first_str(event, _OLD_SYMBOL_FIELDS),
                types,
                symbols,
                names,
            )
            destination = _display(
                _first_int(event, _ID_FIELDS),
                _first_str(event, _SYMBOL_TYPE_FIELDS),
                types,
                symbols,
                names,
            )
            moments.append(
                _moment(
                    MomentKind.SHIP_SWAP,
                    _SWAP_LABEL.format(origin, destination),
                    event,
                )
            )
        elif event.event_type == _NEW:
            destination = _display(
                _first_int(event, _ID_FIELDS),
                _first_str(event, _SYMBOL_TYPE_FIELDS),
                types,
                symbols,
                names,
            )
            moments.append(
                _moment(
                    MomentKind.SHIP_PURCHASE,
                    _PURCHASE_LABEL.format(destination),
                    event,
                )
            )
    return tuple(moments)
