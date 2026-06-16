"""Tests for the ConceptualBeat model."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidRawEventError
from o7debrief.domain.model.conceptual_beat import ConceptualBeat
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
)
from o7debrief.domain.value_objects.event_time import EventTime


def _at() -> EventTime:
    return EventTime.parse("2024-01-01T10:00:00Z")


def _beat(label: str) -> ConceptualBeat:
    return ConceptualBeat(
        kind=BeatKind.JUMP,
        domain=ActivityDomain.TRAVEL,
        mode=ActivityMode.SHIP,
        occurred_at=_at(),
        label=label,
        magnitude=8,
        credits_delta=Credits.zero(),
        detail=(("StarSystem", "Sol"),),
    )


def test_valid_beat_fields() -> None:
    beat = _beat("Hyperspace jump")
    assert beat.label == "Hyperspace jump"
    assert beat.magnitude == 8
    assert beat.kind is BeatKind.JUMP


def test_empty_label_raises() -> None:
    with pytest.raises(InvalidRawEventError):
        _beat("")
