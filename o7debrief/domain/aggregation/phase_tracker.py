"""Phase tracking: derive the control mode in effect at each event.

The journal does not stamp every event with the commander's control mode,
so we reconstruct it by folding over the transition events that change it:
deploying or stowing the SRV, and disembarking or embarking on foot. The
result has exactly one ``ActivityMode`` per input event, aligned by index.
"""

from __future__ import annotations

from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.enums import ActivityMode

__all__ = [
    "LAUNCH_SRV",
    "DOCK_SRV",
    "SRV_DESTROYED",
    "DISEMBARK",
    "EMBARK",
    "SRV_FLAG",
    "mode_at_each",
]

LAUNCH_SRV = "LaunchSRV"
DOCK_SRV = "DockSRV"
SRV_DESTROYED = "SRVDestroyed"
DISEMBARK = "Disembark"
EMBARK = "Embark"

# Boolean field on Disembark/Embark indicating the SRV (vs ship) is involved.
SRV_FLAG = "SRV"


def _mode_after(event: RawEvent, current: ActivityMode) -> ActivityMode:
    """Return the control mode in effect after applying ``event``."""
    event_type = event.event_type
    if event_type == LAUNCH_SRV:
        return ActivityMode.SRV
    if event_type in (DOCK_SRV, SRV_DESTROYED):
        return ActivityMode.SHIP
    if event_type == DISEMBARK:
        return ActivityMode.ON_FOOT
    if event_type == EMBARK:
        if event.get(SRV_FLAG) is True:
            return ActivityMode.SRV
        return ActivityMode.SHIP
    return current


def mode_at_each(events: tuple[RawEvent, ...]) -> tuple[ActivityMode, ...]:
    """Return the control mode in effect at each event, aligned by index.

    Folds left, starting in ``SHIP``. Each transition event updates the
    running mode; non-transition events inherit the current mode.
    """
    modes: list[ActivityMode] = []
    current = ActivityMode.SHIP
    for event in events:
        current = _mode_after(event, current)
        modes.append(current)
    return tuple(modes)
