"""Aggregation: pure functions turning raw events into a debrief.

Every function here consumes event-time only and performs no I/O. They
form the pipeline: isolate the latest session, track control mode, build
moments, compute rank deltas and assemble the final debrief.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
