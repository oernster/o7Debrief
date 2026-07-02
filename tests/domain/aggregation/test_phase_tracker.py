"""Tests for the phase tracker control-mode fold."""

from __future__ import annotations

from o7debrief.domain.aggregation.phase_tracker import (
    DISEMBARK,
    DOCK_FIGHTER,
    DOCK_SRV,
    EMBARK,
    FIGHTER_DESTROYED,
    LAUNCH_FIGHTER,
    LAUNCH_SRV,
    PLAYER_CONTROLLED,
    SRV_DESTROYED,
    SRV_FLAG,
    SlvLaunchRule,
    mode_at_each,
)

# The Nomad-deployment discriminator the taxonomy supplies at runtime.
_NOMAD = SlvLaunchRule(
    event_type=LAUNCH_FIGHTER,
    field="Loadout",
    tokens=("galactic", "stellar", "standard"),
)
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.enums import ActivityMode
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int, fields: tuple = ()) -> RawEvent:
    return RawEvent(event_type, EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z"), fields)


def test_empty_events_yields_empty() -> None:
    assert mode_at_each(()) == ()


def test_default_mode_is_ship() -> None:
    modes = mode_at_each((_ev("FSDJump", 0),))
    assert modes == (ActivityMode.SHIP,)


def test_launch_srv_enters_srv_then_dock_returns_to_ship() -> None:
    events = (
        _ev("FSDJump", 0),
        _ev(LAUNCH_SRV, 1),
        _ev("FSDJump", 2),
        _ev(DOCK_SRV, 3),
        _ev("FSDJump", 4),
    )
    modes = mode_at_each(events)
    assert modes == (
        ActivityMode.SHIP,
        ActivityMode.SRV,
        ActivityMode.SRV,
        ActivityMode.SHIP,
        ActivityMode.SHIP,
    )


def test_srv_destroyed_returns_to_ship() -> None:
    events = (_ev(LAUNCH_SRV, 0), _ev(SRV_DESTROYED, 1))
    modes = mode_at_each(events)
    assert modes == (ActivityMode.SRV, ActivityMode.SHIP)


def test_nomad_launch_enters_slv_then_dock_srv_returns_to_ship() -> None:
    # The Nomad deploys via a LaunchFighter with a Nomad loadout and docks via
    # a DockSRV, so the vessel context spans launch to dock.
    events = (
        _ev("FSDJump", 0),
        _ev(LAUNCH_FIGHTER, 1, (("Loadout", "galactic"),)),
        _ev("ScanOrganic", 2),
        _ev(DOCK_SRV, 3, (("SRVType", "lander01"),)),
        _ev("FSDJump", 4),
    )
    modes = mode_at_each(events, _NOMAD)
    assert modes == (
        ActivityMode.SHIP,
        ActivityMode.SLV,
        ActivityMode.SLV,
        ActivityMode.SHIP,
        ActivityMode.SHIP,
    )


def test_nomad_launch_matches_any_loadout_variant() -> None:
    for loadout in ("stellar", "standard", "Galactic"):
        events = (_ev(LAUNCH_FIGHTER, 0, (("Loadout", loadout),)),)
        assert mode_at_each(events, _NOMAD) == (ActivityMode.SLV,)


def test_player_controlled_fighter_enters_slf_then_dock_returns_to_ship() -> None:
    events = (
        _ev(LAUNCH_FIGHTER, 0, (("Loadout", "gu97"), (PLAYER_CONTROLLED, True))),
        _ev("Bounty", 1),
        _ev(DOCK_FIGHTER, 2, (("ID", 3),)),
        _ev("FSDJump", 3),
    )
    modes = mode_at_each(events, _NOMAD)
    assert modes == (
        ActivityMode.SLF,
        ActivityMode.SLF,
        ActivityMode.SHIP,
        ActivityMode.SHIP,
    )


def test_npc_fighter_launch_leaves_the_mode_unchanged() -> None:
    # PlayerControlled false means an NPC flies it; the commander stays in-ship.
    events = (_ev(LAUNCH_FIGHTER, 0, (("Loadout", "gu97"), (PLAYER_CONTROLLED, False))),)
    assert mode_at_each(events, _NOMAD) == (ActivityMode.SHIP,)


def test_fighter_destroyed_returns_to_ship_only_from_the_fighter() -> None:
    lost = (
        _ev(LAUNCH_FIGHTER, 0, (("Loadout", "gu97"), (PLAYER_CONTROLLED, True))),
        _ev(FIGHTER_DESTROYED, 1, (("ID", 3),)),
    )
    assert mode_at_each(lost, _NOMAD) == (ActivityMode.SLF, ActivityMode.SHIP)
    # A remote fighter loss while in the SRV must not disturb the SRV context.
    in_srv = (_ev(LAUNCH_SRV, 0), _ev(FIGHTER_DESTROYED, 1, (("ID", 3),)))
    assert mode_at_each(in_srv, _NOMAD) == (ActivityMode.SRV, ActivityMode.SRV)


def test_launch_fighter_ignored_without_discriminator() -> None:
    # With no Nomad rule supplied, no LaunchFighter enters the vessel context.
    events = (_ev(LAUNCH_FIGHTER, 0, (("Loadout", "galactic"),)),)
    assert mode_at_each(events) == (ActivityMode.SHIP,)


def test_launch_fighter_without_loadout_field_stays_in_ship() -> None:
    events = (_ev(LAUNCH_FIGHTER, 0),)
    assert mode_at_each(events, _NOMAD) == (ActivityMode.SHIP,)


def test_nomad_loss_via_srv_destroyed_returns_to_ship() -> None:
    # Confirmed against a live journal: a lost Nomad fires SRVDestroyed (the
    # vessel docks and dies through the SRV path), returning control to the ship.
    events = (
        _ev(LAUNCH_FIGHTER, 0, (("Loadout", "galactic"),)),
        _ev(SRV_DESTROYED, 1, (("SRVType", "lander01"),)),
    )
    assert mode_at_each(events, _NOMAD) == (ActivityMode.SLV, ActivityMode.SHIP)


def test_disembark_enters_on_foot() -> None:
    events = (_ev(DISEMBARK, 0),)
    assert mode_at_each(events) == (ActivityMode.ON_FOOT,)


def test_embark_without_srv_flag_returns_to_ship() -> None:
    events = (_ev(DISEMBARK, 0), _ev(EMBARK, 1))
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SHIP)


def test_embark_with_srv_flag_returns_to_srv() -> None:
    events = (
        _ev(DISEMBARK, 0),
        _ev(EMBARK, 1, ((SRV_FLAG, True),)),
    )
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SRV)


def test_embark_with_srv_flag_false_returns_to_ship() -> None:
    events = (
        _ev(DISEMBARK, 0),
        _ev(EMBARK, 1, ((SRV_FLAG, False),)),
    )
    modes = mode_at_each(events)
    assert modes == (ActivityMode.ON_FOOT, ActivityMode.SHIP)
