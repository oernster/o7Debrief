"""CommanderId value object: a commander's frontier id paired with name."""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.errors import InvalidCommanderError

__all__ = ["CommanderId"]


@dataclass(frozen=True, slots=True)
class CommanderId:
    """Identity of a commander: a stable frontier id and a display name."""

    fid: str
    name: str

    def __post_init__(self) -> None:
        if not self.fid.strip():
            raise InvalidCommanderError("Commander fid must not be empty.")
        if not self.name.strip():
            raise InvalidCommanderError("Commander name must not be empty.")
