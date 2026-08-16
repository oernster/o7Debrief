"""Measure how far a fleet carrier travelled, from the positions it arrived at.

A ``CarrierJump`` states the destination ``StarPos`` and never a ``JumpDist``,
so unlike a ship jump the distance cannot be read and has to be measured: the
straight-line gap between consecutive stated positions is the leg flown. That
leaves the first jump of a session unmeasurable, because the carrier's position
before it is stated nowhere in the session, which is why the leg count travels
with the distance rather than being assumed equal to the jumps made.

Extracted from the assembler as its own concern: everything here is geometry
over stated readings, where the rest of that module folds moments into counts
and currency totals.
"""

from __future__ import annotations

import math

__all__ = ["STAR_POS_FIELD", "leg_distances", "star_positions"]

# Raw-event/detail field carrying a system's galactic coordinates, as three
# numbers in light years.
STAR_POS_FIELD = "StarPos"

# Indices into the ordered star positions: the first reading, whose shape every
# later one must match; then the second, from which each position is paired
# with its predecessor to form a leg.
_FIRST_POSITION = 0
_SECOND_POSITION = 1
# Starting values for the distance and leg-count accumulators.
_NO_DISTANCE = 0.0
_NO_LEGS = 0
# A single leg, subtracted because the first arrival has no stated origin.
_ONE_LEG = 1


def _is_coordinate(axis: object) -> bool:
    """Return whether one element of a star position is a usable number.

    A bool is rejected explicitly because bool subclasses int and a stray True
    would otherwise read as a coordinate of one light year.
    """
    return isinstance(axis, (int, float)) and not isinstance(axis, bool)


def star_positions(moments, kind) -> tuple[tuple[float, ...], ...]:
    """Return the well-formed star positions stated by moments of a kind.

    A position must be a non-empty sequence of numbers, all positions the same
    length as the first, so the gaps between them are measurable at all. What
    that length is does not matter here: the requirement is that the readings
    are commensurable, not that space has any particular number of axes.
    Anything malformed is dropped rather than guessed at, so a bad payload
    shortens the measured legs instead of contributing a fictional distance.
    """
    positions: list[tuple[float, ...]] = []
    for moment in moments:
        if moment.kind != kind:
            continue
        raw = dict(moment.detail).get(STAR_POS_FIELD)
        if not isinstance(raw, (list, tuple)) or not raw:
            continue
        if not all(_is_coordinate(axis) for axis in raw):
            continue
        axes = tuple(float(axis) for axis in raw)
        if positions and len(axes) != len(positions[_FIRST_POSITION]):
            continue
        positions.append(axes)
    return tuple(positions)


def leg_distances(positions: tuple[tuple[float, ...], ...]) -> tuple[float, int]:
    """Return the total straight-line distance between consecutive positions.

    Also returns how many legs that total covers, which is one fewer than the
    number of positions: the first arrival has no stated origin to measure from.
    """
    total = _NO_DISTANCE
    for start, end in zip(positions, positions[_SECOND_POSITION:]):
        total += math.dist(start, end)
    return total, max(_NO_LEGS, len(positions) - _ONE_LEG)
