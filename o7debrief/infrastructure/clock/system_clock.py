"""SystemClock: the only place that reads the real wall clock.

Implements the application ``Clock`` port. The domain never reads the clock and
the application reads it solely through this port, so this is the single module
in the whole system that calls ``datetime.now``. It returns a timezone-aware UTC
instant as an ISO-8601 string.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["SystemClock"]


class SystemClock:
    """A ``Clock`` returning the current UTC time as an ISO-8601 string."""

    def now_utc(self) -> str:
        """Return the current UTC time as a timezone-aware ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()
