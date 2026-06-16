"""Typed exception hierarchy for the o7Debrief application layer.

These sit above the domain errors. ``ApplicationError`` is the single base
the outer layers can catch to handle any orchestration failure, and the
specific subclasses name the conditions the services raise.
"""

from __future__ import annotations

__all__ = [
    "ApplicationError",
    "ConfigSchemaMismatchError",
]


class ApplicationError(Exception):
    """Base class for all errors raised by the application layer."""


class ConfigSchemaMismatchError(ApplicationError):
    """Raised when a loaded spec's schema version is not the expected one.

    Carries both the expected and the actual schema version so the caller
    can report exactly which versions disagreed.
    """

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Config schema version mismatch: expected {expected!r}, "
            f"got {actual!r}."
        )
