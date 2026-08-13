"""ValueFormatter: turn domain values into display-ready strings.

All numeric and time formatting for the debrief lives here so the presenter
reads cleanly. The formatter is driven entirely by a ``NumberFormat`` config
(itself populated from the taxonomy ``[format]`` table) so no formatting
literal is hardcoded. Event-time strings are parsed with the standard library
purely to reformat them; the wall clock is never read here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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
# Format mini-language precision for a distance: one decimal place.
_ONE_DECIMAL_PLACE = ".1f"
# Sortable year-month key used to group and to name a history page file. It is
# never displayed, so it is fixed here rather than drawn from configuration.
_MONTH_KEY_FORMAT = "%Y-%m"
# Sortable ISO day key, used to group rows for a daily rollup and to measure
# the age of a row in whole days. Never displayed, so likewise fixed here.
_DAY_KEY_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True, slots=True)
class NumberFormat:
    """Display formatting tokens, sourced from the taxonomy ``[format]``."""

    credits_suffix: str
    coins_suffix: str
    distance_suffix: str
    thousands: bool
    duration_format: str
    time_format: str
    datetime_format: str
    date_format: str
    month_format: str
    timezone_label: str


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

    def coins(self, value: int) -> str:
        """Return a Merc Coins amount grouped and suffixed (for example Merc Coins)."""
        return f"{self.integer(value)}{_SUFFIX_SEPARATOR}{self._fmt.coins_suffix}"

    def distance(self, value: float) -> str:
        """Return a distance grouped, rounded and suffixed (for example ly).

        Distances are real quantities: the journal states a jump as 12.129 ly.
        One decimal place is kept so a short hop reads as 7.8 ly rather than
        collapsing to 8, while a long carrier run stays readable.
        """
        body = format(value, f"{self._grouping()}{_ONE_DECIMAL_PLACE}")
        return f"{body}{_SUFFIX_SEPARATOR}{self._fmt.distance_suffix}"

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

    def percent_level(self, value: int) -> str:
        """Return an unsigned percentage reading (for example 73%).

        A level answers "where does this stand", so it carries no sign; the
        signed form above answers "how far did it move".
        """
        return f"{value}{_PERCENT_SIGN}"

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
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    def time(self, iso_utc: str) -> str:
        """Return only the time portion of an event-time, formatted."""
        return self._parse(iso_utc).strftime(self._fmt.time_format)

    def datetime(self, iso_utc: str) -> str:
        """Return the full date and time of an event-time, formatted."""
        return self._parse(iso_utc).strftime(self._fmt.datetime_format)

    def date(self, iso_utc: str) -> str:
        """Return only the calendar day of an event-time, formatted.

        The day is read in the same zone the times are shown in, which is UTC,
        because ``_parse`` never converts. Grouping rows by a day computed in
        one zone while showing times in another would file entries under the
        wrong heading, so both must come from the same instant untouched.
        """
        return self._parse(iso_utc).strftime(self._fmt.date_format)

    def month(self, iso_utc: str) -> str:
        """Return the calendar month of an event-time, formatted for display."""
        return self._parse(iso_utc).strftime(self._fmt.month_format)

    def month_key(self, iso_utc: str) -> str:
        """Return the sortable year-month an event-time falls in.

        This is an internal grouping key, never shown to a reader, so its shape
        is fixed here rather than configured: it exists to sort and to name a
        page file and both break if a reader can change it.
        """
        return self._parse(iso_utc).strftime(_MONTH_KEY_FORMAT)

    def day_key(self, iso_utc: str) -> str:
        """Return the sortable ISO calendar day an event-time falls in."""
        return self._parse(iso_utc).strftime(_DAY_KEY_FORMAT)

    def timezone_label(self) -> str:
        """Return the label naming the zone every displayed time is in."""
        return self._fmt.timezone_label
