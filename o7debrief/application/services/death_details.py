"""Everything the journal knows about a death, stamped onto its moment.

A death row read back months later has to stand alone. The journal's ``Died``
event carries almost nothing: five of six real deaths carry only a timestamp,
and the sixth names its killer with a raw model token. Everything else worth
reporting is in the events around it, so it is gathered here and stamped onto
the moment, because the presenter is handed the assembled debrief alone and
never the events behind it.

Four readings are gathered, each confirmed against real journals:

* The victim: the commander plus the ship in force at that instant.
* The vehicle actually lost. An ``SRVDestroyed`` since the last resurrection
  means the commander died in the SRV, so the row names the SRV rather than
  the mothership it was launched from.
* The killer's ship, properly named. ``Died`` gives "cobramkv"; the full
  ``ShipTargeted`` scan of the same pilot moments earlier gives "Cobra Mk V"
  and their squadron.
* The rebuy. ``Resurrect`` states the cost of getting the ship back, which is
  a real charge no other event reports.

The ship is read at the instant of death rather than taken from the closing
state, because a commander who dies in one hull and finishes in another would
otherwise be reported in the wrong ship; an all-history debrief spans
every hull the commander has ever flown.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.enums import MomentKind

if TYPE_CHECKING:
    from o7debrief.application.services.ship_state import ShipHistory

__all__ = [
    "KILLER_SHIP_FIELD",
    "KILLER_SQUADRON_FIELD",
    "REBUY_COST_FIELD",
    "VICTIM_NAME_FIELD",
    "VICTIM_SHIP_FIELD",
    "VICTIM_SHIP_NAME_FIELD",
    "Death",
    "deaths_in",
    "stamp_deaths",
]

# Detail keys the gathered readings ride on. The victim and rebuy keys are
# this application's own vocabulary, since the journal names only the killer;
# the killer ship key is the journal's own, so stamping a better value there
# needs no change in the row formatter, which already prefers it.
VICTIM_NAME_FIELD = "VictimName"
VICTIM_SHIP_FIELD = "VictimShip"
VICTIM_SHIP_NAME_FIELD = "VictimShipName"
KILLER_SHIP_FIELD = "KillerShip_Localised"
KILLER_SQUADRON_FIELD = "KillerSquadron"
REBUY_COST_FIELD = "RebuyCost"

_STAMPED_FIELDS = (
    VICTIM_NAME_FIELD,
    VICTIM_SHIP_FIELD,
    VICTIM_SHIP_NAME_FIELD,
    KILLER_SHIP_FIELD,
    KILLER_SQUADRON_FIELD,
    REBUY_COST_FIELD,
)

# Journal vocabulary for the events read here.
_DIED = "Died"
_KILLER_NAME_FIELDS = ("KillerName_Localised", "KillerName")
_SRV_DESTROYED = "SRVDestroyed"
_SRV_TYPE_FIELDS = ("SRVType_Localised", "SRVType")
_RESURRECT = "Resurrect"
_COST_FIELD = "Cost"
_SHIP_TARGETED = "ShipTargeted"
_SCAN_STAGE_FIELD = "ScanStage"
# The journal's scan stage for a fully identified target, the only stage that
# names both the pilot and their ship.
_FULL_SCAN = 3
_PILOT_FIELDS = ("PilotName_Localised", "PilotName")
_TARGET_SHIP_FIELDS = ("Ship_Localised", "Ship")
_SQUADRON_FIELD = "SquadronID"
# A resurrection that cost nothing is not a rebuy and is not reported.
_NO_COST = 0


@dataclass(frozen=True, slots=True)
class Death:
    """What the events around one death say about it."""

    epoch_s: float
    srv_type: str
    killer_ship: str
    killer_squadron: str
    rebuy_cost: int


def _first_str(event: RawEvent, fields: tuple[str, ...]) -> str:
    """Return the first of ``fields`` holding a non-empty string, else blank."""
    for field in fields:
        value = event.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _scan_of(event: RawEvent) -> tuple[str, str, str] | None:
    """Return (pilot key, ship, squadron) for a full scan, else None."""
    if event.get(_SCAN_STAGE_FIELD) != _FULL_SCAN:
        return None
    pilot = _first_str(event, _PILOT_FIELDS)
    if not pilot:
        return None
    return (
        pilot.casefold(),
        _first_str(event, _TARGET_SHIP_FIELDS),
        _first_str(event, (_SQUADRON_FIELD,)),
    )


def _rebuy_of(event: RawEvent) -> int:
    """Return the cost stated by a resurrection, else nothing owed."""
    value = event.get(_COST_FIELD)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return _NO_COST


def deaths_in(events: tuple[RawEvent, ...]) -> tuple[Death, ...]:
    """Gather what the events say about each death, in order.

    One pass, because every reading is positional: the SRV loss precedes the
    death, the scan of the killer precedes it too, then the rebuy follows it.
    The SRV is cleared at each resurrection, so a later death in the ship is
    never attributed to an SRV lost before it.
    """
    found: list[Death] = []
    scans: dict[str, tuple[str, str]] = {}
    srv_type = ""
    for event in events:
        if event.event_type == _SHIP_TARGETED:
            scan = _scan_of(event)
            if scan is not None:
                scans[scan[0]] = (scan[1], scan[2])
        elif event.event_type == _SRV_DESTROYED:
            srv_type = _first_str(event, _SRV_TYPE_FIELDS)
        elif event.event_type == _RESURRECT:
            srv_type = ""
            if found:
                found[-1] = replace(found[-1], rebuy_cost=_rebuy_of(event))
        elif event.event_type == _DIED:
            killer = _first_str(event, _KILLER_NAME_FIELDS).casefold()
            ship, squadron = scans.get(killer, ("", ""))
            found.append(
                Death(
                    epoch_s=event.event_time.epoch_s,
                    srv_type=srv_type,
                    killer_ship=ship,
                    killer_squadron=squadron,
                    rebuy_cost=_NO_COST,
                )
            )
    return tuple(found)


def _pairs(
    death: Death | None, commander: CommanderId, ship_type: str, ship_name: str
) -> tuple[tuple[str, object], ...]:
    """Return the detail pairs that actually carry a reading.

    A reading the journal never gave is left off entirely rather than stamped
    blank, so the row formatter sees only what is known. The SRV supersedes the
    ship. It takes no custom name with it: an SRV carries none.
    """
    if death is not None and death.srv_type:
        ship_type, ship_name = death.srv_type, ""
    candidates: tuple[tuple[str, object], ...] = (
        (VICTIM_NAME_FIELD, commander.name),
        (VICTIM_SHIP_FIELD, ship_type),
        (VICTIM_SHIP_NAME_FIELD, ship_name),
    )
    if death is not None:
        candidates = candidates + (
            (KILLER_SHIP_FIELD, death.killer_ship),
            (KILLER_SQUADRON_FIELD, death.killer_squadron),
            (REBUY_COST_FIELD, death.rebuy_cost),
        )
    return tuple((key, value) for key, value in candidates if value)


def _death_at(deaths: tuple[Death, ...], epoch_s: float) -> Death | None:
    """Return the gathered death at an instant, else None when not found."""
    for death in deaths:
        if death.epoch_s == epoch_s:
            return death
    return None


def _stamped(
    moment: ConceptualMoment,
    deaths: tuple[Death, ...],
    history: ShipHistory,
    commander: CommanderId,
) -> ConceptualMoment:
    """Return a death moment carrying its readings, else the moment unchanged."""
    if moment.kind is not MomentKind.DEATH:
        return moment
    epoch_s = moment.occurred_at.epoch_s
    ship_type, ship_name = history.at(epoch_s)
    kept = tuple(pair for pair in moment.detail if pair[0] not in _STAMPED_FIELDS)
    death = _death_at(deaths, epoch_s)
    return replace(moment, detail=kept + _pairs(death, commander, ship_type, ship_name))


def stamp_deaths(
    moments: tuple[ConceptualMoment, ...],
    deaths: tuple[Death, ...],
    history: ShipHistory,
    commander: CommanderId,
) -> tuple[ConceptualMoment, ...]:
    """Return the moments with every death carrying what the journal knows."""
    return tuple(_stamped(moment, deaths, history, commander) for moment in moments)
