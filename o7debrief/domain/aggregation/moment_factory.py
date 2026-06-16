"""Moment factory: turn matching raw events into conceptual moments.

Each raw event whose type has a ``MomentRule`` in the spec becomes one
``ConceptualMoment``. The moment's control mode comes from the phase tracker
(aligned by index), its magnitude and credit delta are read from the
rule's named fields, and its label is resolved through the spec (falling
back to the event type so a moment is never unlabelled).
"""

from __future__ import annotations

from o7debrief.domain.aggregation.phase_tracker import mode_at_each
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import MomentRule, RollupSpec
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import ActivityMode

__all__ = ["build_moments"]

# Magnitude used when a rule names no magnitude field or the field is absent.
_DEFAULT_MAGNITUDE = 0


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


def _moment_from(
    event: RawEvent, rule: MomentRule, mode: ActivityMode, spec: RollupSpec
) -> ConceptualMoment:
    """Construct a single moment from an event and its matching rule."""
    label = spec.label_for(event.event_type, event.event_type)
    return ConceptualMoment(
        kind=rule.kind,
        domain=rule.domain,
        mode=mode,
        occurred_at=event.event_time,
        label=label,
        magnitude=_magnitude_from(event, rule),
        credits_delta=_credits_from(event, rule),
        detail=event.fields,
    )


def build_moments(
    events: tuple[RawEvent, ...], spec: RollupSpec
) -> tuple[ConceptualMoment, ...]:
    """Map every event with a matching rule to a ConceptualMoment.

    Events without a matching rule are skipped. The control mode for each
    moment is taken from the phase tracker, aligned by the event's index.
    """
    modes = mode_at_each(events)
    moments: list[ConceptualMoment] = []
    for index, event in enumerate(events):
        rule = spec.rule_for(event.event_type)
        if rule is None:
            continue
        moments.append(_moment_from(event, rule, modes[index], spec))
    return tuple(moments)
