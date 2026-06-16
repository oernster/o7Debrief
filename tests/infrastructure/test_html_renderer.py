"""Tests for HtmlDebriefExporter: self-contained, escaped, all sections."""

from __future__ import annotations

from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    MomentKind,
    RankLadder,
)
from o7debrief.infrastructure.render.html_renderer import HtmlDebriefExporter

# A moment credit value above the taxonomy big-payout threshold.
_BIG_PAYOUT_MOMENT = 2000000
# A jump magnitude above the long-jump threshold.
_LONG_JUMP = 60


def _present(debrief):
    return DebriefPresenter(spec(), number_format()).present(debrief)


def _populated_view():
    moments = (
        build.moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            1,
            magnitude=_LONG_JUMP,
            system="Sol",
        ),
        build.moment(
            MomentKind.BOUNTY,
            ActivityDomain.COMBAT,
            2,
            credits=_BIG_PAYOUT_MOMENT,
            system="Sol",
        ),
        build.moment(MomentKind.PROMOTION, ActivityDomain.MISSIONS, 3),
    )
    ranks = (
        build.rank_delta(
            RankLadder.COMBAT,
            from_tier=3,
            to_tier=4,
            promoted=True,
            start_pct=90,
            end_pct=10,
            growth_pct=None,
            tier_ups=1,
        ),
    )
    return _present(
        build.debrief(
            moments=moments,
            activity=build.full_activity(),
            ranks=ranks,
            net_credits=_BIG_PAYOUT_MOMENT,
        )
    )


def test_extension_is_html() -> None:
    assert HtmlDebriefExporter().extension == "html"


def test_render_returns_self_contained_html_bytes() -> None:
    out = HtmlDebriefExporter().render(_populated_view())

    assert isinstance(out, bytes)
    html = out.decode("utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    # Self-contained: styles inlined, no scripts and no external references.
    assert "<style>" in html
    assert "<script" not in html.lower()
    assert "http://" not in html and "https://" not in html


def test_render_includes_commander_metrics_and_sections() -> None:
    html = HtmlDebriefExporter().render(_populated_view()).decode("utf-8")

    assert "Jameson" in html
    assert "2,000,000" in html  # net credits, digit-grouped
    assert "Travel" in html  # a domain title
    assert "Rank progress" in html
    assert "Milestones" in html


def test_render_includes_the_ship_type_and_name() -> None:
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        ship="Krait Mk II",
        ship_name="Stardust",
    )

    html = HtmlDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "Krait Mk II" in html
    assert "Stardust" in html


def test_render_escapes_html_in_journal_values() -> None:
    moments = (
        build.moment(MomentKind.SCAN_BODY, ActivityDomain.EXPLORATION, 1, system="<x>"),
    )
    debrief = build.debrief(
        moments=moments,
        activity=build.full_activity(),
        start_system="<x>",
        end_system="<x>",
    )

    html = HtmlDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "&lt;x&gt;" in html
    assert "<x>" not in html


def test_render_omits_optional_sections_when_empty() -> None:
    debrief = build.debrief(
        moments=(), activity=ActivityRollup(modes_used=()), ranks=()
    )

    html = HtmlDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "Rank progress" not in html
    assert "Session log" not in html
    assert "Headline" in html  # the headline is always present


def test_render_includes_category_tabs_for_the_session_log() -> None:
    html = HtmlDebriefExporter().render(_populated_view()).decode("utf-8")

    # The All tab plus a per-category tab and its panel are present.
    assert 'id="logtab-all"' in html
    assert 'id="panel-all"' in html
    assert 'id="logtab-combat"' in html
    assert 'id="panel-combat"' in html
    # Still self-contained: the tabs are pure CSS, no scripts.
    assert "<script" not in html.lower()


def test_rank_progress_and_milestones_precede_the_session_log() -> None:
    html = HtmlDebriefExporter().render(_populated_view()).decode("utf-8")

    # Both summaries sit above the log so they are not lost beneath a long one.
    log_at = html.index("Session log")
    assert html.index("Rank progress") < log_at
    assert html.index("Milestones") < log_at


def test_render_shows_no_change_note_for_a_steady_rank() -> None:
    steady = build.rank_delta(
        RankLadder.EMPIRE,
        from_tier=14,
        to_tier=14,
        promoted=False,
        start_pct=0,
        end_pct=None,
        growth_pct=None,
        tier_ups=0,
    )
    debrief = build.debrief(moments=(), activity=build.full_activity(), ranks=(steady,))

    html = HtmlDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "(no change)" in html


def test_render_includes_a_rank_progress_bar() -> None:
    html = HtmlDebriefExporter().render(_populated_view()).decode("utf-8")

    assert "rank-bar" in html
    assert "width: 10%" in html  # combat is 10% toward the next tier
