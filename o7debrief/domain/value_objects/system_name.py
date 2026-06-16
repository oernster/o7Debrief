"""SystemName value object: a non-empty star-system identifier."""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import InvalidSystemNameError

__all__ = ["SystemName"]


@dataclass(frozen=True, slots=True)
class SystemName:
    """The name of a star system, guaranteed non-empty after trimming."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidSystemNameError("System name must not be empty.")

    def __str__(self) -> str:
        return self.value
