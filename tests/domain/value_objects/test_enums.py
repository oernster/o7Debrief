"""Tests for the domain enumerations.

These assert the contractually required members exist, since other layers
reference them by name.
"""

from __future__ import annotations

from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
    RankLadder,
)


def test_activity_mode_members() -> None:
    assert {m.name for m in ActivityMode} == {
        "SHIP",
        "SRV",
        "SLV",
        "SLF",
        "ON_FOOT",
    }


def test_activity_domain_members() -> None:
    expected = {
        "TRAVEL",
        "EXPLORATION",
        "COMBAT",
        "TRADE",
        "MINING",
        "MISSIONS",
        "ENGINEERING",
        "CARRIER",
        "SRV",
        "SLV",
        "SLF",
        "ON_FOOT",
        "EXOBIOLOGY",
        "SHIPYARD",
    }
    assert {d.name for d in ActivityDomain} == expected


def test_moment_kind_members() -> None:
    expected = {
        "JUMP",
        "SCAN_BODY",
        "MAP_BODY",
        "HONK",
        "BOUNTY",
        "BOND",
        "DEATH",
        "SELL_EXPLORATION",
        "MARKET_BUY",
        "MARKET_SELL",
        "REFINE",
        "MISSION_COMPLETE",
        "ENGINEER_CRAFT",
        "CARRIER_JUMP",
        "EXOBIO_SAMPLE",
        "EXOBIO_SELL",
        "SRV_DEPLOY",
        "SLV_DEPLOY",
        "SLV_DOCK",
        "SLV_DESTROYED",
        "SLF_DEPLOY",
        "SLF_DOCK",
        "SLF_DESTROYED",
        "VESSEL_HANGAR_BUY",
        "VESSEL_HANGAR_SELL",
        "DISEMBARK",
        "SETTLEMENT_VISIT",
        "PROMOTION",
        "SHIP_SWAP",
        "SHIP_PURCHASE",
        "MILESTONE",
    }
    assert {b.name for b in MomentKind} == expected


def test_rank_ladder_members() -> None:
    expected = {
        "COMBAT",
        "TRADE",
        "EXPLORE",
        "CQC",
        "FEDERATION",
        "EMPIRE",
        "SOLDIER",
        "EXOBIOLOGIST",
    }
    assert {r.name for r in RankLadder} == expected
