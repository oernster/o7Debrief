"""Debrief assembler: fold moments into the final SessionDebrief.

Given the isolated session's moments (already chronological) plus the
commander, window, rank progression and spec, this groups moments by domain
into the eleven rollups, sums the net credit change, and reads the start
and end systems from the first and last location-bearing moments.
"""

from __future__ import annotations

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
from o7debrief.domain.value_objects.session_window import SessionWindow
from o7debrief.domain.value_objects.system_name import SystemName

__all__ = ["assemble", "STAR_SYSTEM_FIELD"]

# Raw-event/detail field naming the star system a moment occurred in.
STAR_SYSTEM_FIELD = "StarSystem"
# Count contributed by a single moment occurrence.
_ONE_OCCURRENCE = 1
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


def _sum_magnitude(moments: tuple[ConceptualMoment, ...], kind: MomentKind) -> int:
    """Sum the magnitude of moments of a given kind."""
    return sum(moment.magnitude for moment in moments if moment.kind == kind)


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
    return TradeRollup(
        buys=_count(moments, MomentKind.MARKET_BUY),
        sells=_count(moments, MomentKind.MARKET_SELL),
        spent=_sum_credits(moments, MomentKind.MARKET_BUY),
        earned=_sum_credits(moments, MomentKind.MARKET_SELL),
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
    return EngineeringRollup(crafted=_count(moments, MomentKind.ENGINEER_CRAFT))


def _carrier(moments: tuple[ConceptualMoment, ...]) -> CarrierRollup:
    return CarrierRollup(jumps=_count(moments, MomentKind.CARRIER_JUMP))


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
    return OnFootRollup(
        disembarks=_count(moments, MomentKind.DISEMBARK),
        settlements=_count(moments, MomentKind.SETTLEMENT_VISIT),
    )


def _net_credits(moments: tuple[ConceptualMoment, ...]) -> Credits:
    """Sum the credit delta across every moment."""
    total = Credits.zero()
    for moment in moments:
        total = total + moment.credits_delta
    return total


def _system_at(moment: ConceptualMoment) -> SystemName | None:
    """Return the star system named in a moment's detail, if any."""
    for key, value in moment.detail:
        if key == STAR_SYSTEM_FIELD and isinstance(value, str) and value.strip():
            return SystemName(value)
    return None


def _endpoints(
    moments: tuple[ConceptualMoment, ...],
) -> tuple[SystemName | None, SystemName | None]:
    """Return the first and last location-bearing systems in order."""
    located = tuple(
        system
        for system in (_system_at(moment) for moment in moments)
        if system is not None
    )
    if not located:
        return None, None
    return located[0], located[-_ONE_OCCURRENCE]


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
) -> SessionDebrief:
    """Fold the session's moments into a complete SessionDebrief."""
    start_system, end_system = _endpoints(moments)
    return SessionDebrief(
        commander=commander,
        window=window,
        start_system=start_system,
        end_system=end_system,
        net_credits_delta=_net_credits(moments),
        moments=moments,
        activity=_activity(moments),
        rank_progression=rank_progression,
        config_schema_version=spec.schema_version,
        ship=ship,
        ship_name=ship_name,
    )
