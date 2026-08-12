"""Tests for the credit balance readings the builder takes from a session.

The balance is a level the journal states outright at every login, and the
session's net change is the difference between the first and last such reading.
That change used to be summed from the moments instead, which priced income and
nothing else, so a session that paid an eleven million credit rebuy still
reported a gain. These tests hold the change to the stated balances, and hold a
change that was never stated apart from a session that broke even.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_builder import DebriefBuilder
from tests.application.fakes import commander, event, spec

# Balances taken from a real session: the commander ended it twenty million
# credits poorer, having paid an eleven million credit rebuy along the way.
_OPENING_BALANCE = 33_457_213_621
_CLOSING_BALANCE = 33_437_103_620


def test_net_change_is_the_difference_between_the_stated_balances() -> None:
    """The defect this closes: the change counted income and nothing else.

    A session that paid an eleven million credit rebuy still reported a gain,
    because rebuys, outfitting and market purchases never reach an income
    total. Both ends of the balance are stated outright, so their difference
    captures every outgoing regardless of whether the journal itemises it.
    """
    events = (
        event("LoadGame", 0, Credits=_OPENING_BALANCE),
        event("LoadGame", 20, Credits=_CLOSING_BALANCE),
        event("Shutdown", 30),
    )

    result = DebriefBuilder(spec()).build(commander(), events, ())

    assert result.net_credits_delta == _CLOSING_BALANCE - _OPENING_BALANCE
    assert result.net_credits_delta < 0
    # The balance itself stays the latest reading, a level beside the change.
    assert result.credits_balance.value == _CLOSING_BALANCE


def test_a_single_balance_reading_leaves_the_change_unread() -> None:
    """One reading states a level but no change, so none is reported."""
    events = (event("LoadGame", 0, Credits=_OPENING_BALANCE), event("Shutdown", 30))

    result = DebriefBuilder(spec()).build(commander(), events, ())

    assert result.net_credits_delta is None
    assert result.credits_balance.value == _OPENING_BALANCE


def test_no_balance_reading_leaves_both_the_level_and_the_change_unread() -> None:
    events = (event("LoadGame", 0), event("Shutdown", 30))

    result = DebriefBuilder(spec()).build(commander(), events, ())

    assert result.net_credits_delta is None
    assert result.credits_balance is None


def test_a_boolean_is_never_mistaken_for_a_balance() -> None:
    """bool subclasses int, so a stray True must not read as one credit."""
    events = (
        event("LoadGame", 0, Credits=True),
        event("LoadGame", 10, Credits=_OPENING_BALANCE),
        event("LoadGame", 20, Credits=_CLOSING_BALANCE),
        event("Shutdown", 30),
    )

    result = DebriefBuilder(spec()).build(commander(), events, ())

    assert result.net_credits_delta == _CLOSING_BALANCE - _OPENING_BALANCE
