"""Tests for the ship-launched-vessel rows in the timeline presenter.

A deploy, dock or loss row names the vessel type, read from the moment detail
(the journal's SRVType_Localised, or the type the moment factory recovered for a
deployment). These cover each verb, the generic fallback and configurability.
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


def _slv(kind: MomentKind, detail: tuple) -> ConceptualMoment:
    return ConceptualMoment(
        kind=kind,
        domain=ActivityDomain.SLV,
        mode=ActivityMode.SHIP,
        occurred_at=at(1),
        label=kind.name,
        magnitude=0,
        credits_delta=Credits(0),
        detail=detail,
    )


def _row_text(
    kind: MomentKind, detail: tuple, labels: tuple[tuple[str, str], ...] = ()
) -> str:
    debrief = build.debrief(
        moments=(_slv(kind, detail),), activity=ActivityRollup(modes_used=())
    )
    return _presenter(labels).present(debrief).to_context()["timeline"][0]["text"]


_NOMAD = (("VesselType", "Nomad"),)


def test_deploy_names_the_vessel_type() -> None:
    assert _row_text(MomentKind.SLV_DEPLOY, _NOMAD) == "Deployed the Nomad"


def test_dock_names_the_vessel_type() -> None:
    assert _row_text(MomentKind.SLV_DOCK, _NOMAD) == "Docked the Nomad"


def test_loss_names_the_vessel_type() -> None:
    assert _row_text(MomentKind.SLV_DESTROYED, _NOMAD) == "Lost the Nomad"


def test_fighter_rows_name_the_fighter_type() -> None:
    gelid = (("VesselType", "Gelid"),)
    assert _row_text(MomentKind.SLF_DEPLOY, gelid) == "Deployed the Gelid"
    assert _row_text(MomentKind.SLF_DOCK, gelid) == "Docked the Gelid"
    assert _row_text(MomentKind.SLF_DESTROYED, gelid) == "Lost the Gelid"


def test_unknown_vessel_type_falls_back_to_a_generic_phrase() -> None:
    assert _row_text(MomentKind.SLV_DEPLOY, ()) == "Deployed the ship-launched vessel"


def test_unknown_fighter_type_falls_back_to_a_generic_fighter_phrase() -> None:
    assert _row_text(MomentKind.SLF_DEPLOY, ()) == "Deployed the ship-launched fighter"


def test_blank_vessel_type_falls_back_to_generic() -> None:
    assert (
        _row_text(MomentKind.SLV_DOCK, (("VesselType", "  "),))
        == "Docked the ship-launched vessel"
    )


def test_vehicle_wording_is_configurable() -> None:
    labels = (
        ("label.vehicle.deployed", "Launched"),
        ("label.slv.vessel", "SLV"),
    )
    assert _row_text(MomentKind.SLV_DEPLOY, (), labels) == "Launched SLV"
