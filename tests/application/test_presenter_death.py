"""Tests for the death-row killer summary in the timeline presenter.

A death moment carries the Died payload in its detail plus the victim stamped
on by the builder; the presenter turns the pair into a "Killed by ...: CMDR ..."
row. These cover the single-killer, wing, name-only and no-killer shapes, every
degradation of the victim clause and that the wording is configurable through
the spec.
"""

from __future__ import annotations

from o7debrief.application.services.death_details import (
    KILLER_SQUADRON_FIELD,
    REBUY_COST_FIELD,
    VICTIM_NAME_FIELD,
    VICTIM_SHIP_FIELD,
    VICTIM_SHIP_NAME_FIELD,
)
from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from tests.application import domain_builders as build
from tests.application.fakes import at, number_format, spec


def _presenter(labels: tuple[tuple[str, str], ...] = ()) -> DebriefPresenter:
    return DebriefPresenter(spec(labels), number_format(), app_version="1.2.3")


def _death(detail: tuple) -> ConceptualMoment:
    """Build a death moment carrying a Died payload in its detail."""
    return ConceptualMoment(
        kind=MomentKind.DEATH,
        domain=ActivityDomain.COMBAT,
        mode=ActivityMode.SHIP,
        occurred_at=at(1),
        label="DEATH",
        magnitude=0,
        credits_delta=Credits(0),
        detail=detail,
    )


def _row_text(detail: tuple, labels: tuple[tuple[str, str], ...] = ()) -> str:
    debrief = build.debrief(
        moments=(_death(detail),), activity=ActivityRollup(modes_used=())
    )
    return _presenter(labels).present(debrief).to_context()["timeline"][0]["text"]


def test_single_killer_with_ship_and_rank() -> None:
    text = _row_text(
        (
            ("KillerName", "Cmdr Russet Meles"),
            ("KillerShip", "cobramkv"),
            ("KillerRank", "Elite"),
        )
    )
    assert text == "Killed by Cmdr Russet Meles (cobramkv, Elite)"


def test_prefers_localised_killer_name_and_ship() -> None:
    text = _row_text(
        (
            ("KillerName", "$ShipName_Police_Federation;"),
            ("KillerName_Localised", "Federal Security Service"),
            ("KillerShip", "federation_gunship"),
            ("KillerShip_Localised", "Federal Gunship"),
        )
    )
    assert text == "Killed by Federal Security Service (Federal Gunship)"


def test_killer_name_only_when_no_ship_or_rank() -> None:
    assert _row_text((("KillerName", "Cmdr Jameson"),)) == "Killed by Cmdr Jameson"


def test_wing_of_several_killers_is_listed() -> None:
    killers = [
        {"Name": "Cmdr A", "Ship": "anaconda", "Rank": "Deadly"},
        {"Name": "Cmdr B", "Ship": "python", "Rank": "Elite"},
        {"Name": "Cmdr C"},
    ]
    assert _row_text((("Killers", killers),)) == "Killed by Cmdr A, Cmdr B and Cmdr C"


def test_wing_of_one_named_killer_reads_as_a_single() -> None:
    # A Killers array with a single named entry needs no conjunction.
    assert _row_text((("Killers", [{"Name": "Cmdr Solo"}]),)) == "Killed by Cmdr Solo"


def test_wing_with_no_named_entries_falls_back() -> None:
    # A Killers array carrying no usable name drops through to the no-killer text.
    assert _row_text((("Killers", [{"Ship": "sidewinder"}, "junk"]),)) == "Destroyed"


def test_self_destruct_death_names_the_cause() -> None:
    # The moment factory marks a self-inflicted death; the row names it.
    assert _row_text((("SelfDestruct", True),)) == "Self-destruct"


def test_death_without_a_killer_or_cause_reports_plain_destruction() -> None:
    # An environmental death names no killer and is not a self-destruct.
    assert _row_text(()) == "Destroyed"


def test_wording_is_configurable_through_the_spec() -> None:
    labels = (
        ("label.death.killed_by", "Slain by"),
        ("label.death.no_killer", "Lost the ship"),
        ("label.list.and", "&"),
    )
    text = _row_text((("Killers", [{"Name": "A"}, {"Name": "B"}]),), labels)
    assert text == "Slain by A & B"
    assert _row_text((), labels) == "Lost the ship"


def test_the_victim_follows_the_cause_on_every_death_row() -> None:
    # The row has to stand alone months later: who died and in what.
    text = _row_text(
        (
            ("KillerName", "Cmdr Russet Meles"),
            ("KillerRank", "Elite"),
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_FIELD, "Imperial Cutter"),
            (VICTIM_SHIP_NAME_FIELD, "Majestic Darkness"),
        )
    )
    assert text == (
        "Killed by Cmdr Russet Meles (Elite): "
        'CMDR MidnightWraith in Imperial Cutter "Majestic Darkness"'
    )


def test_a_killerless_death_still_names_the_victim() -> None:
    text = _row_text(
        (
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_FIELD, "Imperial Cutter"),
        )
    )
    assert text == "Destroyed: CMDR MidnightWraith in Imperial Cutter"


def test_an_unnamed_hull_is_named_by_its_type_alone() -> None:
    text = _row_text(
        (
            ("SelfDestruct", True),
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_FIELD, "Sidewinder"),
        )
    )
    assert text == "Self-destruct: CMDR MidnightWraith in Sidewinder"


def test_a_hull_of_unknown_type_is_named_by_its_given_name() -> None:
    text = _row_text(
        (
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_NAME_FIELD, "Majestic Darkness"),
        )
    )
    assert text == 'Destroyed: CMDR MidnightWraith in "Majestic Darkness"'


def test_a_victim_with_no_ship_at_all_is_named_alone() -> None:
    assert _row_text(((VICTIM_NAME_FIELD, "MidnightWraith"),)) == (
        "Destroyed: CMDR MidnightWraith"
    )


def test_a_hull_without_a_commander_is_still_reported() -> None:
    text = _row_text(
        (
            (VICTIM_SHIP_FIELD, "Imperial Cutter"),
            (VICTIM_SHIP_NAME_FIELD, "Majestic Darkness"),
        )
    )
    assert text == 'Destroyed: Imperial Cutter "Majestic Darkness"'


def test_the_victim_wording_is_configurable_through_the_spec() -> None:
    labels = (
        ("label.death.victim_title", "Commander"),
        ("label.death.victim_in", "flying a"),
    )
    text = _row_text(
        (
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_FIELD, "Imperial Cutter"),
        ),
        labels,
    )
    assert text == "Destroyed: Commander MidnightWraith flying a Imperial Cutter"


def test_the_rebuy_charge_closes_the_row_when_one_was_paid() -> None:
    # No other figure in the report accounts for the rebuy.
    text = _row_text(
        (
            (VICTIM_NAME_FIELD, "MidnightWraith"),
            (VICTIM_SHIP_FIELD, "Imperial Cutter"),
            (REBUY_COST_FIELD, 11312783),
        )
    )
    assert text == (
        "Destroyed: CMDR MidnightWraith in Imperial Cutter " "(rebuy 11,312,783 Cr)"
    )


def test_a_death_with_no_rebuy_recorded_ends_at_the_victim() -> None:
    text = _row_text(((VICTIM_NAME_FIELD, "MidnightWraith"),))
    assert text == "Destroyed: CMDR MidnightWraith"


def test_the_killers_squadron_joins_their_ship_and_rank() -> None:
    text = _row_text(
        (
            ("KillerName", "Cmdr Russet Meles"),
            ("KillerShip_Localised", "Cobra Mk V"),
            ("KillerRank", "Elite"),
            (KILLER_SQUADRON_FIELD, "JOME"),
        )
    )
    assert text == "Killed by Cmdr Russet Meles (Cobra Mk V, Elite, JOME)"
