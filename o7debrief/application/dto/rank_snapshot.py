"""RankSnapshot DTO: a commander's rank state captured at a point in time.

The store persists this between sessions so the next debrief can measure
percentage growth and tier-ups against the previous close. Tiers and
percentages are tuples of (ladder-key, value) pairs to stay immutable.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RankSnapshot"]


@dataclass(frozen=True, slots=True)
class RankSnapshot:
    """A commander's per-ladder tiers and percentages at one instant."""

    commander_fid: str
    tiers: tuple[tuple[str, int], ...]
    pcts: tuple[tuple[str, int], ...]
    captured_iso: str
