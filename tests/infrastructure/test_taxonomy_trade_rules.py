"""Tests for the taxonomy rules covering outfitting, the shipyard and engineering.

Two subjects that go wrong the same way. An outfitting purchase and an
experimental effect are both reported by the journal through an event that
already means something else, so each is settled by which channel the rule
reads and by which filter picks it. Split out of the provider tests, which
cover the parse itself.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from o7debrief.infrastructure.config.toml_config_provider import TomlConfigProvider

# Sentinel proving an absent note stays absent rather than becoming a blank.
_NO_NOTE = "<none>"


def _provider() -> TomlConfigProvider:
    """Return a provider over the shipped taxonomy."""
    taxonomy = Path(__file__).resolve().parents[2] / "config" / "debrief_taxonomy.toml"
    return TomlConfigProvider(taxonomy)


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
    # Income rides the credits channel and spending its own, because
    # credits is the income channel and a purchase routed through it counts as
    # money banked. One big enough raised the major-payout milestone.
    income = {
        "ModuleSell": ("SellPrice", MomentKind.MODULE_SELL),
        "ModuleSellRemote": ("SellPrice", MomentKind.MODULE_SELL),
        "ShipyardSell": ("ShipPrice", MomentKind.SHIP_SALE),
    }
    spending = {
        "ModuleBuy": ("BuyPrice", MomentKind.MODULE_BUY),
        "ShipyardBuy": ("ShipPrice", MomentKind.SHIP_PURCHASE),
        "ShipyardTransfer": ("TransferPrice", MomentKind.SHIP_TRANSFER),
    }

    for event, (field, kind) in income.items():
        rule = next(r for r in spec.rules_for(event) if r.kind is kind)
        assert rule.credits_field == field, event
        assert rule.magnitude_field is None, event
        assert rule.domain is ActivityDomain.SHIPYARD, event
    for event, (field, kind) in spending.items():
        rule = next(r for r in spec.rules_for(event) if r.kind is kind)
        assert rule.spend_field == field, event
        assert rule.credits_field is None, event
        assert rule.magnitude_field is None, event
        assert rule.domain is ActivityDomain.SHIPYARD, event


def test_a_vessel_hangar_still_wins_over_the_general_outfitting_rule() -> None:
    """A hangar bay is bought through the same events and keeps its own moment.

    The general rules are declared after it, so the first matching rule is
    still the hangar one.
    """
    kinds = [rule.kind for rule in _provider().load().rules_for("ModuleBuy")]

    assert kinds == [MomentKind.VESSEL_HANGAR_BUY, MomentKind.MODULE_BUY]
