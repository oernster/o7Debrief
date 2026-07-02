"""Moment factory: turn matching raw events into conceptual moments.

Each raw event whose type has a ``MomentRule`` in the spec becomes one
``ConceptualMoment``. The moment's control mode comes from the phase tracker
(aligned by index), its magnitude and credit delta are read from the
rule's named fields, and its label is resolved through the spec (falling
back to the event type so a moment is never unlabelled).
"""

from __future__ import annotations

from o7debrief.domain.aggregation.phase_tracker import (
    DOCK_SRV,
    LAUNCH_FIGHTER,
    SRV_DESTROYED,
    SlvLaunchRule,
    mode_at_each,
)
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import MomentRule, RollupSpec
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import ActivityMode, MomentKind

__all__ = ["build_moments", "SELF_DESTRUCT_MARK", "VESSEL_TYPE_MARK"]

# Magnitude used when a rule names no magnitude field or the field is absent.
_DEFAULT_MAGNITUDE = 0

# The journal event fired when the commander triggers a self-destruct. It is a
# signal rather than a moment of its own: it marks the death that follows as
# self-inflicted so the report can name the cause. The paired ``Died`` carries
# no killer, so without this the death would read as a bare loss.
_SELF_DESTRUCT_EVENT = "SelfDestruct"
# Synthetic detail key added to a self-destruct death moment. It is not a real
# journal field; the presenter reads it to render the death cause. The same
# literal is mirrored in the presenter, as with other shared field names.
SELF_DESTRUCT_MARK = "SelfDestruct"

# Ship-launched-vehicle moment kinds that name a vehicle type in the report,
# grouped by how that type is found. A vessel dock/loss names it directly
# (SRVType_Localised); a vessel deploy and a fighter dock/loss carry only an ID
# and recover the type by matching it; a fighter deploy names it from its own
# loadout. Nomad and fighter both arrive on LaunchFighter.
_SLV_NAMED_KINDS = frozenset(
    {MomentKind.SLV_DOCK, MomentKind.SLV_DESTROYED}
)
_SLF_CORRELATED_KINDS = frozenset(
    {MomentKind.SLF_DOCK, MomentKind.SLF_DESTROYED}
)
_VEHICLE_KINDS = (
    _SLV_NAMED_KINDS
    | _SLF_CORRELATED_KINDS
    | {MomentKind.SLV_DEPLOY, MomentKind.SLF_DEPLOY}
)
# Journal fields naming a vehicle type and the vehicle instance.
_SRV_TYPE_FIELD = "SRVType_Localised"
_LOADOUT_FIELD = "Loadout"
_VEHICLE_ID_FIELD = "ID"
# Synthetic detail key carrying the resolved vehicle type to the presenter.
VESSEL_TYPE_MARK = "VesselType"


def _magnitude_from(event: RawEvent, rule: MomentRule) -> int:
    """Read the integer magnitude named by the rule, or the default."""
    if rule.magnitude_field is None:
        return _DEFAULT_MAGNITUDE
    raw = event.get(rule.magnitude_field)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    return _DEFAULT_MAGNITUDE


def _credits_from(event: RawEvent, rule: MomentRule) -> Credits:
    """Read the credit delta named by the rule, or zero.

    A rule names either a single scalar credit field or, for events whose
    value is spread across a nested array, an array field plus the per-entry
    fields to sum. The array form takes precedence when present.
    """
    if rule.credits_array_field is not None:
        return _credits_from_array(event, rule)
    if rule.credits_field is None:
        return Credits.zero()
    raw = event.get(rule.credits_field)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return Credits(raw)
    return Credits.zero()


def _credits_from_array(event: RawEvent, rule: MomentRule) -> Credits:
    """Sum the rule's named item fields across its credit array, or zero.

    The array field and the item fields both come from the rule (taxonomy),
    so no journal key is hardcoded here. Entries that are not objects, and
    item values that are not plain integers, are ignored rather than guessed.
    """
    entries = event.get(rule.credits_array_field)
    if not isinstance(entries, (list, tuple)):
        return Credits.zero()
    total = Credits.zero()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for item_field in rule.credits_item_fields:
            raw = entry.get(item_field)
            if isinstance(raw, int) and not isinstance(raw, bool):
                total = total + Credits(raw)
    return total


def _matches_filter(event: RawEvent, rule: MomentRule) -> bool:
    """Return whether the event satisfies the rule's optional where-filter.

    When the rule names a ``where_field`` and one or more ``where_contains``
    tokens, the event matches only if that field is a string containing at
    least one token (case-insensitive). A rule without a complete filter
    matches every event.
    """
    if rule.where_field is None or not rule.where_contains:
        return True
    raw = event.get(rule.where_field)
    if not isinstance(raw, str):
        return False
    lowered = raw.lower()
    return any(token.lower() in lowered for token in rule.where_contains)


def _slv_launch_from(spec: RollupSpec) -> SlvLaunchRule | None:
    """Derive the Nomad-launch discriminator from the SLV deployment rule.

    The phase tracker needs to know which shared launch event, field and
    loadout tokens mean the commander entered the ship-launched vessel. That
    lives in the taxonomy as the ``slv_deploy`` moment rule's where-filter, so
    it is read from there rather than hardcoded here.
    """
    for rule in spec.rules:
        if (
            rule.kind is MomentKind.SLV_DEPLOY
            and rule.where_field is not None
            and rule.where_contains
        ):
            return SlvLaunchRule(
                event_type=rule.event_type,
                field=rule.where_field,
                tokens=rule.where_contains,
            )
    return None


def _is_nomad_launch(event: RawEvent, slv_launch: SlvLaunchRule) -> bool:
    """Return whether a LaunchFighter is the Nomad (vs a genuine fighter)."""
    value = event.get(slv_launch.field)
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(token.lower() in lowered for token in slv_launch.tokens)


def _titlecase(value: object) -> str | None:
    """Return a loadout string title-cased for display, or None if blank."""
    if isinstance(value, str) and value.strip():
        return value.title()
    return None


def _type_maps(
    events: tuple[RawEvent, ...], slv_launch: SlvLaunchRule | None
) -> tuple[dict[object, str], dict[object, str]]:
    """Build the two ID-to-type maps used to name a vehicle by correlation.

    ``srv_type_by_id`` comes from the vessel dock/loss events (SRVType_Localised)
    and names a vessel deployment, which carries only an ID. ``fighter_loadout``
    comes from genuine (non-Nomad) fighter launches and names a fighter dock or
    loss, which likewise carry only an ID.
    """
    srv_type_by_id: dict[object, str] = {}
    fighter_loadout: dict[object, str] = {}
    for event in events:
        if event.event_type in (DOCK_SRV, SRV_DESTROYED):
            name = event.get(_SRV_TYPE_FIELD)
            vehicle_id = event.get(_VEHICLE_ID_FIELD)
            if isinstance(name, str) and name and vehicle_id is not None:
                srv_type_by_id[vehicle_id] = name
        elif event.event_type == LAUNCH_FIGHTER:
            if slv_launch is not None and _is_nomad_launch(event, slv_launch):
                continue
            loadout = event.get(_LOADOUT_FIELD)
            vehicle_id = event.get(_VEHICLE_ID_FIELD)
            if isinstance(loadout, str) and loadout and vehicle_id is not None:
                fighter_loadout[vehicle_id] = loadout
    return srv_type_by_id, fighter_loadout


def _vehicle_type_for(
    event: RawEvent,
    kind: MomentKind,
    srv_type_by_id: dict[object, str],
    fighter_loadout: dict[object, str],
) -> str | None:
    """Return the vehicle type named on a ship-launched-vehicle moment, or None.

    A vessel dock/loss names it directly; a vessel deploy recovers it by ID from
    the dock/loss; a fighter deploy names it from its own loadout; a fighter
    dock/loss recovers the loadout by ID from the launch.
    """
    if kind is MomentKind.SLV_DEPLOY:
        return srv_type_by_id.get(event.get(_VEHICLE_ID_FIELD))
    if kind in _SLV_NAMED_KINDS:
        name = event.get(_SRV_TYPE_FIELD)
        return name if isinstance(name, str) and name else None
    if kind is MomentKind.SLF_DEPLOY:
        return _titlecase(event.get(_LOADOUT_FIELD))
    return _titlecase(fighter_loadout.get(event.get(_VEHICLE_ID_FIELD)))


def _moment_from(
    event: RawEvent,
    rule: MomentRule,
    mode: ActivityMode,
    spec: RollupSpec,
    extra_detail: tuple[tuple[str, object], ...] = (),
) -> ConceptualMoment:
    """Construct a single moment from an event and its matching rule.

    ``extra_detail`` appends derived (non-journal) pairs to the moment's detail,
    used to carry a self-destruct marker onto a death the report must explain.
    """
    label = spec.label_for(event.event_type, event.event_type)
    return ConceptualMoment(
        kind=rule.kind,
        domain=rule.domain,
        mode=mode,
        occurred_at=event.event_time,
        label=label,
        magnitude=_magnitude_from(event, rule),
        credits_delta=_credits_from(event, rule),
        detail=event.fields + extra_detail,
    )


def _first_matching_rule(event: RawEvent, spec: RollupSpec) -> MomentRule | None:
    """Return the first rule for this event whose where-filter matches.

    A shared event (LaunchFighter) has several candidate rules; the first whose
    filter passes wins, so taxonomy order decides precedence (Nomad before the
    generic fighter). Returns None when no candidate matches.
    """
    for rule in spec.rules_for(event.event_type):
        if _matches_filter(event, rule):
            return rule
    return None


def build_moments(
    events: tuple[RawEvent, ...], spec: RollupSpec
) -> tuple[ConceptualMoment, ...]:
    """Map every event with a matching rule to a ConceptualMoment.

    Events without a matching rule are skipped. The control mode for each
    moment is taken from the phase tracker, aligned by the event's index. A
    ``SelfDestruct`` event is not itself a moment; it marks the next death as
    self-inflicted so the report can name the cause. Ship-launched-vehicle
    moments are tagged with the vehicle type for the report.
    """
    slv_launch = _slv_launch_from(spec)
    modes = mode_at_each(events, slv_launch)
    srv_type_by_id, fighter_loadout = _type_maps(events, slv_launch)
    moments: list[ConceptualMoment] = []
    self_destruct_pending = False
    for index, event in enumerate(events):
        if event.event_type == _SELF_DESTRUCT_EVENT:
            self_destruct_pending = True
            continue
        rule = _first_matching_rule(event, spec)
        if rule is None:
            continue
        extra: tuple[tuple[str, object], ...] = ()
        if rule.kind is MomentKind.DEATH and self_destruct_pending:
            extra = extra + ((SELF_DESTRUCT_MARK, True),)
            self_destruct_pending = False
        if rule.kind in _VEHICLE_KINDS:
            vehicle = _vehicle_type_for(
                event, rule.kind, srv_type_by_id, fighter_loadout
            )
            if vehicle is not None:
                extra = extra + ((VESSEL_TYPE_MARK, vehicle),)
        moments.append(_moment_from(event, rule, modes[index], spec, extra))
    return tuple(moments)
