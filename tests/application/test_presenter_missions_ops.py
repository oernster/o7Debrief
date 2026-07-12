"""Tests for Operations/Merc-Coins support in the missions presenter.

A completed mission (an Operation among them) names itself and its faction in
the timeline, and surfaces any Merc Coins reward on the row. The missions domain
section carries the credit and the Merc Coins totals as separate stats.

The Merc Coins field name is configured in the taxonomy (new game content absent
from the published schema); these tests exercise the mechanism with a stand-in
name, independent of the eventual live journal key.
"""

from __future__ import annotations

from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup, MissionRollup
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind


def _presenter(labels: tuple[tuple[str, str], ...] = ()) -> DebriefPresenter:
    return DebriefPresenter(spec(labels), number_format())


def _row_text(
    detail: tuple,
    *,
    coins: int = 0,
    labels: tuple[tuple[str, str], ...] = (),
) -> str:
    moment = build.moment(
        MomentKind.MISSION_COMPLETE,
        ActivityDomain.MISSIONS,
        1,
        coins=coins,
        detail=detail,
    )
    debrief = build.debrief(
        moments=(moment,), activity=ActivityRollup(modes_used=())
    )
    return _presenter(labels).present(debrief).to_context()["timeline"][0]["text"]


def test_row_names_the_operation_faction_and_coins() -> None:
    detail = (
        ("LocalisedName", "Infiltrate the compound"),
        ("Faction", "Fong Wang Limited"),
    )
    text = _row_text(detail, coins=500)
    assert text == "Completed Infiltrate the compound for Fong Wang Limited (+500 Merc Coins)"


def test_row_prefers_localised_name_but_falls_back_to_the_raw_name() -> None:
    detail = (("Name", "Mission_Operation_Infiltration"), ("Faction", "Fong Wang"))
    assert _row_text(detail) == "Completed Mission_Operation_Infiltration for Fong Wang"


def test_row_without_a_name_reads_as_a_generic_mission() -> None:
    assert _row_text((("Faction", "Fong Wang"),)) == "Completed a mission for Fong Wang"


def test_row_without_a_faction_names_only_the_mission() -> None:
    assert _row_text((("LocalisedName", "Escort duty"),)) == "Completed Escort duty"


def test_row_omits_the_coin_suffix_when_no_coins_were_paid() -> None:
    detail = (("LocalisedName", "Courier run"), ("Faction", "Fong Wang"))
    assert _row_text(detail, coins=0) == "Completed Courier run for Fong Wang"


def test_row_wording_is_configurable() -> None:
    labels = (
        ("label.missions.completed_verb", "Finished"),
        ("label.missions.for", "on behalf of"),
    )
    detail = (("LocalisedName", "Recon"), ("Faction", "Fong Wang"))
    assert _row_text(detail, labels=labels) == "Finished Recon on behalf of Fong Wang"


def test_missions_section_carries_credit_and_merc_coin_totals() -> None:
    activity = ActivityRollup(
        missions=MissionRollup(
            completed=2, rewards=Credits(20000), coin_rewards=Credits(750)
        ),
        modes_used=(),
    )
    debrief = build.debrief(moments=(), activity=activity)

    context = _presenter().present(debrief).to_context()

    section = context["domains"][0]
    assert section["key"] == "missions"
    stats = {stat["label"]: stat["value_display"] for stat in section["stats"]}
    assert stats["Completed"] == "2"
    assert stats["Rewards"] == "20,000 Cr"
    assert stats["Merc Coins"] == "750 Merc Coins"
