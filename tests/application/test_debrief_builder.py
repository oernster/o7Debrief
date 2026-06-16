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
    # An empty-rules spec produces no beats, which is a valid debrief.
    assert result.beats == ()
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
