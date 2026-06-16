"""Tests for the domain enumerations.

These assert the contractually required members exist, since other layers
reference them by name.
"""

from __future__ import annotations

from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
    RankLadder,
)


def test_activity_mode_members() -> None:
    assert {m.name for m in ActivityMode} == {"SHIP", "SRV", "ON_FOOT"}


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
        "ON_FOOT",
        "EXOBIOLOGY",
    }
    assert {d.name for d in ActivityDomain} == expected


def test_beat_kind_members() -> None:
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
        "DISEMBARK",
        "SETTLEMENT_VISIT",
        "PROMOTION",
        "MILESTONE",
    }
    assert {b.name for b in BeatKind} == expected


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
