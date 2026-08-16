"""Debrief assembler: fold moments into the final SessionDebrief.

Given the isolated session's moments (already chronological) plus the
commander, window, rank progression and spec, this groups moments by domain
into the eleven rollups and sums the net credit change.

Levels are not derived here. The systems, the ship and the credit balance are
readings the journal states outright, so they are passed in and carried
through untouched. Deriving location from the moments was wrong in a way worth
recording: most location-bearing events produce no moment, so a session could
name four systems and still report none.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.carrier_distance import (
    STAR_POS_FIELD,
    leg_distances,
    star_positions,
)
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rank_delta import RankDelta
from o7debrief.domain.model.rollups import (
    ActivityRollup,
    CarrierRollup,
    CombatRollup,
    EngineeringRollup,
    ExobiologyRollup,
    ExplorationRollup,
    FlightRollup,
    MiningRollup,
    MissionRollup,
    OnFootRollup,
    ShipyardRollup,
    SlfRollup,
    SlvRollup,
    SrvRollup,
    TradeRollup,
)
from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.domain.rules.rollup_spec import RollupSpec
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow
from o7debrief.domain.value_objects.system_name import SystemName

__all__ = ["STAR_POS_FIELD", "STAR_SYSTEM_FIELD", "assemble"]

# Raw-event/detail field naming the star system a moment occurred in.
STAR_SYSTEM_FIELD = "StarSystem"
# Count contributed by a single moment occurrence.
_ONE_OCCURRENCE = 1
# Starting value for the distance accumulator.
_NO_MAGNITUDE = 0.0
# Canonical order in which control modes are reported.
_MODE_ORDER: tuple[ActivityMode, ...] = (
    ActivityMode.SHIP,
    ActivityMode.SRV,
    ActivityMode.SLV,
    ActivityMode.SLF,
    ActivityMode.ON_FOOT,
)


def _count(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> int:
    """Count moments of a given kind."""
    return sum(_ONE_OCCURRENCE for moment in moments if moment.kind == kind)


def _sum_magnitude(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> float:
    """Sum the magnitude of moments of a given kind."""
    return sum(
        (moment.magnitude for moment in moments if moment.kind == kind),
        _NO_MAGNITUDE,
    )


def _spend(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> Credits:
    """Sum a kind's priced outgoings from the spend channel.

    Spending is deliberately kept off the credits channel, which is income:
    routing a purchase through credits counts it as money banked.
    """
    total = Credits.zero()
    for moment in moments:
        if moment.kind == kind:
            total = total + moment.spend_delta
    return total


def _priced_change(moments: tuple[ConceptualMoment, ...]) -> int:
    """Return what the session's priced events came to, income less outgoings.

    This is emphatically NOT the change in the balance and must never be shown
    as one. It is the total of what the journal actually prices, which is only
    part of what moves a commander's money: measured across a real journal of
    117 logins, applying it to the opening balance matched the next stated
    balance on two of fifty-four active sessions and was out by a median of
    about eight million credits, with four sessions moving the balance while
    pricing nothing at all. So it answers "what did the events I can see come
    to", which is a real question; the balance is left to the readings.

    Signed, so not a Credits, which is non-negative by construction: a session
    that spent more than it earned is ordinary and must be reportable.
    """
    earned = sum(moment.credits_delta.value for moment in moments)
    spent = sum(moment.spend_delta.value for moment in moments)
    return earned - spent


def _sum_credits(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> Credits:
    """Sum the credit deltas of moments of a given kind."""
    total = Credits.zero()
    for moment in moments:
        if moment.kind == kind:
            total = total + moment.credits_delta
    return total


def _sum_coins(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> Credits:
    """Sum the Merc Coins deltas of moments of a given kind.

    A separate currency from credits, so it is totalled on its own and never
    contributes to the session net-credits figure.
    """
    total = Credits.zero()
    for moment in moments:
        if moment.kind == kind:
            total = total + moment.coins_delta
    return total


def _by_domain(
    moments: tuple[ConceptualMoment, ...], domain: ActivityDomain
) -> tuple[ConceptualMoment, ...]:
    """Return only the moments belonging to a domain."""
    return tuple(moment for moment in moments if moment.domain == domain)


def _flight(moments: tuple[ConceptualMoment, ...]) -> FlightRollup:
    return FlightRollup(
        jumps=_count(moments, MomentKind.JUMP),
        distance_ly=_sum_magnitude(moments, MomentKind.JUMP),
        settlements=_count(moments, MomentKind.SETTLEMENT_APPROACH),
    )


def _exploration(moments: tuple[ConceptualMoment, ...]) -> ExplorationRollup:
    return ExplorationRollup(
        bodies_scanned=_count(moments, MomentKind.SCAN_BODY),
        bodies_mapped=_count(moments, MomentKind.MAP_BODY),
        honks=_count(moments, MomentKind.HONK),
        data_sold=_sum_credits(moments, MomentKind.SELL_EXPLORATION),
    )


def _combat(moments: tuple[ConceptualMoment, ...]) -> CombatRollup:
    return CombatRollup(
        kills=_count(moments, MomentKind.BOUNTY) + _count(moments, MomentKind.BOND),
        bounties=_sum_credits(moments, MomentKind.BOUNTY),
        bonds=_sum_credits(moments, MomentKind.BOND),
    )


def _trade(moments: tuple[ConceptualMoment, ...]) -> TradeRollup:
    """Build the trade rollup.

    ``spent`` comes from the buy moment's magnitude rather than its credit
    delta. The journal states the cost outright in ``TotalCost``; even so, a buy
    deliberately carries no credit delta so that spending never inflates an
    income total. Routing the stated cost through the magnitude channel keeps
    that separation while ending a real defect: ten purchases used to report
    nought credits spent.

    ``material_trades`` is a bare count. A material-trader exchange is paid for
    in materials rather than credits and the journal states no price, so there
    is nothing to sum and nothing that belongs in either credit column.
    """
    return TradeRollup(
        buys=_count(moments, MomentKind.MARKET_BUY),
        sells=_count(moments, MomentKind.MARKET_SELL),
        spent=_spend(moments, MomentKind.MARKET_BUY),
        earned=_sum_credits(moments, MomentKind.MARKET_SELL),
        material_trades=_count(moments, MomentKind.MATERIAL_TRADE),
    )


def _mining(moments: tuple[ConceptualMoment, ...]) -> MiningRollup:
    return MiningRollup(refined=_count(moments, MomentKind.REFINE))


def _missions(moments: tuple[ConceptualMoment, ...]) -> MissionRollup:
    return MissionRollup(
        completed=_count(moments, MomentKind.MISSION_COMPLETE),
        rewards=_sum_credits(moments, MomentKind.MISSION_COMPLETE),
        coin_rewards=_sum_coins(moments, MomentKind.MISSION_COMPLETE),
    )


def _engineering(moments: tuple[ConceptualMoment, ...]) -> EngineeringRollup:
    return EngineeringRollup(
        crafted=_count(moments, MomentKind.ENGINEER_CRAFT),
        experimentals=_count(moments, MomentKind.ENGINEER_EXPERIMENTAL),
    )


def _shipyard(moments: tuple[ConceptualMoment, ...]) -> ShipyardRollup:
    """Fold the outfitting and shipyard purchases and sales.

    Each side keeps its own count and its own sum: a session that replaced its
    outfitting spent on the new modules and took money back for the old, which
    a single net figure would report as though nothing had happened.

    Spending rides the magnitude channel and income the credits channel, which
    is why the two sides read different fields here. Credits is the income
    channel: a purchase routed through it counts as money banked. One big
    enough raised the major-payout milestone for buying a drive.
    """
    return ShipyardRollup(
        modules_bought=_count(moments, MomentKind.MODULE_BUY),
        modules_sold=_count(moments, MomentKind.MODULE_SELL),
        module_spend=_spend(moments, MomentKind.MODULE_BUY),
        module_earned=_sum_credits(moments, MomentKind.MODULE_SELL),
        ships_bought=_count(moments, MomentKind.SHIP_PURCHASE),
        ships_sold=_count(moments, MomentKind.SHIP_SALE),
        ship_spend=_spend(moments, MomentKind.SHIP_PURCHASE),
        ship_earned=_sum_credits(moments, MomentKind.SHIP_SALE),
        transfers=_count(moments, MomentKind.SHIP_TRANSFER),
        transfer_fees=_spend(moments, MomentKind.SHIP_TRANSFER),
    )


def _carrier(moments: tuple[ConceptualMoment, ...]) -> CarrierRollup:
    jumps = _count(moments, MomentKind.CARRIER_JUMP)
    positions = star_positions(moments, MomentKind.CARRIER_JUMP)
    distance, measured = leg_distances(positions)
    # Every jump is a leg flown, so the total is the jump count. Only the legs
    # between two stated positions can be measured, which is why the first jump
    # of a session is always short of the total.
    return CarrierRollup(
        jumps=jumps,
        distance_ly=distance,
        legs_measured=measured,
        legs_total=jumps,
    )


def _exobiology(moments: tuple[ConceptualMoment, ...]) -> ExobiologyRollup:
    return ExobiologyRollup(
        samples=_count(moments, MomentKind.EXOBIO_SAMPLE),
        sold=_sum_credits(moments, MomentKind.EXOBIO_SELL),
    )


def _srv(moments: tuple[ConceptualMoment, ...]) -> SrvRollup:
    return SrvRollup(deployments=_count(moments, MomentKind.SRV_DEPLOY))


def _slv(moments: tuple[ConceptualMoment, ...]) -> SlvRollup:
    return SlvRollup(
        deployments=_count(moments, MomentKind.SLV_DEPLOY),
        hangars_bought=_count(moments, MomentKind.VESSEL_HANGAR_BUY),
        hangars_sold=_count(moments, MomentKind.VESSEL_HANGAR_SELL),
    )


def _slf(moments: tuple[ConceptualMoment, ...]) -> SlfRollup:
    return SlfRollup(deployments=_count(moments, MomentKind.SLF_DEPLOY))


def _on_foot(moments: tuple[ConceptualMoment, ...]) -> OnFootRollup:
    return OnFootRollup(disembarks=_count(moments, MomentKind.DISEMBARK))


def _modes_used(moments: tuple[ConceptualMoment, ...]) -> tuple[ActivityMode, ...]:
    """Return the distinct control modes across moments in canonical order."""
    present = {moment.mode for moment in moments}
    return tuple(mode for mode in _MODE_ORDER if mode in present)


def _activity(moments: tuple[ConceptualMoment, ...]) -> ActivityRollup:
    """Build the ActivityRollup, including a domain only when it has moments."""

    def rollup(domain: ActivityDomain, builder):
        domain_moments = _by_domain(moments, domain)
        return builder(domain_moments) if domain_moments else None

    return ActivityRollup(
        flight=rollup(ActivityDomain.TRAVEL, _flight),
        exploration=rollup(ActivityDomain.EXPLORATION, _exploration),
        combat=rollup(ActivityDomain.COMBAT, _combat),
        trade=rollup(ActivityDomain.TRADE, _trade),
        mining=rollup(ActivityDomain.MINING, _mining),
        missions=rollup(ActivityDomain.MISSIONS, _missions),
        engineering=rollup(ActivityDomain.ENGINEERING, _engineering),
        carrier=rollup(ActivityDomain.CARRIER, _carrier),
        exobiology=rollup(ActivityDomain.EXOBIOLOGY, _exobiology),
        srv=rollup(ActivityDomain.SRV, _srv),
        slv=rollup(ActivityDomain.SLV, _slv),
        slf=rollup(ActivityDomain.SLF, _slf),
        on_foot=rollup(ActivityDomain.ON_FOOT, _on_foot),
        shipyard=rollup(ActivityDomain.SHIPYARD, _shipyard),
        modes_used=_modes_used(moments),
    )


def assemble(
    commander: CommanderId,
    window: SessionWindow,
    moments: tuple[ConceptualMoment, ...],
    rank_progression: tuple[RankDelta, ...],
    spec: RollupSpec,
    ship: str = "",
    ship_name: str = "",
    credits_balance: Credits | None = None,
    credits_balance_at: EventTime | None = None,
    start_system: SystemName | None = None,
    end_system: SystemName | None = None,
    systems_visited: int | None = None,
    net_credits_delta: int | None = None,
) -> SessionDebrief:
    """Fold the session's moments into a complete SessionDebrief.

    ``credits_balance``, ``net_credits_delta``, the systems and the ship are
    readings rather than totals the domain computes: each is a level the
    journal states outright, so they are passed in and carried through
    untouched. None means no reading was seen and must stay distinguishable
    from a balance of zero, a change of nothing, a count of no systems or a
    commander who is nowhere.

    The net change used to be summed from the moments, which counted income
    only and so reported a session that lost twenty million credits as a gain
    of two hundred thousand. It is now the difference between the balances the
    journal states at each end of the session, which is the only figure that is
    actually true: it captures rebuys, outfitting and every other outgoing the
    moment rules deliberately do not price.
    """
    return SessionDebrief(
        commander=commander,
        window=window,
        start_system=start_system,
        end_system=end_system,
        net_credits_delta=net_credits_delta,
        moments=moments,
        activity=_activity(moments),
        rank_progression=rank_progression,
        config_schema_version=spec.schema_version,
        ship=ship,
        ship_name=ship_name,
        credits_balance=credits_balance,
        credits_balance_at=credits_balance_at,
        priced_change=_priced_change(moments),
        systems_visited=systems_visited,
    )
