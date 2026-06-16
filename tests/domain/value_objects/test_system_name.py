"""Tests for the SystemName value object."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidSystemNameError
from o7debrief.domain.value_objects.system_name import SystemName


def test_accepts_nonempty() -> None:
    assert SystemName("Sol").value == "Sol"


def test_str_returns_value() -> None:
    assert str(SystemName("Lave")) == "Lave"


def test_empty_raises() -> None:
    with pytest.raises(InvalidSystemNameError):
        SystemName("")


def test_whitespace_only_raises() -> None:
    with pytest.raises(InvalidSystemNameError):
        SystemName("   ")
