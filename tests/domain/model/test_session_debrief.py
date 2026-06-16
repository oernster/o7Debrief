"""Tests for the SessionDebrief model and its ordering invariant."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import AggregationError
from o7debrief.domain.model.conceptual_beat import ConceptualBeat
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.model.session_debrief import SessionDebrief
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
)
from o7debrief.domain.value_objects.event_time import EventTime
from o7debrief.domain.value_objects.session_window import SessionWindow

_SCHEMA = "1.0.0"


def _at(sec: int) -> EventTime:
    return EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z")


def _beat(sec: int) -> ConceptualBeat:
    return ConceptualBeat(
        kind=BeatKind.JUMP,
        domain=ActivityDomain.TRAVEL,
        mode=ActivityMode.SHIP,
        occurred_at=_at(sec),
        label="Jump",
        magnitude=0,
        credits_delta=Credits.zero(),
        detail=(),
    )


def _window() -> SessionWindow:
    return SessionWindow(start=_at(0), end=_at(59), clean_shutdown=True)


def _commander() -> CommanderId:
    return CommanderId(fid="F1", name="Jameson")


def test_sorted_beats_accepted() -> None:
    debrief = SessionDebrief(
        commander=_commander(),
        window=_window(),
        start_system=None,
        end_system=None,
        net_credits_delta=Credits.zero(),
        beats=(_beat(0), _beat(5), _beat(5), _beat(10)),
        activity=ActivityRollup(),
        rank_progression=(),
        config_schema_version=_SCHEMA,
    )
    assert len(debrief.beats) == 4


def test_empty_beats_accepted() -> None:
    debrief = SessionDebrief(
        commander=_commander(),
        window=_window(),
        start_system=None,
        end_system=None,
        net_credits_delta=Credits.zero(),
        beats=(),
        activity=ActivityRollup(),
        rank_progression=(),
        config_schema_version=_SCHEMA,
    )
    assert debrief.beats == ()


def test_out_of_order_beats_raise() -> None:
    with pytest.raises(AggregationError):
        SessionDebrief(
            commander=_commander(),
            window=_window(),
            start_system=None,
            end_system=None,
            net_credits_delta=Credits.zero(),
            beats=(_beat(10), _beat(5)),
            activity=ActivityRollup(),
            rank_progression=(),
            config_schema_version=_SCHEMA,
        )
