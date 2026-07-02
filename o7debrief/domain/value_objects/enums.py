"""Enumerations describing activity modes, domains, moment kinds and ranks.

These are pure classification vocabularies shared across the domain. They
carry no behaviour beyond identity, so plain ``enum.Enum`` members suffice.
"""

from __future__ import annotations

from enum import Enum, auto

__all__ = [
    "ActivityMode",
    "ActivityDomain",
    "MomentKind",
    "RankLadder",
]


class ActivityMode(Enum):
    """The physical control context the commander is in."""

    SHIP = auto()
    SRV = auto()
    SLV = auto()
    SLF = auto()
    ON_FOOT = auto()


class ActivityDomain(Enum):
    """The broad gameplay domain a moment belongs to."""

    TRAVEL = auto()
    EXPLORATION = auto()
    COMBAT = auto()
    TRADE = auto()
    MINING = auto()
    MISSIONS = auto()
    ENGINEERING = auto()
    CARRIER = auto()
    SRV = auto()
    SLV = auto()
    SLF = auto()
    ON_FOOT = auto()
    EXOBIOLOGY = auto()
    SHIPYARD = auto()


class MomentKind(Enum):
    """A single conceptual thing that happened during the session."""

    JUMP = auto()
    SCAN_BODY = auto()
    MAP_BODY = auto()
    HONK = auto()
    BOUNTY = auto()
    BOND = auto()
    DEATH = auto()
    SELL_EXPLORATION = auto()
    MARKET_BUY = auto()
    MARKET_SELL = auto()
    REFINE = auto()
    MISSION_COMPLETE = auto()
    ENGINEER_CRAFT = auto()
    CARRIER_JUMP = auto()
    EXOBIO_SAMPLE = auto()
    EXOBIO_SELL = auto()
    SRV_DEPLOY = auto()
    SLV_DEPLOY = auto()
    SLV_DOCK = auto()
    SLV_DESTROYED = auto()
    SLF_DEPLOY = auto()
    SLF_DOCK = auto()
    SLF_DESTROYED = auto()
    VESSEL_HANGAR_BUY = auto()
    VESSEL_HANGAR_SELL = auto()
    DISEMBARK = auto()
    SETTLEMENT_VISIT = auto()
    PROMOTION = auto()
    SHIP_SWAP = auto()
    SHIP_PURCHASE = auto()
    MILESTONE = auto()


class RankLadder(Enum):
    """A progression ladder the commander can advance along."""

    COMBAT = auto()
    TRADE = auto()
    EXPLORE = auto()
    CQC = auto()
    FEDERATION = auto()
    EMPIRE = auto()
    SOLDIER = auto()
    EXOBIOLOGIST = auto()
