"""Row-text formatting for the session-log timeline.

A row is worded one of three ways, tried in this order.

1. A few kinds are assembled here in code, because their wording is conditional
   in ways a template should not carry: a death names who (or what) killed the
   commander and how, then the victim it cost and any rebuy; a
   ship-launched-vehicle row names the vehicle; a bounty names the ship that was
   destroyed; a mission names its faction and any Merc Coins. Because NPCs can
   now fly any ship, the killer ship and the bounty target are read straight
   from the journal rather than from a fixed list.
2. Otherwise the moment's taxonomy template is rendered against its detail,
   which is the raw journal payload. This is how a row states what actually
   happened ("Applied Weapon_Overcharged grade 5 to hpt_multicannon_gimbal_
   medium at Tod 'The Blaster' McQuinn") rather than merely naming its kind.
3. Failing both, the moment's label, which names the kind and claims nothing
   else.

Step 2 did not exist for a long time and its absence was the report's largest
defect: every template in the taxonomy parsed and was discarded, so every row
fell through to step 3 and a session of 261 engineering rolls printed
"Engineer Craft" 261 times, naming no blueprint, grade, module or engineer.

The fallback is deliberate rather than defensive. A template naming a field the
payload lacks yields no text at all (the renderer port returns ``None``); a row
then states its kind instead of a sentence with a hole in it. A partially
rendered sentence would read to a commander as a fact.

This module is application-layer and imports no domain symbols: it reads the
moment by attribute (``kind.name``, ``detail``, ``label``, ``text_template``)
and routes all wording through the label resolver, so nothing here hardcodes a
display string. Its one import is of the victim detail keys, taken from the
module that stamps them so the two never drift apart.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.services.death_details import (
    KILLER_SQUADRON_FIELD,
    REBUY_COST_FIELD,
    VICTIM_NAME_FIELD,
    VICTIM_SHIP_FIELD,
    VICTIM_SHIP_NAME_FIELD,
)

__all__ = ["row_text"]

# The moment attribute carrying the taxonomy's row template, read by name so
# this module keeps its no-domain-import rule, plus its absent/empty value.
_TEMPLATE_ATTR = "text_template"
_NO_TEMPLATE = ""

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

# Every death row also names the victim, because "Destroyed" on its own tells a
# reader coming back months later nothing about who was destroyed or what they
# were flying. The three parts (commander, hull, the commander's own name for
# it) degrade independently; a death carrying none of them reads exactly as
# it did before. The victim follows the cause after a separator so the cause
# keeps its own wording and any spec override of it still applies.
_VICTIM_TITLE = ("death.victim_title", "CMDR")
_VICTIM_IN = ("death.victim_in", "in")
_VICTIM_SEP = ": "
_SHIP_NAME_QUOTE = '"'
# The rebuy is a real charge the journal states only in the resurrection that
# follows a death. No other figure in the report accounts for it. A
# resurrection that cost nothing is not a rebuy, so nothing is shown.
_REBUY = ("death.rebuy", "rebuy")
_REBUY_OPEN = " ("
_REBUY_CLOSE = ")"
_NO_REBUY = 0

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

# Mission-completion rows name the mission (an Operation carries a readable
# LocalisedName) and its issuing faction, then surface the Merc Coins reward on
# the row when one was paid. The credit reward is totalled in the Missions
# section rather than repeated on every row. The _Localised name is preferred so
# a raw token is never shown when the journal offers a readable form.
_MISSION_KIND = "MISSION_COMPLETE"
_COMPLETED_VERB = ("missions.completed_verb", "Completed")
_MISSION_FOR = ("missions.for", "for")
_GENERIC_MISSION = ("missions.generic", "a mission")
_MISSION_NAME_FIELDS = ("LocalisedName", "Name")
_FACTION_FIELD = "Faction"
# Structural punctuation for a coin gain, for example " (+500 Merc Coins)".
_COIN_GAIN_OPEN = " (+"
_COIN_GAIN_CLOSE = ")"
_NO_COINS = 0


def _first_str(mapping, keys) -> str | None:
    """Return the first present, non-blank string among keys in a mapping."""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _titlecase(value: object) -> str | None:
    """Return an internal token title-cased for display, else None if blank."""
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
    """Return the summary for a wing kill, else None if it names no attacker."""
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
    """Return the summary for a single killer, else None if none is named."""
    name = _first_str(detail, _KILLER_NAME_FIELDS)
    if name is None:
        return None
    ship = _first_str(detail, _KILLER_SHIP_FIELDS)
    rank = detail.get(_KILLER_RANK_FIELD)
    squadron = detail.get(KILLER_SQUADRON_FIELD)
    extras = [
        extra
        for extra in (ship, rank, squadron)
        if isinstance(extra, str) and extra.strip()
    ]
    killed_by = resolver.generic(*_KILLED_BY)
    if extras:
        return f"{killed_by} {name} ({_EXTRA_SEP.join(extras)})"
    return f"{killed_by} {name}"


def _death_cause_text(detail: dict, resolver) -> str:
    """Return who killed the commander, else the cause of a killerless loss."""
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


def _hull_text(ship: str, ship_name: str) -> str:
    """Return the hull as its type, its given name or the type carrying it."""
    if not ship_name:
        return ship
    quoted = f"{_SHIP_NAME_QUOTE}{ship_name}{_SHIP_NAME_QUOTE}"
    if not ship:
        return quoted
    return f"{ship} {quoted}"


def _victim_text(detail: dict, resolver) -> str | None:
    """Return the clause naming the victim, else None when none was recorded."""
    name = _first_str(detail, (VICTIM_NAME_FIELD,))
    hull = _hull_text(
        _first_str(detail, (VICTIM_SHIP_FIELD,)) or "",
        _first_str(detail, (VICTIM_SHIP_NAME_FIELD,)) or "",
    )
    if name is None:
        return hull or None
    who = f"{resolver.generic(*_VICTIM_TITLE)} {name}"
    if not hull:
        return who
    return f"{who} {resolver.generic(*_VICTIM_IN)} {hull}"


def _rebuy_text(detail: dict, resolver, fmt) -> str:
    """Return the parenthesised rebuy charge, else nothing when none was paid."""
    cost = detail.get(REBUY_COST_FIELD)
    if not isinstance(cost, int) or isinstance(cost, bool) or cost <= _NO_REBUY:
        return ""
    label = resolver.generic(*_REBUY)
    return f"{_REBUY_OPEN}{label} {fmt.credits(cost)}{_REBUY_CLOSE}"


def _death_text(moment, resolver, fmt) -> str:
    """Return the death row: the cause, who and what was lost, then the rebuy."""
    detail = dict(moment.detail)
    line = _death_cause_text(detail, resolver)
    victim = _victim_text(detail, resolver)
    if victim is not None:
        line = f"{line}{_VICTIM_SEP}{victim}"
    return f"{line}{_rebuy_text(detail, resolver, fmt)}"


def _vehicle_text(moment, resolver) -> str:
    """Return a ship-launched-vehicle row naming the vehicle type."""
    verb_label, generic_label = _VEHICLE_ROWS[moment.kind.name]
    vehicle = dict(moment.detail).get(_VESSEL_TYPE_FIELD)
    if not (isinstance(vehicle, str) and vehicle.strip()):
        vehicle = resolver.generic(*generic_label)
    return f"{resolver.generic(*verb_label)} {vehicle}"


def _bounty_text(moment, resolver) -> str:
    """Return a bounty row naming the destroyed ship, else a bare bounty."""
    detail = dict(moment.detail)
    ship = _first_str(detail, (_TARGET_LOCALISED_FIELD,)) or _titlecase(
        detail.get(_TARGET_FIELD)
    )
    if ship is None:
        return resolver.generic(*_BOUNTY_GENERIC)
    return f"{resolver.generic(*_BOUNTY_ON)} {ship}"


def _mission_text(moment, resolver, fmt) -> str:
    """Return a mission-completion row: the mission, its faction and any coins.

    An Operation pays a Merc Coins reward, appended in parentheses when present;
    the credit reward is totalled in the Missions section, not repeated here.
    The formatter is used only to group and suffix the coin amount.
    """
    detail = dict(moment.detail)
    name = _first_str(detail, _MISSION_NAME_FIELDS) or resolver.generic(
        *_GENERIC_MISSION
    )
    verb = resolver.generic(*_COMPLETED_VERB)
    faction = _first_str(detail, (_FACTION_FIELD,))
    if faction is not None:
        line = f"{verb} {name} {resolver.generic(*_MISSION_FOR)} {faction}"
    else:
        line = f"{verb} {name}"
    coins = moment.coins_delta.value
    if coins > _NO_COINS:
        line = f"{line}{_COIN_GAIN_OPEN}{fmt.coins(coins)}{_COIN_GAIN_CLOSE}"
    return line


def _templated_text(moment, renderer) -> str | None:
    """Return the moment's rendered taxonomy wording, else None.

    None covers every reason a template cannot speak for this moment: no
    renderer was supplied; the rule declared no template; the renderer could not
    satisfy it against this payload; it rendered to nothing. A row that rendered
    to whitespace is treated as no text at all, since an empty row tells the
    reader less than the label does.
    """
    if renderer is None:
        return None
    template = getattr(moment, _TEMPLATE_ATTR, _NO_TEMPLATE)
    if not template:
        return None
    rendered = renderer.render(template, dict(moment.detail))
    if rendered is None or not rendered.strip():
        return None
    return rendered.strip()


def row_text(moment, resolver, fmt, renderer=None) -> str:
    """Return the session-log text for a moment, enriched where the kind needs it.

    The formatter is passed for the few rows that surface an amount (a mission's
    Merc Coins reward); name-only rows ignore it. The renderer words every other
    row from the taxonomy template. Without one (or where a template cannot be
    satisfied) the row falls back to the moment's label.
    """
    kind = moment.kind.name
    if kind == _DEATH_KIND:
        return _death_text(moment, resolver, fmt)
    if kind in _VEHICLE_ROWS:
        return _vehicle_text(moment, resolver)
    if kind == _BOUNTY_KIND:
        return _bounty_text(moment, resolver)
    if kind == _MISSION_KIND:
        return _mission_text(moment, resolver, fmt)
    return _templated_text(moment, renderer) or moment.label
