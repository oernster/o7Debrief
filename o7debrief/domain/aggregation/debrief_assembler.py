"""Debrief assembler: fold beats into the final SessionDebrief.

Given the isolated session's beats (already chronological) plus the
commander, window, rank progression and spec, this groups beats by domain
into the eleven rollups, sums the net credit change, and reads the start
and end systems from the first and last location-bearing beats.
"""

from __future__ import annotations

from o7debrief.domain.model.conceptual_beat import ConceptualBeat
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
    BeatKind,
)
from o7debrief.domain.value_objects.session_window import SessionWindow
from o7debrief.domain.value_objects.system_name import SystemName

__all__ = ["assemble", "STAR_SYSTEM_FIELD"]

# Raw-event/detail field naming the star system a beat occurred in.
STAR_SYSTEM_FIELD = "StarSystem"
# Count contributed by a single beat occurrence.
_ONE_OCCURRENCE = 1
# Canonical order in which control modes are reported.
_MODE_ORDER: tuple[ActivityMode, ...] = (
    ActivityMode.SHIP,
    ActivityMode.SRV,
    ActivityMode.ON_FOOT,
)


def _count(beats: tuple[ConceptualBeat, ...], kind: BeatKind) -> int:
    """Count beats of a given kind."""
    return sum(_ONE_OCCURRENCE for beat in beats if beat.kind == kind)


def _sum_magnitude(beats: tuple[ConceptualBeat, ...], kind: BeatKind) -> int:
    """Sum the magnitude of beats of a given kind."""
    return sum(beat.magnitude for beat in beats if beat.kind == kind)


def _sum_credits(beats: tuple[ConceptualBeat, ...], kind: BeatKind) -> Credits:
    """Sum the credit deltas of beats of a given kind."""
    total = Credits.zero()
    for beat in beats:
        if beat.kind == kind:
            total = total + beat.credits_delta
    return total


def _by_domain(
    beats: tuple[ConceptualBeat, ...], domain: ActivityDomain
) -> tuple[ConceptualBeat, ...]:
    """Return only the beats belonging to a domain."""
    return tuple(beat for beat in beats if beat.domain == domain)


def _flight(beats: tuple[ConceptualBeat, ...]) -> FlightRollup:
    return FlightRollup(
        jumps=_count(beats, BeatKind.JUMP),
        distance_ly=_sum_magnitude(beats, BeatKind.JUMP),
    )


def _exploration(beats: tuple[ConceptualBeat, ...]) -> ExplorationRollup:
    return ExplorationRollup(
        bodies_scanned=_count(beats, BeatKind.SCAN_BODY),
        bodies_mapped=_count(beats, BeatKind.MAP_BODY),
        honks=_count(beats, BeatKind.HONK),
        data_sold=_sum_credits(beats, BeatKind.SELL_EXPLORATION),
    )


def _combat(beats: tuple[ConceptualBeat, ...]) -> CombatRollup:
    return CombatRollup(
        kills=_count(beats, BeatKind.BOUNTY) + _count(beats, BeatKind.BOND),
        bounties=_sum_credits(beats, BeatKind.BOUNTY),
        bonds=_sum_credits(beats, BeatKind.BOND),
    )


def _trade(beats: tuple[ConceptualBeat, ...]) -> TradeRollup:
    return TradeRollup(
        buys=_count(beats, BeatKind.MARKET_BUY),
        sells=_count(beats, BeatKind.MARKET_SELL),
        spent=_sum_credits(beats, BeatKind.MARKET_BUY),
        earned=_sum_credits(beats, BeatKind.MARKET_SELL),
    )


def _mining(beats: tuple[ConceptualBeat, ...]) -> MiningRollup:
    return MiningRollup(refined=_count(beats, BeatKind.REFINE))


def _missions(beats: tuple[ConceptualBeat, ...]) -> MissionRollup:
    return MissionRollup(
        completed=_count(beats, BeatKind.MISSION_COMPLETE),
        rewards=_sum_credits(beats, BeatKind.MISSION_COMPLETE),
    )


def _engineering(beats: tuple[ConceptualBeat, ...]) -> EngineeringRollup:
    return EngineeringRollup(crafted=_count(beats, BeatKind.ENGINEER_CRAFT))


def _carrier(beats: tuple[ConceptualBeat, ...]) -> CarrierRollup:
    return CarrierRollup(jumps=_count(beats, BeatKind.CARRIER_JUMP))


def _exobiology(beats: tuple[ConceptualBeat, ...]) -> ExobiologyRollup:
    return ExobiologyRollup(
        samples=_count(beats, BeatKind.EXOBIO_SAMPLE),
        sold=_sum_credits(beats, BeatKind.EXOBIO_SELL),
    )


def _srv(beats: tuple[ConceptualBeat, ...]) -> SrvRollup:
    return SrvRollup(deployments=_count(beats, BeatKind.SRV_DEPLOY))


def _on_foot(beats: tuple[ConceptualBeat, ...]) -> OnFootRollup:
    return OnFootRollup(
        disembarks=_count(beats, BeatKind.DISEMBARK),
        settlements=_count(beats, BeatKind.SETTLEMENT_VISIT),
    )


def _net_credits(beats: tuple[ConceptualBeat, ...]) -> Credits:
    """Sum the credit delta across every beat."""
    total = Credits.zero()
    for beat in beats:
        total = total + beat.credits_delta
    return total


def _system_at(beat: ConceptualBeat) -> SystemName | None:
    """Return the star system named in a beat's detail, if any."""
    for key, value in beat.detail:
        if key == STAR_SYSTEM_FIELD and isinstance(value, str) and value.strip():
            return SystemName(value)
    return None


def _endpoints(
    beats: tuple[ConceptualBeat, ...],
) -> tuple[SystemName | None, SystemName | None]:
    """Return the first and last location-bearing systems in order."""
    located = tuple(
        system for system in (_system_at(beat) for beat in beats) if system is not None
    )
    if not located:
        return None, None
    return located[0], located[-_ONE_OCCURRENCE]


def _modes_used(beats: tuple[ConceptualBeat, ...]) -> tuple[ActivityMode, ...]:
    """Return the distinct control modes across beats in canonical order."""
    present = {beat.mode for beat in beats}
    return tuple(mode for mode in _MODE_ORDER if mode in present)


def _activity(beats: tuple[ConceptualBeat, ...]) -> ActivityRollup:
    """Build the ActivityRollup, including a domain only when it has beats."""

    def rollup(domain: ActivityDomain, builder):
        domain_beats = _by_domain(beats, domain)
        return builder(domain_beats) if domain_beats else None

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
        on_foot=rollup(ActivityDomain.ON_FOOT, _on_foot),
        modes_used=_modes_used(beats),
    )


def assemble(
    commander: CommanderId,
    window: SessionWindow,
    beats: tuple[ConceptualBeat, ...],
    rank_progression: tuple[RankDelta, ...],
    spec: RollupSpec,
    ship: str = "",
) -> SessionDebrief:
    """Fold the session's beats into a complete SessionDebrief."""
    start_system, end_system = _endpoints(beats)
    return SessionDebrief(
        commander=commander,
        window=window,
        start_system=start_system,
        end_system=end_system,
        net_credits_delta=_net_credits(beats),
        beats=beats,
        activity=_activity(beats),
        rank_progression=rank_progression,
        config_schema_version=spec.schema_version,
        ship=ship,
    )
