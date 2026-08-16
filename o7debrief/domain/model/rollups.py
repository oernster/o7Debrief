"""Per-domain rollups and the aggregate ActivityRollup.

Each rollup summarises one gameplay domain with a small set of integer,
Credits or tuple fields. ``ActivityRollup`` composes the thirteen optional
domain rollups and exposes which domains were actually active.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import ActivityDomain, ActivityMode

__all__ = [
    "ActivityRollup",
    "CarrierRollup",
    "CombatRollup",
    "EngineeringRollup",
    "ExobiologyRollup",
    "ExplorationRollup",
    "FlightRollup",
    "MiningRollup",
    "MissionRollup",
    "OnFootRollup",
    "ShipyardRollup",
    "SlfRollup",
    "SlvRollup",
    "SrvRollup",
    "TradeRollup",
]


@dataclass(frozen=True, slots=True)
class FlightRollup:
    """Travel summary: jumps made and total distance covered.

    ``distance_ly`` is a float because the journal states each jump distance as
    one (``"JumpDist": 12.129``). Truncating to int would quietly shed a
    fraction of a light year on every jump.
    """

    jumps: int = 0
    distance_ly: float = 0.0


@dataclass(frozen=True, slots=True)
class ExplorationRollup:
    """Exploration summary: scans, maps, honks and data sold."""

    bodies_scanned: int = 0
    bodies_mapped: int = 0
    honks: int = 0
    data_sold: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class CombatRollup:
    """Combat summary: kills and the bounty/bond earnings split."""

    kills: int = 0
    bounties: Credits = field(default_factory=Credits.zero)
    bonds: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class TradeRollup:
    """Trade summary: market buys and sells, plus material-trader exchanges.

    ``material_trades`` counts exchanges at a raw, manufactured or encoded
    material trader. It is a plain count and carries no credit flow because a
    material trade has none: the commander pays in one material and is paid in
    another; the journal states no price. Counting it alongside the market
    figures is the honest reading, since a session can trade heavily at the
    material traders while buying and selling nothing on any commodity market.
    """

    buys: int = 0
    sells: int = 0
    spent: Credits = field(default_factory=Credits.zero)
    earned: Credits = field(default_factory=Credits.zero)
    material_trades: int = 0


@dataclass(frozen=True, slots=True)
class MiningRollup:
    """Mining summary: refining events completed."""

    refined: int = 0


@dataclass(frozen=True, slots=True)
class MissionRollup:
    """Mission summary: completions and their reward totals.

    ``rewards`` is the credit total; ``coin_rewards`` is the separate Merc Coins
    total earned from Operations, kept apart from credits by design.
    """

    completed: int = 0
    rewards: Credits = field(default_factory=Credits.zero)
    coin_rewards: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class EngineeringRollup:
    """Engineering summary: grade rolls made and experimental effects applied.

    The two are counted apart because they are different work. A grade is
    rolled over and over, often dozens of times for one module; an experimental
    effect is chosen once and applied once. The journal reports both as an
    ``EngineerCraft``, so counting them together made a session of picking
    effects read as a session of heavy modification.
    """

    crafted: int = 0
    experimentals: int = 0


@dataclass(frozen=True, slots=True)
class CarrierRollup:
    """Fleet carrier summary: jumps performed and the distance they covered.

    A ``CarrierJump`` states no ``JumpDist``, so unlike a ship jump the distance
    is not read but derived: each jump states the destination ``StarPos``; the
    straight-line gap between consecutive positions is the leg flown. That
    leaves the very first jump of a session with no measurable origin, because
    the carrier's position before it is not stated anywhere in the session.
    ``legs_measured`` and ``legs_total`` carry that gap explicitly so the report
    can say the distance covers eight of nine jumps rather than presenting a
    short total as though it were complete.
    """

    jumps: int = 0
    distance_ly: float = 0.0
    legs_measured: int = 0
    legs_total: int = 0


@dataclass(frozen=True, slots=True)
class ExobiologyRollup:
    """Exobiology summary: samples taken and data sold."""

    samples: int = 0
    sold: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class SrvRollup:
    """SRV summary: number of SRV deployments."""

    deployments: int = 0


@dataclass(frozen=True, slots=True)
class SlvRollup:
    """Ship-launched vessel summary: Nomad deployments and hangar trading.

    ``deployments`` counts how many times the vessel was launched onto a
    surface; ``hangars_bought`` and ``hangars_sold`` count Vessel Hangar
    module purchases and sales (of any size). Credit flows are deliberately
    not summed here so vessel outfitting does not distort net-credit totals,
    matching how ship-module and market purchases are treated elsewhere.
    """

    deployments: int = 0
    hangars_bought: int = 0
    hangars_sold: int = 0


@dataclass(frozen=True, slots=True)
class SlfRollup:
    """Ship-launched fighter summary: number of fighter deployments."""

    deployments: int = 0


@dataclass(frozen=True, slots=True)
class OnFootRollup:
    """On-foot summary: disembarks and settlements visited."""

    disembarks: int = 0
    settlements: int = 0


@dataclass(frozen=True, slots=True)
class ShipyardRollup:
    """Outfitting and shipyard summary: what was bought and what was sold.

    Counts and sums are kept apart per side, because a session that spent
    fifty million on modules and took forty million back for the ones it
    replaced is not the same session as one that did neither; a single net
    figure would report them identically.

    A Vessel Hangar bay is bought and sold through these same journal events
    but is counted on the Ship-Launched Vessel card instead, so it is absent
    here. A ship taken in part-exchange is priced inside the purchase event
    rather than stated as a sale, so it counts as neither sold nor earned. Both
    gaps are declared in the section note rather than papered over.
    """

    modules_bought: int = 0
    modules_sold: int = 0
    module_spend: Credits = field(default_factory=Credits.zero)
    module_earned: Credits = field(default_factory=Credits.zero)
    ships_bought: int = 0
    ships_sold: int = 0
    ship_spend: Credits = field(default_factory=Credits.zero)
    ship_earned: Credits = field(default_factory=Credits.zero)
    # Moving a stored ship to the station the commander is at. Neither a
    # purchase nor a sale, so it gets its own line rather than distorting
    # either: it is real money all the same, one transfer in a live journal
    # costing 1,626,451 Cr.
    transfers: int = 0
    transfer_fees: Credits = field(default_factory=Credits.zero)


# Ordered pairing of each optional rollup attribute to its activity domain.
# Used to derive ``active_domains`` in a single, declarative pass so the
# mapping stays in one place rather than scattered through conditionals.
_DOMAIN_BY_ATTR: tuple[tuple[str, ActivityDomain], ...] = (
    ("flight", ActivityDomain.TRAVEL),
    ("exploration", ActivityDomain.EXPLORATION),
    ("combat", ActivityDomain.COMBAT),
    ("trade", ActivityDomain.TRADE),
    ("mining", ActivityDomain.MINING),
    ("missions", ActivityDomain.MISSIONS),
    ("engineering", ActivityDomain.ENGINEERING),
    ("carrier", ActivityDomain.CARRIER),
    ("exobiology", ActivityDomain.EXOBIOLOGY),
    ("srv", ActivityDomain.SRV),
    ("slv", ActivityDomain.SLV),
    ("slf", ActivityDomain.SLF),
    ("on_foot", ActivityDomain.ON_FOOT),
    ("shipyard", ActivityDomain.SHIPYARD),
)


@dataclass(frozen=True, slots=True)
class ActivityRollup:
    """All fourteen domain rollups plus the set of control modes used."""

    flight: FlightRollup | None = None
    exploration: ExplorationRollup | None = None
    combat: CombatRollup | None = None
    trade: TradeRollup | None = None
    mining: MiningRollup | None = None
    missions: MissionRollup | None = None
    engineering: EngineeringRollup | None = None
    carrier: CarrierRollup | None = None
    exobiology: ExobiologyRollup | None = None
    srv: SrvRollup | None = None
    slv: SlvRollup | None = None
    slf: SlfRollup | None = None
    on_foot: OnFootRollup | None = None
    shipyard: ShipyardRollup | None = None
    modes_used: tuple[ActivityMode, ...] = ()

    @property
    def active_domains(self) -> tuple[ActivityDomain, ...]:
        """The domains whose rollup is present, in canonical order."""
        return tuple(
            domain
            for attr, domain in _DOMAIN_BY_ATTR
            if getattr(self, attr) is not None
        )
