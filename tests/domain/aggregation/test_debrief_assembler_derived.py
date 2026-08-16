"""Tests for the quantities the assembler derives rather than counts.

A count is easy: the rollup tallies moments of a kind. These cover the figures
that need a value read or worked out, which is where every silent zero in this
application has come from. A jump distance is stated as a real quantity and was
being discarded by an int-only reader; a purchase states its cost on a channel
of its own so it never joins an income total; a carrier states where it arrived
and never how far it came; the session's net change is a reading passed in
rather than a fold.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.debrief_assembler import assemble
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from tests.domain.aggregation.test_debrief_assembler import (
    _commander,
    _moment,
    _spec,
    _window,
)

# Star positions taken from a real journal, three consecutive carrier jumps.
# The legs between them are roughly 499.9 ly and 498.0 ly, comfortably inside
# the carrier's 500 ly range, which is what makes them a useful check.
_POS_ONE = [28.96875, 95.34375, -455.59375]
_POS_TWO = [15.71875, 200.65625, -944.09375]
_POS_THREE = [25.59375, 350.5625, -1418.90625]
_STAR_POS = "StarPos"


def _carrier_jump(sec: int, position=None) -> ConceptualMoment:
    """Build a carrier-jump moment, optionally stating a destination position."""
    detail = () if position is None else ((_STAR_POS, position),)
    return _moment(MomentKind.CARRIER_JUMP, ActivityDomain.CARRIER, sec, detail=detail)


def test_jump_distance_sums_the_fractional_magnitudes() -> None:
    # The journal states a jump distance as a float. Truncating each one would
    # shed a fraction of a light year per jump; rejecting them outright, as an
    # int-only guard once did, reported five jumps as no distance at all.
    moments = (
        _moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 1, magnitude=12.129),
        _moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 2, magnitude=16.122),
        _moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 3, magnitude=7.773),
    )
    debrief = assemble(_commander(), _window(), moments, (), _spec())
    assert debrief.activity.flight.jumps == 3
    assert debrief.activity.flight.distance_ly == 12.129 + 16.122 + 7.773


def test_carrier_distance_measures_the_legs_between_stated_positions() -> None:
    # Three jumps give two measurable legs: the first arrival has no stated
    # origin to measure from, so the total covers two of the three.
    moments = (
        _carrier_jump(1, _POS_ONE),
        _carrier_jump(2, _POS_TWO),
        _carrier_jump(3, _POS_THREE),
    )
    carrier = assemble(_commander(), _window(), moments, (), _spec()).activity.carrier
    assert carrier.jumps == 3
    assert carrier.legs_measured == 2
    assert carrier.legs_total == 3
    assert round(carrier.distance_ly) == 998


def test_carrier_distance_is_nothing_when_no_position_is_stated() -> None:
    moments = (_carrier_jump(1), _carrier_jump(2))
    carrier = assemble(_commander(), _window(), moments, (), _spec()).activity.carrier
    assert carrier.jumps == 2
    assert carrier.distance_ly == 0.0
    assert carrier.legs_measured == 0
    assert carrier.legs_total == 2


def test_carrier_distance_drops_malformed_positions_rather_than_guessing() -> None:
    # A position that is not a sequence, is empty, holds a non-number, holds a
    # bool or does not match the shape of the first good reading is unusable.
    # Each is skipped, shortening the measured legs instead of contributing a
    # fictional distance.
    moments = (
        _carrier_jump(1, _POS_ONE),
        _carrier_jump(2, "not a position"),
        _carrier_jump(3, []),
        _carrier_jump(4, ["x", "y", "z"]),
        _carrier_jump(5, [True, False, True]),
        _carrier_jump(6, [1.0, 2.0]),
        _carrier_jump(7, _POS_TWO),
    )
    carrier = assemble(_commander(), _window(), moments, (), _spec()).activity.carrier
    assert carrier.jumps == 7
    assert carrier.legs_measured == 1
    assert carrier.legs_total == 7
    assert round(carrier.distance_ly) == 500


def test_trade_spending_comes_from_the_buy_spend_channel() -> None:
    # The journal states a purchase cost in TotalCost, which rides the
    # magnitude channel so spending never joins an income total. Reporting
    # nought spent beside a set of purchases was the defect this closes.
    moments = (
        _moment(MomentKind.MARKET_BUY, ActivityDomain.TRADE, 1, spend=223155),
        _moment(MomentKind.MARKET_BUY, ActivityDomain.TRADE, 2, spend=76950),
    )
    trade = assemble(_commander(), _window(), moments, (), _spec()).activity.trade
    assert trade.buys == 2
    assert trade.spent.value == 300105
    # Buys carry no credit delta, so they leave the earnings side untouched.
    assert trade.earned.value == 0


def test_net_credit_change_is_carried_through_as_given() -> None:
    debrief = assemble(
        _commander(), _window(), (), (), _spec(), net_credits_delta=-20110001
    )
    assert debrief.net_credits_delta == -20110001
