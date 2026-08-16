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

__all__ = ["DOMAIN_ORDER", "build_domain_sections", "build_milestones"]

# Stat labels, resolved through the spec under these generic keys so the
# wording is configurable and never hardcoded as a domain string.
_JUMPS = ("flight.jumps", "Jumps")
_DISTANCE = ("flight.distance", "Distance")
_SETTLEMENTS = ("flight.settlements", "Settlements approached")
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
_MATERIAL_TRADES = ("trade.material_trades", "Material trades")
_REFINED = ("mining.refined", "Refined")
_COMPLETED = ("missions.completed", "Completed")
_REWARDS = ("missions.rewards", "Rewards")
_MERC_COINS = ("missions.merc_coins", "Merc Coins")
_CRAFTED = ("engineering.crafted", "Modification rolls")
_EXPERIMENTALS = ("engineering.experimentals", "Experimental effects")
_MODULES_BOUGHT = ("shipyard.modules_bought", "Modules bought")
_MODULE_SPEND = ("shipyard.module_spend", "Spent on modules")
_MODULES_SOLD = ("shipyard.modules_sold", "Modules sold")
_MODULE_EARNED = ("shipyard.module_earned", "Earned from modules")
_SHIPS_BOUGHT = ("shipyard.ships_bought", "Ships bought")
_SHIP_SPEND = ("shipyard.ship_spend", "Spent on ships")
_SHIPS_SOLD = ("shipyard.ships_sold", "Ships sold")
_SHIP_EARNED = ("shipyard.ship_earned", "Earned from ships")
_TRANSFERS = ("shipyard.transfers", "Ship transfers")
_TRANSFER_FEES = ("shipyard.transfer_fees", "Transfer fees")
_CARRIER_JUMPS = ("carrier.jumps", "Carrier jumps")
_CARRIER_DISTANCE = ("carrier.distance", "Distance")
# Qualifier shown beside the carrier distance when it covers only some of the
# jumps made, because the first jump of a session has no stated origin to
# measure from. It is held apart from the distance rather than formatted into
# it: the distance is a quantity that must not break across lines and this is
# prose that may. Joined into one unbreakable string the row overflowed its
# card and ran over the panel beside it.
_CARRIER_PARTIAL = (
    "carrier.distance_partial",
    "over {measured} of {total} jumps",
)
_SAMPLES = ("exobiology.samples", "Samples")
_SOLD = ("exobiology.sold", "Organic data sold")
_DEPLOYMENTS = ("srv.deployments", "Deployments")
_SLV_DEPLOYMENTS = ("slv.deployments", "Deployments")
_HANGARS_BOUGHT = ("slv.hangars_bought", "Hangars bought")
_HANGARS_SOLD = ("slv.hangars_sold", "Hangars sold")
_SLF_DEPLOYMENTS = ("slf.deployments", "Deployments")
_DISEMBARKS = ("on_foot.disembarks", "Disembarks")

# Milestone label keys, default text and icon for each notable kind, plus the
# MomentKind member names matched by string so no enum import is needed.
_PROMOTION_MILESTONE = ("promotion", "Earned a rank promotion.", "medal")
_LONG_JUMP_MILESTONE = ("long_jump", "Made an exceptionally long jump.", "star")
_BIG_PAYOUT_MILESTONE = ("big_payout", "Banked a major payout.", "money")
_PROMOTION_KIND = "PROMOTION"
_JUMP_KIND = "JUMP"


def _stat(
    resolver,
    label_key: tuple[str, str],
    value: str,
    qualifier: str | None = None,
) -> DomainStat:
    """Build one DomainStat with a resolved label and formatted value."""
    key, default = label_key
    return DomainStat(
        label=resolver.generic(key, default),
        value_display=value,
        qualifier=qualifier,
    )


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
        _stat(resolver, _SETTLEMENTS, fmt.integer(rollup.settlements)),
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
        _stat(resolver, _MATERIAL_TRADES, fmt.integer(rollup.material_trades)),
    )


def _mining_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _REFINED, fmt.integer(rollup.refined)),)


def _missions_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _COMPLETED, fmt.integer(rollup.completed)),
        _stat(resolver, _REWARDS, fmt.credits(rollup.rewards.value)),
        _stat(resolver, _MERC_COINS, fmt.coins(rollup.coin_rewards.value)),
    )


def _engineering_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    """Grade rolls and experimental effects, counted apart.

    Together they read as one figure and a session spent choosing effects
    looked like a session of heavy modification. The journal reports both as an
    EngineerCraft, which is why they were one count to begin with.
    """
    return (
        _stat(resolver, _CRAFTED, fmt.integer(rollup.crafted)),
        _stat(resolver, _EXPERIMENTALS, fmt.integer(rollup.experimentals)),
    )


def _shipyard_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    """Outfitting and shipyard trade: each side counted and priced separately."""
    return (
        _stat(resolver, _MODULES_BOUGHT, fmt.integer(rollup.modules_bought)),
        _stat(resolver, _MODULE_SPEND, fmt.credits(rollup.module_spend.value)),
        _stat(resolver, _MODULES_SOLD, fmt.integer(rollup.modules_sold)),
        _stat(resolver, _MODULE_EARNED, fmt.credits(rollup.module_earned.value)),
        _stat(resolver, _SHIPS_BOUGHT, fmt.integer(rollup.ships_bought)),
        _stat(resolver, _SHIP_SPEND, fmt.credits(rollup.ship_spend.value)),
        _stat(resolver, _SHIPS_SOLD, fmt.integer(rollup.ships_sold)),
        _stat(resolver, _SHIP_EARNED, fmt.credits(rollup.ship_earned.value)),
        _stat(resolver, _TRANSFERS, fmt.integer(rollup.transfers)),
        _stat(resolver, _TRANSFER_FEES, fmt.credits(rollup.transfer_fees.value)),
    )


def _carrier_distance(rollup, fmt, resolver) -> tuple[str, str | None]:
    """Return the carrier distance and its qualifier, if the total is short.

    A carrier jump states its destination but not how far it came, so a leg is
    only measurable between two stated positions and the first jump of a
    session has no stated origin. Where that leaves the total short, the display
    says which legs it covers rather than passing an incomplete figure off as
    the whole distance. The qualifier is returned separately from the distance
    so the renderer can wrap the prose without breaking the quantity.
    """
    distance = fmt.distance(rollup.distance_ly)
    if rollup.legs_measured >= rollup.legs_total:
        return distance, None
    template = resolver.generic(*_CARRIER_PARTIAL)
    qualifier = template.format(
        distance=distance,
        measured=fmt.integer(rollup.legs_measured),
        total=fmt.integer(rollup.legs_total),
    )
    return distance, qualifier


def _carrier_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    distance, qualifier = _carrier_distance(rollup, fmt, resolver)
    return (
        _stat(resolver, _CARRIER_JUMPS, fmt.integer(rollup.jumps)),
        _stat(resolver, _CARRIER_DISTANCE, distance, qualifier),
    )


def _exobiology_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _SAMPLES, fmt.integer(rollup.samples)),
        _stat(resolver, _SOLD, fmt.credits(rollup.sold.value)),
    )


def _srv_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _DEPLOYMENTS, fmt.integer(rollup.deployments)),)


def _slv_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (
        _stat(resolver, _SLV_DEPLOYMENTS, fmt.integer(rollup.deployments)),
        _stat(resolver, _HANGARS_BOUGHT, fmt.integer(rollup.hangars_bought)),
        _stat(resolver, _HANGARS_SOLD, fmt.integer(rollup.hangars_sold)),
    )


def _slf_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _SLF_DEPLOYMENTS, fmt.integer(rollup.deployments)),)


def _on_foot_stats(rollup, fmt, resolver) -> tuple[DomainStat, ...]:
    return (_stat(resolver, _DISEMBARKS, fmt.integer(rollup.disembarks)),)


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
    ("slv", "slv", _slv_stats),
    ("slf", "slf", _slf_stats),
    ("on_foot", "on_foot", _on_foot_stats),
    ("shipyard", "shipyard", _shipyard_stats),
)

# Display order of the activity-domain keys for the timeline categories, which
# is the section order. Every domain now carries a stat section: Shipyard used
# to be timeline-only and had to be appended by hand, which is why a session
# could sell fifty-six modules and report none of it.
DOMAIN_ORDER: tuple[str, ...] = tuple(key for _, key, _ in _BUILDERS)


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
