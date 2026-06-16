"""Tests for the CommanderId value object."""

from __future__ import annotations

import pytest

from o7debrief.domain.errors import InvalidCommanderError
from o7debrief.domain.value_objects.commander_id import CommanderId


def test_accepts_valid() -> None:
    cmdr = CommanderId(fid="F1234", name="Jameson")
    assert cmdr.fid == "F1234"
    assert cmdr.name == "Jameson"


def test_empty_fid_raises() -> None:
    with pytest.raises(InvalidCommanderError):
        CommanderId(fid="", name="Jameson")


def test_whitespace_fid_raises() -> None:
    with pytest.raises(InvalidCommanderError):
        CommanderId(fid="   ", name="Jameson")


def test_empty_name_raises() -> None:
    with pytest.raises(InvalidCommanderError):
        CommanderId(fid="F1234", name="")


def test_whitespace_name_raises() -> None:
    with pytest.raises(InvalidCommanderError):
        CommanderId(fid="F1234", name="   ")
