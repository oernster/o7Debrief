"""Rank adapter: persist per-commander rank snapshots between sessions.

The public adapter is ``JsonRankSnapshotStore`` (see
``json_rank_snapshot_store``), which stores each commander's last-known rank
state as a small JSON file so the next debrief can measure progress against it.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
