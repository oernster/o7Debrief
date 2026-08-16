"""Tests for TomlConfigProvider against the real taxonomy file.

These prove the shipped ``config/debrief_taxonomy.toml`` parses into a spec the
application can consume: the moment rules carry the credit and magnitude fields
the rollups read, the mode mapping bridges ``foot`` to ON_FOOT and the flat
label map uses exactly the keys the LabelResolver looks up.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.infrastructure.config.toml_config_provider import TomlConfigProvider

# Every key a [[moment]] table may declare. The provider reads each one onto the
# MomentRule; anything outside this set parses fine and is then silently thrown
# away, which is exactly how the "text" key was lost. It was declared on all
# twenty-nine moments from the start; nothing ever read it, so every row in
# every report fell back to its kind label. A session of 261 engineering rolls
# printed "Engineer Craft" 261 times. Nothing failed, because a dropped key
# looks identical to a key nobody wanted. This set is the guard against the
# next one; adding a key to the taxonomy now means teaching the provider to
# read it or naming it here on purpose.
_READ_MOMENT_KEYS = frozenset(
    {
        "event",
        "kind",
        "domain",
        "mode",
        "text",
        "magnitude_field",
        "credits_field",
        "credits_array_field",
        "credits_item_fields",
        "coins_field",
        "where_field",
        "where_contains",
        "where_present",
    }
)

# Number of [[moment]] rules defined in the shipped taxonomy.
_EXPECTED_RULES = 36
# Threshold magnitudes declared in the taxonomy [thresholds] table.
_LONG_JUMP_LY = 50.0
_BIG_PAYOUT = 1000000
_HIGH_VALUE_EXOBIO = 5000000
# Sentinel proving an absent note stays absent rather than becoming a blank.
_NO_NOTE = "<none>"
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


def _raw_moments() -> list[dict]:
    """Return the [[moment]] tables straight from the shipped taxonomy."""
    with _taxonomy_path().open("rb") as handle:
        return tomllib.load(handle)["moment"]


def test_every_taxonomy_moment_key_is_actually_read() -> None:
    """No [[moment]] declares a key the provider quietly discards."""
    unread = {
        (moment["event"], key)
        for moment in _raw_moments()
        for key in moment
        if key not in _READ_MOMENT_KEYS
    }
    assert not unread, f"taxonomy keys parsed but never read: {sorted(unread)}"


def test_every_moment_declares_row_wording() -> None:
    """Each rule carries the text template its taxonomy entry declares."""
    spec = _provider().load()
    missing = [rule.event_type for rule in spec.rules if not rule.text_template]
    assert not missing, f"moments with no row wording: {missing}"


def test_an_experimental_effect_is_a_rule_of_its_own() -> None:
    """The two EngineerCraft rules are told apart by a field, not a value.

    Only the event that applies the effect carries ApplyExperimentalEffect;
    every later roll on that module restates ExperimentalEffect, so the latter
    cannot distinguish them. The experimental rule is declared first, since the
    first rule whose filter matches wins.
    """
    rules = _provider().load().rules_for("EngineerCraft")

    assert [rule.kind for rule in rules] == [
        MomentKind.ENGINEER_EXPERIMENTAL,
        MomentKind.ENGINEER_CRAFT,
    ]
    assert rules[0].where_present == "ApplyExperimentalEffect"
    assert rules[1].where_present is None


def test_engineer_craft_wording_names_the_work_and_the_engineer() -> None:
    """The engineering row states blueprint, grade, module and engineer."""
    craft = _provider().load().rules_for("EngineerCraft")[1]
    assert craft is not None
    # The blueprint and module ride the humanising filters, because the journal
    # states each as an internal token and never as English.
    assert craft.text_template == (
        "Applied {{ BlueprintName | blueprint }} grade {{ Level }} "
        "to a {{ Module | module }} at {{ Engineer }}."
    )


def test_material_trade_rule_is_trade_with_no_credit_flow() -> None:
    """A material-trader exchange is a trade moment that reads no credits.

    It is paid for in materials and the journal states no price, so naming a
    credits or magnitude field would invent one.
    """
    trade = _provider().load().rule_for("MaterialTrade")
    assert trade is not None
    assert trade.kind is MomentKind.MATERIAL_TRADE
    assert trade.domain is ActivityDomain.TRADE
    assert trade.mode is ActivityMode.SHIP
    assert trade.credits_field is None
    assert trade.credits_array_field is None
    assert trade.magnitude_field is None


def test_foot_mode_maps_to_on_foot() -> None:
    spec = _provider().load()
    disembark = spec.rule_for("Disembark")
    assert disembark is not None
    assert disembark.mode is ActivityMode.ON_FOOT


def test_nomad_deploy_rule_maps_to_slv_via_launchfighter() -> None:
    # The Nomad deploys through the shared LaunchFighter event, scoped to its
    # loadout variants by a where-filter.
    spec = _provider().load()
    launch = spec.rule_for("LaunchFighter")
    assert launch is not None
    assert launch.kind is MomentKind.SLV_DEPLOY
    assert launch.domain is ActivityDomain.SLV
    assert launch.mode is ActivityMode.SLV
    assert launch.where_field == "Loadout"
    assert launch.where_contains == ("galactic", "stellar", "standard")


def test_nomad_dock_rule_maps_to_slv_via_dock_srv() -> None:
    # The Nomad docks through DockSRV, scoped to the vessel's SRVType.
    spec = _provider().load()
    dock = spec.rule_for("DockSRV")
    assert dock is not None
    assert dock.kind is MomentKind.SLV_DOCK
    assert dock.domain is ActivityDomain.SLV
    assert dock.where_field == "SRVType"
    assert dock.where_contains == ("lander",)


def test_nomad_loss_rule_maps_to_slv_via_srv_destroyed() -> None:
    spec = _provider().load()
    lost = spec.rule_for("SRVDestroyed")
    assert lost is not None
    assert lost.kind is MomentKind.SLV_DESTROYED
    assert lost.domain is ActivityDomain.SLV
    assert lost.where_field == "SRVType"
    assert lost.where_contains == ("lander",)


def test_launch_fighter_has_nomad_then_fighter_rules_in_that_order() -> None:
    # LaunchFighter is shared: the Nomad rule (with a loadout filter) must come
    # first, then the generic fighter rule (no filter) as the catch-all.
    spec = _provider().load()
    rules = spec.rules_for("LaunchFighter")
    assert len(rules) == 2
    assert rules[0].kind is MomentKind.SLV_DEPLOY
    assert rules[0].where_field == "Loadout"
    assert rules[1].kind is MomentKind.SLF_DEPLOY
    assert rules[1].domain is ActivityDomain.SLF
    assert rules[1].where_field is None
    assert rules[1].where_contains == ()


def test_fighter_dock_and_loss_rules_map_to_slf() -> None:
    spec = _provider().load()
    assert spec.rule_for("DockFighter").kind is MomentKind.SLF_DOCK
    assert spec.rule_for("DockFighter").mode is ActivityMode.SHIP
    assert spec.rule_for("FighterDestroyed").kind is MomentKind.SLF_DESTROYED


def test_vessel_hangar_rules_carry_a_where_filter() -> None:
    spec = _provider().load()
    buy = spec.rule_for("ModuleBuy")
    assert buy is not None
    assert buy.kind is MomentKind.VESSEL_HANGAR_BUY
    assert buy.where_field == "BuyItem"
    assert buy.where_contains == ("fighterbay",)
    sell = spec.rule_for("ModuleSell")
    assert sell.kind is MomentKind.VESSEL_HANGAR_SELL
    assert sell.where_field == "SellItem"
    assert sell.where_contains == ("fighterbay",)


def test_moment_without_where_filter_leaves_fields_empty() -> None:
    spec = _provider().load()
    jump = spec.rule_for("FSDJump")
    assert jump.where_field is None
    assert jump.where_contains == ()


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
    assert spec.label_for("domain.slv.title", miss) == "Ship-Launched Vessel"
    assert spec.label_for("mode.slv.tag", miss) == "V"
    assert spec.label_for("mode.ship.label", miss) == "Ship"
    assert spec.label_for("mode.foot.label", miss) == "On Foot"
    assert spec.label_for("mode.ship.tag", miss) == "S"
    assert spec.label_for("mode.foot.tag", miss) == "F"
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


def test_the_humanise_vocabulary_is_read_from_the_shipped_taxonomy() -> None:
    """The decoder's whole vocabulary is configuration, so it is read not built."""
    vocabulary = _provider().humanise_vocabulary()

    assert vocabulary.ratings
    assert vocabulary.words
    assert vocabulary.mounts


def test_a_taxonomy_without_a_humanise_table_yields_the_defaults(tmp_path) -> None:
    """An older taxonomy still loads; the decoder degrades to title-casing."""
    taxonomy = tmp_path / "bare.toml"
    taxonomy.write_text('[meta]\nschema_version = "1"\n', encoding="utf-8")

    vocabulary = TomlConfigProvider(taxonomy).humanise_vocabulary()

    assert vocabulary.ratings == ()
    assert vocabulary.words == {}


def test_meta_without_an_app_name_or_licence_contributes_no_footer_labels(
    tmp_path,
) -> None:
    """The footer labels are optional: a taxonomy stating neither states neither."""
    taxonomy = tmp_path / "nameless.toml"
    taxonomy.write_text(
        '[meta]\nschema_version = "1"\n'
        "[thresholds]\n"
        "long_jump_ly = 50\n"
        "big_payout_credits = 1000000\n"
        "high_value_exobio_credits = 1000000\n",
        encoding="utf-8",
    )

    spec = TomlConfigProvider(taxonomy).load()

    assert spec.label_for("label.footer.app_name", "MISS") == "MISS"
    assert spec.label_for("label.footer.license", "MISS") == "MISS"


def test_a_declared_domain_note_reaches_the_label_map() -> None:
    """The taxonomy could declare a note and nothing read it back.

    The outfitting section needs one, because a Vessel Hangar and a ship taken
    in part-exchange are both absent from its totals.
    """
    spec = _provider().load()

    note = spec.label_for("domain.shipyard.note", "")
    assert "Vessel Hangar" in note
    assert "part-exchange" in note


def test_a_domain_with_no_note_declares_none() -> None:
    """An absent note stays absent rather than becoming an empty line."""
    spec = _provider().load()

    assert spec.label_for("domain.travel.note", _NO_NOTE) == _NO_NOTE


def test_outfitting_and_shipyard_trade_is_mapped_and_priced() -> None:
    """Each purchase and sale names the payload key holding its price.

    None of these events was mapped at all, so a session that sold eighty
    modules for nearly two billion credits recorded none of it.
    """
    spec = _provider().load()
    priced = {
        "ModuleBuy": ("BuyPrice", MomentKind.MODULE_BUY),
        "ModuleSell": ("SellPrice", MomentKind.MODULE_SELL),
        "ModuleSellRemote": ("SellPrice", MomentKind.MODULE_SELL),
        "ShipyardBuy": ("ShipPrice", MomentKind.SHIP_PURCHASE),
        "ShipyardSell": ("ShipPrice", MomentKind.SHIP_SALE),
    }

    for event, (field, kind) in priced.items():
        rule = next(r for r in spec.rules_for(event) if r.kind is kind)
        assert rule.credits_field == field, event
        assert rule.domain is ActivityDomain.SHIPYARD, event


def test_a_vessel_hangar_still_wins_over_the_general_outfitting_rule() -> None:
    """A hangar bay is bought through the same events and keeps its own moment.

    The general rules are declared after it, so the first matching rule is
    still the hangar one.
    """
    kinds = [rule.kind for rule in _provider().load().rules_for("ModuleBuy")]

    assert kinds == [MomentKind.VESSEL_HANGAR_BUY, MomentKind.MODULE_BUY]
