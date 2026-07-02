"""Tests for bounty rows naming the destroyed ship.

Since NPCs can fly any ship, a bounty row names its target from the journal
(Target_Localised where present, else the title-cased Target), covering ship
types and ship-launched fighters alike.
"""

from __future__ import annotations

from tests.application import domain_builders as build
from tests.application.fakes import at, number_format, spec

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)


def _presenter(labels: tuple[tuple[str, str], ...] = ()) -> DebriefPresenter:
    return DebriefPresenter(spec(labels), number_format())


def _bounty(detail: tuple) -> ConceptualMoment:
    return ConceptualMoment(
        kind=MomentKind.BOUNTY,
        domain=ActivityDomain.COMBAT,
        mode=ActivityMode.SHIP,
        occurred_at=at(1),
        label="BOUNTY",
        magnitude=0,
        credits_delta=Credits(0),
        detail=detail,
    )


def _row_text(detail: tuple, labels: tuple[tuple[str, str], ...] = ()) -> str:
    debrief = build.debrief(
        moments=(_bounty(detail),), activity=ActivityRollup(modes_used=())
    )
    return _presenter(labels).present(debrief).to_context()["timeline"][0]["text"]


def test_bounty_names_the_target_from_localised() -> None:
    text = _row_text(
        (("Target", "federation_dropship_mkii"), ("Target_Localised", "Federal Assault Ship"))
    )
    assert text == "Bounty on Federal Assault Ship"


def test_bounty_title_cases_a_bare_target() -> None:
    # A simple ship name carries no localised form; it is title-cased.
    assert _row_text((("Target", "mamba"),)) == "Bounty on Mamba"


def test_bounty_without_a_target_reads_as_a_bare_bounty() -> None:
    assert _row_text(()) == "Bounty"


def test_bounty_wording_is_configurable() -> None:
    labels = (("label.combat.bounty_on", "Destroyed a"),)
    assert _row_text((("Target", "vulture"),), labels) == "Destroyed a Vulture"
