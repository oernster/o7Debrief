"""Tests for TomlConfigProvider against the real taxonomy file.

These prove the shipped ``config/debrief_taxonomy.toml`` parses into a spec the
application can consume: the moment rules carry the credit and magnitude fields the
rollups read, the mode mapping bridges ``foot`` to ON_FOOT, and the flat label
map uses exactly the keys the LabelResolver looks up.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.infrastructure.config.toml_config_provider import TomlConfigProvider

# Number of [[moment]] rules defined in the shipped taxonomy.
_EXPECTED_RULES = 22
# Threshold magnitudes declared in the taxonomy [thresholds] table.
_LONG_JUMP_LY = 50.0
_BIG_PAYOUT = 1000000
_HIGH_VALUE_EXOBIO = 5000000
# Highest tier index on the combat ladder (nine tiers, zero-indexed).
_COMBAT_ELITE_INDEX = 8


def _taxonomy_path() -> Path:
    """Return the shipped taxonomy path relative to the repository root."""
    return Path(__file__).resolve().parents[2] / "config" / "debrief_taxonomy.toml"


def _provider() -> TomlConfigProvider:
    return TomlConfigProvider(_taxonomy_path())


def test_schema_version_is_read_from_meta() -> None:
    assert _provider().schema_version() == "1"


def test_rules_carry_kind_domain_and_mode() -> None:
    spec = _provider().load()
    assert len(spec.rules) == _EXPECTED_RULES

    jump = spec.rule_for("FSDJump")
    assert jump is not None
    assert jump.kind is MomentKind.JUMP
    assert jump.domain is ActivityDomain.TRAVEL
    assert jump.mode is ActivityMode.SHIP


def test_ship_change_events_map_to_shipyard_moments() -> None:
    spec = _provider().load()

    swap = spec.rule_for("ShipyardSwap")
    assert swap is not None
    assert swap.kind is MomentKind.SHIP_SWAP
    assert swap.domain is ActivityDomain.SHIPYARD

    purchase = spec.rule_for("ShipyardNew")
    assert purchase is not None
    assert purchase.kind is MomentKind.SHIP_PURCHASE
    assert purchase.domain is ActivityDomain.SHIPYARD


def test_foot_mode_maps_to_on_foot() -> None:
    spec = _provider().load()
    disembark = spec.rule_for("Disembark")
    assert disembark is not None
    assert disembark.mode is ActivityMode.ON_FOOT


def test_rules_carry_credit_and_magnitude_fields() -> None:
    spec = _provider().load()
    assert spec.rule_for("FSDJump").magnitude_field == "JumpDist"
    assert spec.rule_for("Bounty").credits_field == "TotalReward"
    assert spec.rule_for("MarketSell").credits_field == "TotalSale"
    # SellOrganicData has no scalar credit key: its value is summed from the
    # BioData array's Value and Bonus per entry.
    exobio = spec.rule_for("SellOrganicData")
    assert exobio.credits_field is None
    assert exobio.credits_array_field == "BioData"
    assert exobio.credits_item_fields == ("Value", "Bonus")
    # A moment with no income or magnitude has neither field.
    assert spec.rule_for("Disembark").credits_field is None
    assert spec.rule_for("Disembark").magnitude_field is None


def test_thresholds_match_the_taxonomy() -> None:
    thresholds = _provider().load().thresholds
    assert thresholds.long_jump_ly == _LONG_JUMP_LY
    assert thresholds.big_payout_credits == _BIG_PAYOUT
    assert thresholds.high_value_exobio_credits == _HIGH_VALUE_EXOBIO


def test_labels_use_the_resolver_key_convention() -> None:
    spec = _provider().load()
    miss = "MISS"
    assert spec.label_for("domain.travel.title", miss) == "Travel"
    assert spec.label_for("domain.srv.icon", miss) == "buggy"
    assert spec.label_for("mode.ship.label", miss) == "Ship"
    assert spec.label_for("mode.foot.label", miss) == "On Foot"
    assert spec.label_for("rank.combat.title", miss) == "Combat"
    assert spec.label_for("rank.combat.tier.0", miss) == "Harmless"
    assert spec.label_for(f"rank.combat.tier.{_COMBAT_ELITE_INDEX}", miss) == "Elite"


def test_moment_label_is_the_titleised_kind() -> None:
    spec = _provider().load()
    # The timeline label is the moment kind titleised, not the raw event name.
    assert spec.label_for("FSDJump", "MISS") == "Jump"
    assert spec.label_for("Scan", "MISS") == "Scan Body"


def test_footer_labels_come_from_meta() -> None:
    spec = _provider().load()
    assert spec.label_for("label.footer.app_name", "MISS") == "o7 Debrief"
    assert spec.label_for("label.footer.license", "MISS") == "LGPL-3.0-or-later"
