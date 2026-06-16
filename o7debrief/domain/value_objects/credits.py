"""Credits value object: a non-negative quantity of in-game credits."""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import InvalidCreditsError

__all__ = ["Credits"]

# Python format spec that groups thousands with commas, e.g. 14320500 ->
# "14,320,500". A structural formatting token, not a domain magic number.
_THOUSANDS_GROUPED = ","
# The lower bound credits may never fall below, used for clamping subtraction.
_CREDIT_FLOOR = 0


@dataclass(frozen=True, slots=True)
class Credits:
    """A non-negative integer amount of credits with safe arithmetic."""

    value: int

    def __post_init__(self) -> None:
        if self.value < _CREDIT_FLOOR:
            raise InvalidCreditsError("Credits value must not be negative.")

    @classmethod
    def zero(cls) -> Credits:
        """Return a zero-credit amount."""
        return cls(_CREDIT_FLOOR)

    def __add__(self, other: Credits) -> Credits:
        return Credits(self.value + other.value)

    def __sub__(self, other: Credits) -> Credits:
        """Subtract another amount, clamping the result at zero."""
        return Credits(max(_CREDIT_FLOOR, self.value - other.value))

    def __lt__(self, other: Credits) -> bool:
        return self.value < other.value

    def __str__(self) -> str:
        return format(self.value, _THOUSANDS_GROUPED)
