"""Domain-section and milestone builders for the presenter.

Each builder turns one domain rollup into a formatted ``DomainSection`` with
its labelled stats. The milestone builder scans the moments for the notable
moments worth surfacing (promotions, big payouts, long jumps), comparing
against the spec's thresholds so no threshold literal lives in code.

This module belongs to the application layer and imports only application
symbols. It reads the domain rollup, moment and spec objects by attribute
(duck typing) and refers to their types as forward references, so it never
imports the domain layer. Moment kinds are matched by their member name string
to avoid importing the MomentKind enum.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import (
    DomainSection,
    DomainStat,
    Milestone,
)

__all__ = ["build_domain_sections", "build_milestones", "DOMAIN_ORDER"]

# Stat labels, resolved through the spec under these generic keys so the
# wording is configurable and never hardcoded as a domain string.
_JUMPS = ("flight.jumps", "Jumps")
_DISTANCE = ("flight.distance", "Distance")
_SCANNED = ("exploration.scanned", "Bodies scanned")
_MAPPED = ("exploration.mapped", "Bodies mapped")
_HONKS = ("exploration.honks", "Discovery scans")
_DATA_SOLD = ("exploration.data_sold", "Data sold")
_KILLS = ("combat.kills", "Kills")
_BOUNTIES = ("combat.bounties", "Bounties")
_BONDS = ("combat.bonds", "Combat bonds")
_BUYS = ("trade.buys", "Buys")
_SELLS = ("trade.sells", "Sells")
_SPENT = ("trade.spent", "Spent")
_EARNED = ("trade.earned", "Earned")
_REFINED = ("mining.refined", "Refined")
_COMPLETED = ("missions.completed", "Completed")
_REWARDS = ("missions.rewards", "Rewards")
_CRAFTED = ("engineering.crafted", "Modifications")
_CARRIER_JUMPS = ("carrier.jumps", "Carrier jumps")
_SAMPLES = ("exobiology.samples", "Samples")
_SOLD = ("exobiology.sold", "Organic data sold")
_DEPLOYMENTS = ("srv.deployments", "Deployments")
_DISEMBARKS = ("on_foot.disembarks", "Disembarks")
_SETTLEMENTS = ("on_foot.settlements", "Settlements")

# Milestone label keys, default text and icon for each notable kind, plus the
# MomentKind member names matched by string so no enum import is needed.
_PROMOTION_MILESTONE = ("promotion", "Earned a rank promotion.", "medal")
_LONG_JUMP_MILESTONE = ("long_jump", "Made an exceptionally long jump.", "star")
_BIG_PAYOUT_MILESTONE = ("big_payout", "Banked a major payout.", "money")
_PROMOTION_KIND = "PROMOTION"
_JUMP_KIND = "JUMP"


def _stat(resolver, label_key: tuple[str, str], value: str) -> DomainStat:
    """Build one DomainStat with a resolved label and formatted value."""
    key, default = label_key
    return DomainStat(label=resolver.generic(key, default), value_display=value)


def _section(resolver, key: str, stats: tuple[DomainStat, ...]) -> DomainSection:
    """Build a DomainSection with resolved title, icon and optional note."""
    return DomainSection(
        key=key,
        title=resolver.domain_title(key),
        icon=resolver.domain_icon(key),
        stats=stats,
        note=resolver.domain_note(key),
    )


def _flight_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _JUMPS, fmt.integer(rollup.jumps)),
        _stat(resolver, _DISTANCE, fmt.distance(rollup.distance_ly)),
    )


def _exploration_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _SCANNED, fmt.integer(rollup.bodies_scanned)),
        _stat(resolver, _MAPPED, fmt.integer(rollup.bodies_mapped)),
        _stat(resolver, _HONKS, fmt.integer(rollup.honks)),
        _stat(resolver, _DATA_SOLD, fmt.credits(rollup.data_sold.value)),
    )


def _combat_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _KILLS, fmt.integer(rollup.kills)),
        _stat(resolver, _BOUNTIES, fmt.credits(rollup.bounties.value)),
        _stat(resolver, _BONDS, fmt.credits(rollup.bonds.value)),
    )


def _trade_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _BUYS, fmt.integer(rollup.buys)),
        _stat(resolver, _SELLS, fmt.integer(rollup.sells)),
        _stat(resolver, _SPENT, fmt.credits(rollup.spent.value)),
        _stat(resolver, _EARNED, fmt.credits(rollup.earned.value)),
    )


def _mining_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _REFINED, fmt.integer(rollup.refined)),)


def _missions_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _COMPLETED, fmt.integer(rollup.completed)),
        _stat(resolver, _REWARDS, fmt.credits(rollup.rewards.value)),
    )


def _engineering_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _CRAFTED, fmt.integer(rollup.crafted)),)


def _carrier_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _CARRIER_JUMPS, fmt.integer(rollup.jumps)),)


def _exobiology_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _SAMPLES, fmt.integer(rollup.samples)),
        _stat(resolver, _SOLD, fmt.credits(rollup.sold.value)),
    )


def _srv_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _DEPLOYMENTS, fmt.integer(rollup.deployments)),)


def _on_foot_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _DISEMBARKS, fmt.integer(rollup.disembarks)),
        _stat(resolver, _SETTLEMENTS, fmt.integer(rollup.settlements)),
    )


# Pairing of each ActivityRollup attribute to its domain key and stat builder.
# Iterated in this canonical order so sections appear consistently. The key
# strings match the ActivityDomain member names in lower case.
_BUILDERS: tuple[tuple[str, str, object], ...] = (
    ("flight", "travel", _flight_stats),
    ("exploration", "exploration", _exploration_stats),
    ("combat", "combat", _combat_stats),
    ("trade", "trade", _trade_stats),
    ("mining", "mining", _mining_stats),
    ("missions", "missions", _missions_stats),
    ("engineering", "engineering", _engineering_stats),
    ("carrier", "carrier", _carrier_stats),
    ("exobiology", "exobiology", _exobiology_stats),
    ("srv", "srv", _srv_stats),
    ("on_foot", "on_foot", _on_foot_stats),
)

# Display order of the activity-domain keys for the timeline categories. Stat
# sections come from _BUILDERS; Shipyard is a timeline-only domain (ship swaps
# and purchases are logged as records with no rollup stat section), so it is
# appended here without a _BUILDERS entry.
_SHIPYARD_KEY = "shipyard"
DOMAIN_ORDER: tuple[str, ...] = tuple(key for _, key, _ in _BUILDERS) + (_SHIPYARD_KEY,)


def build_domain_sections(activity, fmt, resolver) -> tuple[DomainSection, ...]:
    """Build a section for each rollup present on the activity, in order."""
    sections: list[DomainSection] = []
    for attr, key, builder in _BUILDERS:
        rollup = getattr(activity, attr)
        if rollup is None:
            continue
        stats = builder(rollup, fmt, resolver)
        sections.append(_section(resolver, key, stats))
    return tuple(sections)


def _milestone(resolver, spec, parts: tuple[str, str, str]) -> Milestone:
    """Build one Milestone with a resolved icon and text."""
    key, default_text, default_icon = parts
    icon = resolver.milestone_icon(key, default_icon)
    text = spec.label_for(f"milestone.{key}.text", default_text)
    return Milestone(icon=icon, text=text)


def build_milestones(moments, spec, resolver) -> tuple[Milestone, ...]:
    """Surface notable moments: promotions, big payouts and long jumps.

    Thresholds come from the spec so the notability rule has no hardcoded
    numbers. Each kind contributes at most one milestone, in a fixed order.
    Moment kinds are matched by member-name string to avoid a domain import.
    """
    milestones: list[Milestone] = []
    if any(moment.kind.name == _PROMOTION_KIND for moment in moments):
        milestones.append(_milestone(resolver, spec, _PROMOTION_MILESTONE))
    payout_floor = spec.thresholds.big_payout_credits
    if any(moment.credits_delta.value >= payout_floor for moment in moments):
        milestones.append(_milestone(resolver, spec, _BIG_PAYOUT_MILESTONE))
    long_jump = spec.thresholds.long_jump_ly
    if any(
        moment.kind.name == _JUMP_KIND and moment.magnitude >= long_jump
        for moment in moments
    ):
        milestones.append(_milestone(resolver, spec, _LONG_JUMP_MILESTONE))
    return tuple(milestones)
