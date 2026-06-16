"""Tests for the domain exception hierarchy."""

from __future__ import annotations

import pytest

from o7debrief.domain import errors


@pytest.mark.parametrize(
    "subclass",
    [
        errors.InvalidEventTimeError,
        errors.InvalidRawEventError,
        errors.InvalidCreditsError,
        errors.InvalidSystemNameError,
        errors.InvalidCommanderError,
        errors.InvalidSessionWindowError,
        errors.AggregationError,
    ],
)
def test_every_error_is_an_o7debrief_error(subclass: type[Exception]) -> None:
    assert issubclass(subclass, errors.O7DebriefError)
    assert issubclass(subclass, Exception)


def test_base_error_can_be_raised_and_caught() -> None:
    with pytest.raises(errors.O7DebriefError):
        raise errors.O7DebriefError("boom")


def test_subclass_caught_as_base() -> None:
    with pytest.raises(errors.O7DebriefError):
        raise errors.AggregationError("nope")
