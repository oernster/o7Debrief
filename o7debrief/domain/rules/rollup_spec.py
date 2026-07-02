"""Data-only rollup specification: how raw events become conceptual moments.

A ``RollupSpec`` is a pure configuration object (no behaviour beyond
lookups). It is supplied by an outer layer so the aggregation functions
stay free of hardcoded event mappings, field names and thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)

__all__ = ["MomentRule", "ThresholdSet", "RollupSpec"]


@dataclass(frozen=True, slots=True)
class MomentRule:
    """Maps one journal event type to a classified moment.

    ``magnitude_field`` and ``credits_field`` name the raw-event fields to
    read for the moment's magnitude and scalar credit delta; either may be
    ``None`` when the event carries no such value.

    Some events spread their credit value across a nested array rather than a
    single key (an exobiology sale lists each sample under ``BioData``). For
    those, ``credits_array_field`` names the array and ``credits_item_fields``
    names the per-entry numeric keys to sum. When ``credits_array_field`` is
    set it takes precedence over ``credits_field``.

    Some journal events are shared across many subjects and only become the
    conceptual moment when one payload field carries a distinguishing token.
    A ``ModuleBuy`` becomes a Vessel Hangar purchase only when its bought-item
    name contains ``fighterbay``; a ``LaunchFighter`` is a Nomad deployment
    only when its loadout is one of the Nomad variants. For those, ``where_field``
    names the payload key to inspect and ``where_contains`` is a tuple of
    case-insensitive substrings, any one of which appearing in that field
    satisfies the filter. When ``where_field`` is unset or ``where_contains`` is
    empty the rule matches every occurrence.
    """

    event_type: str
    kind: MomentKind
    domain: ActivityDomain
    mode: ActivityMode
    magnitude_field: str | None
    credits_field: str | None
    credits_array_field: str | None = None
    credits_item_fields: tuple[str, ...] = ()
    where_field: str | None = None
    where_contains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ThresholdSet:
    """Named thresholds that distinguish notable moments from routine ones."""

    long_jump_ly: float
    big_payout_credits: int
    high_value_exobio_credits: int


@dataclass(frozen=True, slots=True)
class RollupSpec:
    """The full event-to-moment specification for one schema version."""

    schema_version: str
    rules: tuple[MomentRule, ...]
    thresholds: ThresholdSet
    labels: tuple[tuple[str, str], ...]

    def rule_for(self, event_type: str) -> MomentRule | None:
        """Return the first rule matching ``event_type``, or ``None`` if absent."""
        for rule in self.rules:
            if rule.event_type == event_type:
                return rule
        return None

    def rules_for(self, event_type: str) -> tuple[MomentRule, ...]:
        """Return all rules matching ``event_type``, in declaration order.

        A single journal event can map to different moments depending on a
        payload field (a ``LaunchFighter`` is a Nomad deployment or a fighter
        deployment by its loadout). The caller tries these in order and uses the
        first whose where-filter matches, so ordering in the taxonomy decides
        precedence.
        """
        return tuple(rule for rule in self.rules if rule.event_type == event_type)

    def label_for(self, key: str, default: str) -> str:
        """Return the configured label for ``key``, or ``default``."""
        for label_key, label_value in self.labels:
            if label_key == key:
                return label_value
        return default
