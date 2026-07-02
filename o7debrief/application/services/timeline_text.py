"""Row-text formatting for the session-log timeline.

Most moments render as their configured label. A few kinds carry payload the
report should surface instead: a death names who (or what) killed the commander
and how; a ship-launched-vehicle row names the vehicle; a bounty names the ship
that was destroyed. Because NPCs can now fly any ship, the killer ship and the
bounty target are read straight from the journal rather than from a fixed list.

This module is application-layer and imports no domain symbols: it reads the
moment by attribute (``kind.name``, ``detail``, ``label``) and routes all
wording through the label resolver, so nothing here hardcodes a display string.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["row_text"]

# Death rows. A death names its killer(s) or the cause; the wording is
# spec-overridable. The _Localised variant of a name or ship is preferred so a
# raw "$..." token is never shown when the journal offers a readable form.
_DEATH_KIND = "DEATH"
_KILLED_BY = ("death.killed_by", "Killed by")
_DEATH_NO_KILLER = ("death.no_killer", "Destroyed")
_DEATH_SELF_DESTRUCT = ("death.self_destruct", "Self-destruct")
_NAME_JOINER = ("list.and", "and")
_SELF_DESTRUCT_FIELD = "SelfDestruct"
_KILLER_NAME_FIELDS = ("KillerName_Localised", "KillerName")
_KILLER_SHIP_FIELDS = ("KillerShip_Localised", "KillerShip")
_KILLER_RANK_FIELD = "KillerRank"
_KILLERS_FIELD = "Killers"
_WING_NAME_FIELDS = ("Name_Localised", "Name")
_EXTRA_SEP = ", "
_NAME_SEP = ", "

# Ship-launched-vehicle rows (the Nomad vessel and ship-launched fighters) name
# the vehicle type, read from the moment detail (set by the moment factory) with
# a per-class generic fallback. Deploy, dock and loss share one verb.
_VESSEL_TYPE_FIELD = "VesselType"
_DEPLOYED = ("vehicle.deployed", "Deployed the")
_DOCKED = ("vehicle.docked", "Docked the")
_LOST = ("vehicle.lost", "Lost the")
_GENERIC_VESSEL = ("slv.vessel", "ship-launched vessel")
_GENERIC_FIGHTER = ("slf.fighter", "ship-launched fighter")
_VEHICLE_ROWS = {
    "SLV_DEPLOY": (_DEPLOYED, _GENERIC_VESSEL),
    "SLV_DOCK": (_DOCKED, _GENERIC_VESSEL),
    "SLV_DESTROYED": (_LOST, _GENERIC_VESSEL),
    "SLF_DEPLOY": (_DEPLOYED, _GENERIC_FIGHTER),
    "SLF_DOCK": (_DOCKED, _GENERIC_FIGHTER),
    "SLF_DESTROYED": (_LOST, _GENERIC_FIGHTER),
}

# Bounty rows name the destroyed ship, which since the latest game update can be
# any ship type an NPC flies. The readable Target_Localised is preferred; a bare
# Target (for example "mamba") is title-cased.
_BOUNTY_KIND = "BOUNTY"
_BOUNTY_ON = ("combat.bounty_on", "Bounty on")
_BOUNTY_GENERIC = ("combat.bounty", "Bounty")
_TARGET_LOCALISED_FIELD = "Target_Localised"
_TARGET_FIELD = "Target"


def _first_str(mapping, keys) -> str | None:
    """Return the first present, non-blank string among keys in a mapping."""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _titlecase(value: object) -> str | None:
    """Return an internal token title-cased for display, or None if blank."""
    if isinstance(value, str) and value.strip():
        return value.title()
    return None


def _join_names(names: list[str], resolver) -> str:
    """Join killer names with commas and a configurable final conjunction."""
    if len(names) == 1:
        return names[0]
    joiner = resolver.generic(*_NAME_JOINER)
    return f"{_NAME_SEP.join(names[:-1])} {joiner} {names[-1]}"


def _wing_killers_text(entries, resolver) -> str | None:
    """Return the summary for a wing kill, or None if it names no attacker."""
    names = [
        name
        for entry in entries
        if isinstance(entry, dict)
        for name in (_first_str(entry, _WING_NAME_FIELDS),)
        if name is not None
    ]
    if not names:
        return None
    return f"{resolver.generic(*_KILLED_BY)} {_join_names(names, resolver)}"


def _single_killer_text(detail: dict, resolver) -> str | None:
    """Return the summary for a single killer, or None if none is named."""
    name = _first_str(detail, _KILLER_NAME_FIELDS)
    if name is None:
        return None
    ship = _first_str(detail, _KILLER_SHIP_FIELDS)
    rank = detail.get(_KILLER_RANK_FIELD)
    extras = [extra for extra in (ship, rank) if isinstance(extra, str) and extra.strip()]
    killed_by = resolver.generic(*_KILLED_BY)
    if extras:
        return f"{killed_by} {name} ({_EXTRA_SEP.join(extras)})"
    return f"{killed_by} {name}"


def _death_text(moment, resolver) -> str:
    """Return the death row text: who killed the commander, or a plain loss."""
    detail = dict(moment.detail)
    killers = detail.get(_KILLERS_FIELD)
    if isinstance(killers, (list, tuple)) and killers:
        wing = _wing_killers_text(killers, resolver)
        if wing is not None:
            return wing
    single = _single_killer_text(detail, resolver)
    if single is not None:
        return single
    if detail.get(_SELF_DESTRUCT_FIELD) is True:
        return resolver.generic(*_DEATH_SELF_DESTRUCT)
    return resolver.generic(*_DEATH_NO_KILLER)


def _vehicle_text(moment, resolver) -> str:
    """Return a ship-launched-vehicle row naming the vehicle type."""
    verb_label, generic_label = _VEHICLE_ROWS[moment.kind.name]
    vehicle = dict(moment.detail).get(_VESSEL_TYPE_FIELD)
    if not (isinstance(vehicle, str) and vehicle.strip()):
        vehicle = resolver.generic(*generic_label)
    return f"{resolver.generic(*verb_label)} {vehicle}"


def _bounty_text(moment, resolver) -> str:
    """Return a bounty row naming the destroyed ship, or a bare bounty."""
    detail = dict(moment.detail)
    ship = _first_str(detail, (_TARGET_LOCALISED_FIELD,)) or _titlecase(
        detail.get(_TARGET_FIELD)
    )
    if ship is None:
        return resolver.generic(*_BOUNTY_GENERIC)
    return f"{resolver.generic(*_BOUNTY_ON)} {ship}"


def row_text(moment, resolver) -> str:
    """Return the session-log text for a moment, enriched where the kind needs it."""
    kind = moment.kind.name
    if kind == _DEATH_KIND:
        return _death_text(moment, resolver)
    if kind in _VEHICLE_ROWS:
        return _vehicle_text(moment, resolver)
    if kind == _BOUNTY_KIND:
        return _bounty_text(moment, resolver)
    return moment.label
