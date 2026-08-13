"""Tests for the rank percentage as a level rather than a reading of zero.

A percentage persists until the game states a new one, so a session that
stated none carries the last known reading forward and shows no growth. These
cover the carry-forward, the promotion that cannot carry one and the standing
that was never recorded at all.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.enums import RankLadder
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

# A recorded standing plus the tier it was earned in.
_KNOWN_PCT = 73
_TIER = 14


def _row(
    *,
    start_pct: int | None,
    end_pct: int | None,
    promoted: bool = False,
    from_tier: int = _TIER,
) -> dict:
    delta = build.rank_delta(
        RankLadder.EMPIRE,
        from_tier=from_tier,
        to_tier=_TIER,
        promoted=promoted,
        start_pct=start_pct,
        end_pct=end_pct,
        growth_pct=None,
        tier_ups=_TIER - from_tier,
    )
    debrief = build.debrief(
        moments=(), activity=ActivityRollup(modes_used=()), ranks=(delta,)
    )
    view = DebriefPresenter(spec(), number_format(), app_version="1.2.3").present(
        debrief
    )
    return view.to_context()["ranks"][0]


def test_this_periods_reading_is_shown_when_the_journal_stated_one() -> None:
    row = _row(start_pct=10, end_pct=_KNOWN_PCT)
    assert row["progress_pct"] == _KNOWN_PCT
    assert row["progress_display"] == "73%"


def test_the_last_known_reading_carries_forward_when_none_was_stated() -> None:
    # The standing did not move, so the previous reading is still the truth.
    row = _row(start_pct=_KNOWN_PCT, end_pct=None)
    assert row["progress_pct"] == _KNOWN_PCT
    assert row["progress_display"] == "73%"


def test_a_standing_never_recorded_reads_as_no_reading() -> None:
    row = _row(start_pct=None, end_pct=None)
    assert row["progress_pct"] is None
    assert row["progress_display"] == "No reading"


def test_a_promotion_without_a_new_reading_does_not_carry_the_old_tiers() -> None:
    # The carried figure was earned in the tier just left, so it cannot stand.
    row = _row(start_pct=_KNOWN_PCT, end_pct=None, promoted=True, from_tier=_TIER - 1)
    assert row["progress_pct"] is None
    assert row["progress_display"] == "No reading"


def test_the_no_reading_wording_is_configurable_through_the_spec() -> None:
    delta = build.rank_delta(
        RankLadder.EMPIRE,
        from_tier=_TIER,
        to_tier=_TIER,
        promoted=False,
        start_pct=None,
        end_pct=None,
        growth_pct=None,
        tier_ups=0,
    )
    debrief = build.debrief(
        moments=(), activity=ActivityRollup(modes_used=()), ranks=(delta,)
    )
    labels = (("label.rank.no_reading", "Unrecorded"),)
    view = DebriefPresenter(spec(labels), number_format(), app_version="1.2.3").present(
        debrief
    )
    assert view.to_context()["ranks"][0]["progress_display"] == "Unrecorded"
