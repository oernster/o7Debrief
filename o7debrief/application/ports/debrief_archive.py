"""DebriefArchive port: lists debriefs already written to the output directory.

The tray reads existing debriefs so the recents list reflects what is on disk,
not only what this run produced. The concrete archive decides where to look and
how to order; it exposes a count and a paged slice so the ui can page through a
large back-catalogue without realising every entry at once.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["DebriefArchive"]


class DebriefArchive(Protocol):
    """A source of previously written debrief file paths, newest first."""

    def count(self) -> int:
        """Return how many debriefs are currently available."""
        ...

    def list_page(self, offset: int, limit: int) -> tuple[str, ...]:
        """Return up to ``limit`` debrief paths starting at ``offset``.

        Paths are ordered newest first, so ``offset`` zero is the most recent.
        """
        ...
