"""Domain layer: pure, stdlib-only model and aggregation for o7Debrief.

The domain has no I/O, no framework dependency and never reads the
wall clock. All time handled here is event-time parsed from the journal.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
