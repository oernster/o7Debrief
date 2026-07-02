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
    "FlightRollup",
    "ExplorationRollup",
    "CombatRollup",
    "TradeRollup",
    "MiningRollup",
    "MissionRollup",
    "EngineeringRollup",
    "CarrierRollup",
    "ExobiologyRollup",
    "SrvRollup",
    "SlvRollup",
    "SlfRollup",
    "OnFootRollup",
    "ActivityRollup",
]


@dataclass(frozen=True, slots=True)
class FlightRollup:
    """Travel summary: jumps made and total distance covered."""

    jumps: int = 0
    distance_ly: int = 0


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
    """Trade summary: market buys and sells with their credit flows."""

    buys: int = 0
    sells: int = 0
    spent: Credits = field(default_factory=Credits.zero)
    earned: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class MiningRollup:
    """Mining summary: refining events completed."""

    refined: int = 0


@dataclass(frozen=True, slots=True)
class MissionRollup:
    """Mission summary: completions and their reward total."""

    completed: int = 0
    rewards: Credits = field(default_factory=Credits.zero)


@dataclass(frozen=True, slots=True)
class EngineeringRollup:
    """Engineering summary: crafting/modification events applied."""

    crafted: int = 0


@dataclass(frozen=True, slots=True)
class CarrierRollup:
    """Fleet carrier summary: carrier jumps performed."""

    jumps: int = 0


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
)


@dataclass(frozen=True, slots=True)
class ActivityRollup:
    """All thirteen domain rollups plus the set of control modes used."""

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
    modes_used: tuple[ActivityMode, ...] = ()

    @property
    def active_domains(self) -> tuple[ActivityDomain, ...]:
        """The domains whose rollup is present, in canonical order."""
        return tuple(
            domain
            for attr, domain in _DOMAIN_BY_ATTR
            if getattr(self, attr) is not None
        )
