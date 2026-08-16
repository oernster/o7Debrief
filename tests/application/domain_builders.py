"""Builders for real domain objects used as presenter inputs.

These assemble genuine ConceptualMoment, ActivityRollup, RankDelta and
SessionDebrief instances so the presenter formats true domain data. Keeping
them here keeps the test modules focused on assertions.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.debrief_assembler import STAR_SYSTEM_FIELD
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
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
    RankLadder,
)
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow
from o7debrief.domain.value_objects.system_name import SystemName
from tests.application.fakes import at, commander

# Window seconds for a non-empty session, kept readable as named bounds.
_START_SECOND = 0
_END_SECOND = 59


def moment(
    kind: MomentKind,
    domain: ActivityDomain,
    second: int,
    *,
    mode: ActivityMode = ActivityMode.SHIP,
    magnitude: float = 0.0,
    credits: int = 0,
    coins: int = 0,
    detail: tuple[tuple[str, object], ...] = (),
    system: str | None = None,
    text_template: str = "",
) -> ConceptualMoment:
    """Build a single ConceptualMoment, optionally tagged with a star system."""
    if system is not None:
        detail = detail + ((STAR_SYSTEM_FIELD, system),)
    return ConceptualMoment(
        kind=kind,
        domain=domain,
        mode=mode,
        occurred_at=at(second),
        label=kind.name,
        magnitude=magnitude,
        credits_delta=Credits(credits),
        coins_delta=Credits(coins),
        detail=detail,
        text_template=text_template,
    )


def full_activity() -> ActivityRollup:
    """Return an ActivityRollup with every one of the fourteen domains present."""
    return ActivityRollup(
        flight=FlightRollup(jumps=3, distance_ly=120),
        exploration=ExplorationRollup(
            bodies_scanned=5,
            bodies_mapped=2,
            honks=1,
            data_sold=Credits(2000),
        ),
        combat=CombatRollup(kills=4, bounties=Credits(5000), bonds=Credits(1500)),
        trade=TradeRollup(buys=2, sells=2, spent=Credits(800), earned=Credits(3200)),
        mining=MiningRollup(refined=7),
        missions=MissionRollup(completed=3, rewards=Credits(9000)),
        engineering=EngineeringRollup(crafted=2, experimentals=1),
        # Two jumps but only one measurable leg, which is the ordinary case: a
        # carrier jump states its destination and not its origin, so the first
        # jump of a session can never be measured.
        carrier=CarrierRollup(
            jumps=2, distance_ly=499.9, legs_measured=1, legs_total=2
        ),
        exobiology=ExobiologyRollup(samples=6, sold=Credits(40000)),
        srv=SrvRollup(deployments=2),
        slv=SlvRollup(deployments=1, hangars_bought=1, hangars_sold=1),
        slf=SlfRollup(deployments=2),
        on_foot=OnFootRollup(disembarks=3, settlements=1),
        shipyard=ShipyardRollup(
            modules_bought=2,
            modules_sold=3,
            module_spend=Credits(6000),
            module_earned=Credits(11000),
            ships_bought=1,
            ships_sold=1,
            ship_spend=Credits(60000000),
            ship_earned=Credits(23000000),
            transfers=1,
            transfer_fees=Credits(1626451),
        ),
        modes_used=(ActivityMode.SHIP, ActivityMode.SRV, ActivityMode.ON_FOOT),
    )


def window() -> SessionWindow:
    """Return a clean-shutdown window spanning the base minute."""
    return SessionWindow(
        start=at(_START_SECOND), end=at(_END_SECOND), clean_shutdown=True
    )


def rank_delta(
    ladder: RankLadder,
    *,
    from_tier: int,
    to_tier: int,
    promoted: bool,
    start_pct: int | None,
    end_pct: int | None,
    growth_pct: int | None,
    tier_ups: int,
) -> RankDelta:
    """Build a RankDelta with explicit fields for presenter coverage."""
    return RankDelta(
        ladder=ladder,
        from_tier=from_tier,
        to_tier=to_tier,
        promoted=promoted,
        start_pct=start_pct,
        end_pct=end_pct,
        growth_pct=growth_pct,
        tier_ups=tier_ups,
    )


def debrief(
    *,
    moments: tuple[ConceptualMoment, ...],
    activity: ActivityRollup,
    ranks: tuple[RankDelta, ...] = (),
    start_system: str | None = "Sol",
    end_system: str | None = "Achenar",
    net_credits: int | None = 0,
    schema_version: str = "1",
    ship: str = "",
    ship_name: str = "",
    credits_balance: int | None = None,
    credits_balance_at: str | None = None,
    systems_visited: int | None = None,
) -> SessionDebrief:
    """Assemble a SessionDebrief from prepared parts for presenter tests."""
    start = SystemName(start_system) if start_system is not None else None
    end = SystemName(end_system) if end_system is not None else None
    return SessionDebrief(
        commander=commander(),
        window=window(),
        start_system=start,
        end_system=end,
        net_credits_delta=net_credits,
        moments=moments,
        activity=activity,
        rank_progression=ranks,
        config_schema_version=schema_version,
        ship=ship,
        ship_name=ship_name,
        credits_balance=(None if credits_balance is None else Credits(credits_balance)),
        credits_balance_at=(
            None if credits_balance_at is None else EventTime.parse(credits_balance_at)
        ),
        systems_visited=systems_visited,
    )
