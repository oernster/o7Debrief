"""Phase tracking: derive the control mode in effect at each event.

The journal does not stamp every event with the commander's control mode,
so we reconstruct it by folding over the transition events that change it:
deploying or stowing the SRV, deploying or losing a ship-launched vessel
(the Nomad), launching, docking or losing a player-controlled ship-launched
fighter, and disembarking or embarking on foot. The result has exactly one
``ActivityMode`` per input event, aligned by index.

The Nomad is asymmetric in the journal, confirmed against live logs: it deploys
through the ship-launched fighter path (a ``LaunchFighter`` whose loadout is a
Nomad variant) but docks and is destroyed through the SRV path (``DockSRV`` and
``SRVDestroyed``, both reporting an SRVType of the vessel). So a ``LaunchFighter``
enters the vessel context only when its loadout matches the Nomad discriminator
supplied by the caller (from the taxonomy), leaving genuine fighters, which this
tool does not model as a control mode, untouched. Docking or losing the vessel
returns to the ship through the same ``DockSRV`` / ``SRVDestroyed`` transitions
that already serve the SRV.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.enums import ActivityMode

__all__ = [
    "LAUNCH_SRV",
    "DOCK_SRV",
    "SRV_DESTROYED",
    "LAUNCH_FIGHTER",
    "DOCK_FIGHTER",
    "FIGHTER_DESTROYED",
    "DISEMBARK",
    "EMBARK",
    "SRV_FLAG",
    "PLAYER_CONTROLLED",
    "SlvLaunchRule",
    "mode_at_each",
]

LAUNCH_SRV = "LaunchSRV"
DOCK_SRV = "DockSRV"
SRV_DESTROYED = "SRVDestroyed"
LAUNCH_FIGHTER = "LaunchFighter"
DOCK_FIGHTER = "DockFighter"
FIGHTER_DESTROYED = "FighterDestroyed"
DISEMBARK = "Disembark"
EMBARK = "Embark"

# Boolean field on Disembark/Embark indicating the SRV (vs ship) is involved.
SRV_FLAG = "SRV"
# Boolean field on LaunchFighter: true when the commander flies the fighter.
PLAYER_CONTROLLED = "PlayerControlled"


@dataclass(frozen=True, slots=True)
class SlvLaunchRule:
    """How to recognise a ship-launched-vessel deployment in the journal.

    ``event_type`` is the shared launch event (the Nomad reuses
    ``LaunchFighter``), ``field`` is the payload key carrying the loadout and
    ``tokens`` are the case-insensitive loadout substrings that identify a
    Nomad variant. All three come from the taxonomy so no game content string
    is hardcoded in the domain.
    """

    event_type: str
    field: str
    tokens: tuple[str, ...]


def _is_slv_launch(event: RawEvent, slv_launch: SlvLaunchRule) -> bool:
    """Return whether an event is a Nomad deployment under the given rule."""
    if event.event_type != slv_launch.event_type:
        return False
    value = event.get(slv_launch.field)
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(token.lower() in lowered for token in slv_launch.tokens)


def _mode_after(
    event: RawEvent, current: ActivityMode, slv_launch: SlvLaunchRule | None
) -> ActivityMode:
    """Return the control mode in effect after applying ``event``."""
    event_type = event.event_type
    if slv_launch is not None and _is_slv_launch(event, slv_launch):
        return ActivityMode.SLV
    if event_type == LAUNCH_FIGHTER:
        # A genuine (non-Nomad) fighter: the commander is in it only when it is
        # player-controlled; an NPC-crewed fighter leaves the ship context.
        if event.get(PLAYER_CONTROLLED) is True:
            return ActivityMode.SLF
        return current
    if event_type in (DOCK_FIGHTER, FIGHTER_DESTROYED):
        # Docking or losing the fighter returns to the ship; a remote fighter
        # loss while in the ship or SRV is a no-op, so only act from the fighter.
        return ActivityMode.SHIP if current is ActivityMode.SLF else current
    if event_type == LAUNCH_SRV:
        return ActivityMode.SRV
    if event_type in (DOCK_SRV, SRV_DESTROYED):
        # Serves both the SRV and the Nomad: the Nomad docks and is destroyed
        # through the SRV path, so either event returns control to the ship.
        return ActivityMode.SHIP
    if event_type == DISEMBARK:
        return ActivityMode.ON_FOOT
    if event_type == EMBARK:
        if event.get(SRV_FLAG) is True:
            return ActivityMode.SRV
        return ActivityMode.SHIP
    return current


def mode_at_each(
    events: tuple[RawEvent, ...], slv_launch: SlvLaunchRule | None = None
) -> tuple[ActivityMode, ...]:
    """Return the control mode in effect at each event, aligned by index.

    Folds left, starting in ``SHIP``. Each transition event updates the
    running mode; non-transition events inherit the current mode. ``slv_launch``
    supplies the Nomad-deployment discriminator; when omitted, no event is
    treated as entering the ship-launched-vessel context.
    """
    modes: list[ActivityMode] = []
    current = ActivityMode.SHIP
    for event in events:
        current = _mode_after(event, current, slv_launch)
        modes.append(current)
    return tuple(modes)
