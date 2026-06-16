"""Typed exception hierarchy for the o7Debrief domain layer.

Every validation failure in the domain raises one of these. The base
class lets callers (application/infrastructure layers) catch any domain
error with a single ``except O7DebriefError``.
"""

from __future__ import annotations

__all__ = [
    "O7DebriefError",
    "InvalidEventTimeError",
    "InvalidRawEventError",
    "InvalidCreditsError",
    "InvalidSystemNameError",
    "InvalidCommanderError",
    "InvalidSessionWindowError",
    "AggregationError",
]


class O7DebriefError(Exception):
    """Base class for all domain errors raised by o7Debrief."""


class InvalidEventTimeError(O7DebriefError):
    """Raised when an event timestamp is empty or cannot be parsed."""


class InvalidRawEventError(O7DebriefError):
    """Raised when a raw journal event is malformed (e.g. empty type)."""


class InvalidCreditsError(O7DebriefError):
    """Raised when a credit amount is negative."""


class InvalidSystemNameError(O7DebriefError):
    """Raised when a star-system name is empty after trimming."""


class InvalidCommanderError(O7DebriefError):
    """Raised when a commander identity is missing its fid or name."""


class InvalidSessionWindowError(O7DebriefError):
    """Raised when a session window ends before it starts."""


class AggregationError(O7DebriefError):
    """Raised when aggregation invariants are violated (ordering, empty input)."""
