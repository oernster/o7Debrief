"""Tests for the LabelResolver and the mode-string helper."""

from __future__ import annotations

from tests.application.fakes import spec

from o7debrief.application.services.label_resolver import (
    LabelResolver,
    mode_string_from_name,
)


def test_mode_string_maps_every_mode_name() -> None:
    assert mode_string_from_name("SHIP") == "ship"
    assert mode_string_from_name("SRV") == "srv"
    assert mode_string_from_name("ON_FOOT") == "foot"


def test_defaults_are_derived_from_keys_when_unconfigured() -> None:
    resolver = LabelResolver(spec())

    assert resolver.domain_title("on_foot") == "On Foot"
    assert resolver.domain_icon("on_foot") == "on_foot"
    assert resolver.domain_note("travel") is None
    assert resolver.mode_label("foot") == "Foot"
    assert resolver.mode_icon("foot") == "foot"
    assert resolver.ladder_title("exobiologist") == "Exobiologist"
    assert resolver.tier_name("combat", 5) == "5"
    assert resolver.headline_label("jumps", "Jumps") == "Jumps"
    assert resolver.milestone_icon("promotion", "medal") == "medal"
    assert resolver.generic("footer.app_name", "o7Debrief") == "o7Debrief"


def test_configured_labels_override_defaults() -> None:
    labels = (
        ("domain.travel.title", "Voyaging"),
        ("domain.travel.icon", "rocket"),
        ("domain.travel.note", "Long haul."),
        ("mode.ship.label", "Starship"),
        ("mode.ship.icon", "vessel"),
        ("rank.combat.title", "Combat Rank"),
        ("rank.combat.tier.5", "Master"),
        ("headline.jumps.label", "Hyperspace jumps"),
        ("milestone.promotion.icon", "trophy"),
        ("label.footer.app_name", "Override"),
    )
    resolver = LabelResolver(spec(labels))

    assert resolver.domain_title("travel") == "Voyaging"
    assert resolver.domain_icon("travel") == "rocket"
    assert resolver.domain_note("travel") == "Long haul."
    assert resolver.mode_label("ship") == "Starship"
    assert resolver.mode_icon("ship") == "vessel"
    assert resolver.ladder_title("combat") == "Combat Rank"
    assert resolver.tier_name("combat", 5) == "Master"
    assert resolver.headline_label("jumps", "Jumps") == "Hyperspace jumps"
    assert resolver.milestone_icon("promotion", "medal") == "trophy"
    assert resolver.generic("footer.app_name", "fallback") == "Override"
