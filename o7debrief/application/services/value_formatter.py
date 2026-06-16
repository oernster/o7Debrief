"""ValueFormatter: turn domain values into display-ready strings.

All numeric and time formatting for the debrief lives here so the presenter
reads cleanly. The formatter is driven entirely by a ``NumberFormat`` config
(itself populated from the taxonomy ``[format]`` table) so no formatting
literal is hardcoded. Event-time strings are parsed with the standard library
purely to reformat them; the wall clock is never read here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

__all__ = ["NumberFormat", "ValueFormatter"]

# Thousands grouping token for Python's format mini-language.
_GROUPED = ","
_UNGROUPED = ""
# Trailing marker Elite Dangerous journal timestamps use for UTC (Zulu).
_ZULU_SUFFIX = "Z"
_UTC_OFFSET = "+00:00"
# Number of seconds in an hour and in a minute, for duration breakdown.
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60
# Separator placed between a formatted amount and its unit suffix.
_SUFFIX_SEPARATOR = " "
# Sign and unit tokens used when rendering deltas and percentages. Zero is
# the threshold separating a positive sign from a negative one; the rest are
# pure display characters, not domain values.
_POSITIVE_SIGN = "+"
_MINUS_SIGN = "-"
_PERCENT_SIGN = "%"
_CREDIT_ZERO = 0


@dataclass(frozen=True, slots=True)
class NumberFormat:
    """Display formatting tokens, sourced from the taxonomy ``[format]``."""

    credits_suffix: str
    distance_suffix: str
    thousands: bool
    duration_format: str
    time_format: str
    datetime_format: str


class ValueFormatter:
    """Formats credits, distances, durations and times for display."""

    def __init__(self, number_format: NumberFormat) -> None:
        self._fmt = number_format

    def _grouping(self) -> str:
        """Return the format grouping token honouring the thousands flag."""
        return _GROUPED if self._fmt.thousands else _UNGROUPED

    def integer(self, value: int) -> str:
        """Return an integer formatted with the configured grouping."""
        return format(value, self._grouping())

    def credits(self, value: int) -> str:
        """Return a credit amount grouped and suffixed (for example Cr)."""
        return f"{self.integer(value)}{_SUFFIX_SEPARATOR}{self._fmt.credits_suffix}"

    def distance(self, value: int) -> str:
        """Return a distance grouped and suffixed (for example ly)."""
        return f"{self.integer(value)}{_SUFFIX_SEPARATOR}{self._fmt.distance_suffix}"

    def signed_credits(self, value: int) -> str:
        """Return a credit delta with an explicit sign, grouped and suffixed.

        A non-negative value is prefixed with ``+``; a negative value keeps
        the minus sign that grouped formatting already produces.
        """
        body = self.credits(abs(value))
        sign = _POSITIVE_SIGN if value >= _CREDIT_ZERO else _MINUS_SIGN
        return f"{sign}{body}"

    def percent(self, value: int) -> str:
        """Return a signed percentage-point growth string (for example +12%)."""
        sign = _POSITIVE_SIGN if value >= _CREDIT_ZERO else _MINUS_SIGN
        return f"{sign}{abs(value)}{_PERCENT_SIGN}"

    def duration(self, seconds: float) -> str:
        """Return a duration rendered with the configured duration format."""
        whole = int(seconds)
        hours = whole // _SECONDS_PER_HOUR
        minutes = (whole % _SECONDS_PER_HOUR) // _SECONDS_PER_MINUTE
        return self._fmt.duration_format.format(hours=hours, minutes=minutes)

    def _parse(self, iso_utc: str) -> datetime:
        """Parse a journal ISO timestamp into an aware datetime (UTC)."""
        normalised = iso_utc
        if normalised.endswith(_ZULU_SUFFIX):
            normalised = normalised[: -len(_ZULU_SUFFIX)] + _UTC_OFFSET
        parsed = datetime.fromisoformat(normalised)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def time(self, iso_utc: str) -> str:
        """Return only the time portion of an event-time, formatted."""
        return self._parse(iso_utc).strftime(self._fmt.time_format)

    def datetime(self, iso_utc: str) -> str:
        """Return the full date and time of an event-time, formatted."""
        return self._parse(iso_utc).strftime(self._fmt.datetime_format)
