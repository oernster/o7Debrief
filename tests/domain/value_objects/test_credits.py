"""Tests for the Credits value object."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidCreditsError
from o7debrief.domain.value_objects.credits import Credits


def test_zero_classmethod() -> None:
    assert Credits.zero().value == 0


def test_accepts_zero_and_positive() -> None:
    assert Credits(0).value == 0
    assert Credits(123).value == 123


def test_negative_raises() -> None:
    with pytest.raises(InvalidCreditsError):
        Credits(-1)


def test_add() -> None:
    assert (Credits(100) + Credits(50)).value == 150


def test_sub_positive_result() -> None:
    assert (Credits(100) - Credits(40)).value == 60


def test_sub_clamps_at_zero() -> None:
    assert (Credits(10) - Credits(40)).value == 0


def test_sub_exact_to_zero() -> None:
    assert (Credits(40) - Credits(40)).value == 0


def test_lt_true_and_false() -> None:
    assert Credits(1) < Credits(2)
    assert not (Credits(2) < Credits(1))


def test_str_digit_grouped_large() -> None:
    assert str(Credits(14320500)) == "14,320,500"


def test_str_small_value_ungrouped() -> None:
    assert str(Credits(500)) == "500"
