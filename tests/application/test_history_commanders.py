"""A history holding two commanders reports one commander's levels.

Ship, balance, change and ranks are levels of a commander, not of a journal.
The history report once took its name from the first commander and every
level from whichever commander played last, so it showed one commander's
ship under another's name and a "change" that subtracted one commander's
balance from the other's. Which commander a history report should lead with
is an owner decision; what is pinned here is that the levels agree with the
name, so no figure ever spans two commanders.
"""

from __future__ import annotations

from o7debrief.application.services.rank_analyzer import RankAnalyzer
from o7debrief.domain.value_objects.commander_id import CommanderId
from tests.application.fakes import FakeExporter, FakeRankStore, event
from tests.application.service_builders import build_one_shot_service

_ALPHA_BALANCE = 1_000_000
_BRAVO_BALANCE = 50_000_000

_ALPHA_RUN = (
    event("Commander", 0, Name="Alpha", FID="F1"),
    event("LoadGame", 1, Commander="Alpha", FID="F1", Ship="sidewinder"),
    event("LoadGame", 2, Commander="Alpha", FID="F1", Credits=_ALPHA_BALANCE),
    event("Rank", 3, Combat=1),
    event("Shutdown", 4),
)
_BRAVO_RUN = (
    event("Commander", 5, Name="Bravo", FID="F2"),
    event("LoadGame", 6, Commander="Bravo", FID="F2", Ship="anaconda"),
    event("LoadGame", 7, Commander="Bravo", FID="F2", Credits=_BRAVO_BALANCE),
    event("Rank", 8, Combat=8),
    event("Shutdown", 9),
)


def test_every_history_level_belongs_to_the_named_commander() -> None:
    html = FakeExporter("html", b"")
    service = build_one_shot_service(
        event_batches=(_ALPHA_RUN, _BRAVO_RUN),
        store=FakeRankStore(),
        exporters=(html,),
    )

    service.debrief_all_history()

    (view,) = html.rendered
    assert view.header.commander.endswith("Alpha")
    assert "anaconda" not in view.header.ship.lower()
    values = " ".join(item.value_display for item in view.headline)
    deltas = " ".join(item.delta_display or "" for item in view.headline)
    assert f"{_ALPHA_BALANCE:,}" in values
    assert f"{_BRAVO_BALANCE:,}" not in values
    # Alpha stated one balance, so there is no change to report; above all
    # no figure subtracting one commander's balance from the other's.
    assert f"{_BRAVO_BALANCE - _ALPHA_BALANCE:,}" not in deltas
    assert [change.to_tier_name for change in view.ranks] != []
    assert all("Elite" not in change.to_tier_name for change in view.ranks)


def test_events_are_kept_for_the_commander_identified_before_them() -> None:
    alpha = CommanderId(fid="F1", name="Alpha")

    kept = RankAnalyzer().events_of(_ALPHA_RUN + _BRAVO_RUN, alpha)

    assert kept == _ALPHA_RUN


def test_a_single_commander_history_is_left_whole() -> None:
    # Events ahead of the first identity are the first commander's. With one
    # commander nothing is filtered at all.
    lead = (event("Rank", 0, Combat=2),)
    alpha = CommanderId(fid="F1", name="Alpha")
    history = lead + _ALPHA_RUN

    assert RankAnalyzer().events_of(history, alpha) == history
