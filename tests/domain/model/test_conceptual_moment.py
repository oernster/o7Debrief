"""Tests for the ConceptualMoment model."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidRawEventError
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime


def _at() -> EventTime:
    return EventTime.parse("2024-01-01T10:00:00Z")


def _moment(label: str) -> ConceptualMoment:
    return ConceptualMoment(
        kind=MomentKind.JUMP,
        domain=ActivityDomain.TRAVEL,
        mode=ActivityMode.SHIP,
        occurred_at=_at(),
        label=label,
        magnitude=8,
        credits_delta=Credits.zero(),
        detail=(("StarSystem", "Sol"),),
    )


def test_valid_moment_fields() -> None:
    moment = _moment("Hyperspace jump")
    assert moment.label == "Hyperspace jump"
    assert moment.magnitude == 8
    assert moment.kind is MomentKind.JUMP


def test_empty_label_raises() -> None:
    with pytest.raises(InvalidRawEventError):
        _moment("")
