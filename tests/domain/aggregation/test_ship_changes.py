"""Tests for ship-change records built from shipyard events."""

from __future__ import annotations

from o7debrief.domain.aggregation.ship_changes import ship_change_moments
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from o7debrief.domain.value_objects.event_time import EventTime


def _ev(event_type: str, sec: int, **fields: object) -> RawEvent:
    when = EventTime.parse(f"2024-01-01T10:00:{sec:02d}Z")
    return RawEvent(event_type, when, tuple(fields.items()))


def test_no_ship_events_yield_no_records() -> None:
    events = (_ev("FSDJump", 0, StarSystem="Sol"), _ev("Shutdown", 5))
    assert ship_change_moments(events) == ()


def test_swap_names_both_ships_with_their_types_and_names() -> None:
    events = (
        _ev(
            "LoadGame",
            0,
            Ship="cutter",
            Ship_Localised="Imperial Cutter",
            ShipID=1,
            ShipName="EMPEROR'S SOLACE",
        ),
        _ev(
            "ShipyardSwap",
            10,
            ShipType="python_nx",
            ShipType_Localised="Python Mk II",
            ShipID=2,
            StoreShipID=1,
            StoreOldShip="Cutter",
        ),
        # No Ship field here: the name still resolves and indexing tolerates it.
        _ev("Loadout", 11, ShipID=2, ShipName="NIGHTSHADE"),
    )

    moments = ship_change_moments(events)

    assert len(moments) == 1
    assert moments[0].kind is MomentKind.SHIP_SWAP
    assert moments[0].domain is ActivityDomain.SHIPYARD
    assert moments[0].label == (
        "Swapped from Imperial Cutter (EMPEROR'S SOLACE) "
        "to Python Mk II (NIGHTSHADE)."
    )


def test_a_purchase_is_not_recorded_here() -> None:
    """ShipyardNew names the ship bought but states no price.

    The purchase is recorded from the priced ShipyardBuy through the taxonomy
    instead, so the row says what the ship cost and the sum reaches the
    outfitting rollup. Recording it in both places would put two rows in the
    timeline for one purchase. ShipyardNew is still read, for the ship names a
    swap needs.
    """
    events = (
        _ev(
            "ShipyardNew",
            10,
            ShipType="python_nx",
            ShipType_Localised="Python Mk II",
            NewShipID=2,
        ),
        _ev("Loadout", 11, Ship="python_nx", ShipID=2, ShipName="NIGHTSHADE"),
    )

    assert ship_change_moments(events) == ()


def test_a_swap_still_names_a_ship_first_seen_on_a_purchase() -> None:
    """The ShipyardNew that follows a purchase remains part of the name index."""
    events = (
        _ev(
            "ShipyardNew",
            10,
            ShipType="python_nx",
            ShipType_Localised="Python Mk II",
            NewShipID=2,
        ),
        _ev("ShipyardSwap", 12, ShipType="sidewinder", ShipID=1, StoreShipID=2),
    )

    moments = ship_change_moments(events)

    assert [moment.kind for moment in moments] == [MomentKind.SHIP_SWAP]
    assert moments[0].label.startswith("Swapped from Python Mk II")


def test_swap_falls_back_to_internal_symbols_when_not_localised() -> None:
    # No localised type and no names seen, so internal symbols are shown.
    events = (
        _ev(
            "ShipyardSwap",
            10,
            ShipType="sidewinder",
            ShipID=2,
            StoreShipID=1,
            StoreOldShip="SideWinderX",
        ),
    )

    moments = ship_change_moments(events)

    assert moments[0].label == "Swapped from SideWinderX to sidewinder."


def test_swap_with_no_stored_ship_falls_back_to_a_placeholder() -> None:
    # No StoreShipID and no StoreOldShip, so the origin cannot be identified.
    events = (
        _ev(
            "ShipyardSwap",
            10,
            ShipType="python_nx",
            ShipType_Localised="Python Mk II",
            ShipID=2,
        ),
    )

    moments = ship_change_moments(events)

    assert moments[0].label == "Swapped from an unknown ship to Python Mk II."


def test_a_naming_event_without_an_id_is_skipped_when_indexing() -> None:
    events = (
        _ev("Loadout", 0, ShipName="GHOST"),  # no ShipID: ignored when indexing
        _ev(
            "ShipyardSwap",
            10,
            ShipType="python_nx",
            ShipType_Localised="Python Mk II",
            ShipID=2,
            StoreShipID=1,
            StoreOldShip="Cutter",
        ),
    )

    moments = ship_change_moments(events)

    assert moments[0].label == "Swapped from Cutter to Python Mk II."
