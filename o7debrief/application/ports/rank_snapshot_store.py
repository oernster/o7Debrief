"""RankSnapshotStore port: persists a commander's last-known rank state.

Rank progress is measured between sessions, so the application needs the
commander's tiers and percentages as they stood at the end of the previous
session. The store loads that snapshot and saves a fresh one each run.

The ``CommanderId`` and ``RankSnapshot`` types appear only in annotations
and are named as forward references, so this port module imports neither the
domain nor a sibling DTO module; concrete stores in infrastructure supply
the real types by shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from o7debrief.application.dto.rank_snapshot import RankSnapshot
    from o7debrief.domain.value_objects.commander_id import CommanderId

__all__ = ["RankSnapshotStore"]


class RankSnapshotStore(Protocol):
    """A store of per-commander rank snapshots across sessions."""

    def load(self, commander: CommanderId) -> RankSnapshot | None:
        """Return the saved snapshot for a commander, or None if absent."""
        ...

    def save(self, commander: CommanderId, snapshot: RankSnapshot) -> None:
        """Persist the latest snapshot for a commander."""
        ...
