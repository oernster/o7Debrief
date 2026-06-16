"""Tests for the DebriefBuilder domain composition."""

from __future__ import annotations

from tests.application.fakes import commander, event, spec

from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.application.services.debrief_builder import DebriefBuilder


def test_build_returns_session_debrief_with_window_and_commander() -> None:
    events = (event("LoadGame", 0), event("Shutdown", 30))
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert isinstance(result, SessionDebrief)
    assert result.commander == commander()
    # The window spans the first and last event-times and sees the shutdown.
    assert result.window.start.epoch_s == events[0].event_time.epoch_s
    assert result.window.end.epoch_s == events[1].event_time.epoch_s
    assert result.window.clean_shutdown is True
    # An empty-rules spec produces no moments, which is a valid debrief.
    assert result.moments == ()
    assert result.config_schema_version == spec().schema_version


def test_build_reads_the_ship_from_the_load_game_event() -> None:
    events = (
        event(
            "LoadGame", 0, Ship="PantherMkII", Ship_Localised="Panther Clipper Mk II"
        ),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    # The localised name is preferred for display.
    assert result.ship == "Panther Clipper Mk II"


def test_build_falls_back_to_the_internal_ship_symbol() -> None:
    events = (event("LoadGame", 0, Ship="PantherMkII"), event("Shutdown", 30))
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "PantherMkII"


def test_build_ship_is_empty_without_a_load_game() -> None:
    events = (event("FSDJump", 0, StarSystem="Sol"), event("Shutdown", 30))
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == ""


def test_build_reads_the_ship_name_from_the_load_game_event() -> None:
    events = (
        event(
            "LoadGame",
            0,
            Ship="PantherMkII",
            Ship_Localised="Panther Clipper Mk II",
            ShipName="STARDUST",
        ),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "Panther Clipper Mk II"
    assert result.ship_name == "STARDUST"


def test_build_ship_name_is_empty_when_the_ship_is_unnamed() -> None:
    events = (event("LoadGame", 0, Ship="PantherMkII"), event("Shutdown", 30))
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship_name == ""


def test_build_ship_is_empty_when_the_load_game_names_no_ship() -> None:
    events = (event("LoadGame", 0), event("Shutdown", 30))
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == ""
    assert result.ship_name == ""


def test_build_tracks_a_ship_swap_to_the_latest_vessel() -> None:
    """A mid-session ShipyardSwap plus Loadout report the new ship and name."""
    events = (
        event(
            "LoadGame",
            0,
            Ship="CobraMkIII",
            Ship_Localised="Cobra Mk III",
            ShipName="STARDUST",
        ),
        event(
            "ShipyardSwap",
            10,
            ShipType="federation_corvette",
            ShipType_Localised="Federal Corvette",
        ),
        event("Loadout", 11, Ship="federation_corvette", ShipName="BIG BERTHA"),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "Federal Corvette"
    assert result.ship_name == "BIG BERTHA"


def test_build_falls_back_to_internal_symbol_for_a_swapped_ship() -> None:
    """A new ship whose localised name was never seen shows its internal symbol."""
    events = (
        event("LoadGame", 0, Ship="CobraMkIII", Ship_Localised="Cobra Mk III"),
        event("Loadout", 11, Ship="federation_corvette", ShipName="BIG BERTHA"),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "federation_corvette"
    assert result.ship_name == "BIG BERTHA"


def test_build_takes_the_latest_name_for_the_same_ship() -> None:
    """A later Loadout for the same ship updates to its latest custom name."""
    events = (
        event(
            "LoadGame",
            0,
            Ship="CobraMkIII",
            Ship_Localised="Cobra Mk III",
            ShipName="STARDUST",
        ),
        event("Loadout", 11, Ship="CobraMkIII", ShipName="STARDUST II"),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "Cobra Mk III"
    assert result.ship_name == "STARDUST II"


def test_build_tracks_a_newly_bought_ship() -> None:
    """A ShipyardNew plus Loadout report the bought ship and its name."""
    events = (
        event(
            "LoadGame",
            0,
            Ship="CobraMkIII",
            Ship_Localised="Cobra Mk III",
            ShipName="STARDUST",
        ),
        event(
            "ShipyardNew", 10, ShipType="python_nx", ShipType_Localised="Python Mk II"
        ),
        event("Loadout", 11, Ship="python_nx", ShipName="NIGHTSHADE"),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "Python Mk II"
    assert result.ship_name == "NIGHTSHADE"


def test_build_matches_the_ship_symbol_case_insensitively() -> None:
    """The journal's mixed-case ship symbol still resolves the localised name.

    LoadGame writes "Cutter" while the following Loadout writes "cutter"; the
    localised name must survive that, rather than degrading to the raw symbol.
    """
    events = (
        event(
            "LoadGame",
            0,
            Ship="Cutter",
            Ship_Localised="Imperial Cutter",
            ShipName="EMPEROR'S SOLACE",
        ),
        event("Loadout", 11, Ship="cutter", ShipName="EMPEROR'S SOLACE"),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    assert result.ship == "Imperial Cutter"
    assert result.ship_name == "EMPEROR'S SOLACE"


def test_build_records_ship_changes_as_timeline_moments() -> None:
    """A swap appears as a rich, time-ordered moment naming both ships."""
    events = (
        event(
            "LoadGame",
            0,
            Ship="cobramkiii",
            Ship_Localised="Cobra Mk III",
            ShipID=1,
            ShipName="STARDUST",
        ),
        event(
            "ShipyardSwap",
            10,
            ShipType="federation_corvette",
            ShipType_Localised="Federal Corvette",
            ShipID=2,
            StoreShipID=1,
            StoreOldShip="CobraMkIII",
        ),
        event(
            "Loadout",
            11,
            Ship="federation_corvette",
            ShipID=2,
            ShipName="BIG BERTHA",
        ),
        event("Shutdown", 30),
    )
    builder = DebriefBuilder(spec())

    result = builder.build(commander(), events, ())

    swaps = [moment for moment in result.moments if moment.kind.name == "SHIP_SWAP"]
    assert len(swaps) == 1
    assert swaps[0].label == (
        "Swapped from Cobra Mk III (STARDUST) to Federal Corvette (BIG BERTHA)."
    )
