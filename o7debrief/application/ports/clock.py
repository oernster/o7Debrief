"""Clock port: the only source of wall-clock time in the application.

The domain never reads the clock; the application reads it solely through
this port (for example to stamp a generation time into export filenames).
The concrete clock lives in infrastructure.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["Clock"]


class Clock(Protocol):
    """A source of the current wall-clock time as an ISO-8601 string."""

    def now_utc(self) -> str:
        """Return the current UTC time as an ISO-8601 string."""
        ...
