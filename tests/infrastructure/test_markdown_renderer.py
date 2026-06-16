"""Tests for MarkdownDebriefExporter: headings, fenced block, mode tags."""

from __future__ import annotations

from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    BeatKind,
    RankLadder,
)
from o7debrief.infrastructure.render.markdown_renderer import MarkdownDebriefExporter

# A beat credit value above the taxonomy big-payout threshold.
_BIG_PAYOUT_BEAT = 2000000


def _present(debrief):
    return DebriefPresenter(spec(), number_format()).present(debrief)


def _populated_view():
    beats = (
        build.beat(BeatKind.JUMP, ActivityDomain.TRAVEL, 1, magnitude=60, system="Sol"),
        build.beat(
            BeatKind.BOUNTY,
            ActivityDomain.COMBAT,
            2,
            credits=_BIG_PAYOUT_BEAT,
            system="Sol",
        ),
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
            beats=beats,
            activity=build.full_activity(),
            ranks=ranks,
            net_credits=_BIG_PAYOUT_BEAT,
        )
    )


def test_extension_is_md() -> None:
    assert MarkdownDebriefExporter().extension == "md"


def test_render_has_headings_and_fenced_headline() -> None:
    md = MarkdownDebriefExporter().render(_populated_view()).decode("utf-8")

    assert md.startswith("# Commander Mission Debrief")
    assert "## Headline" in md
    assert "```" in md  # the headline is a fenced block
    assert "CMDR Jameson" in md
    assert "2,000,000" in md


def test_render_includes_the_ship_type_and_name() -> None:
    debrief = build.debrief(
        beats=(),
        activity=ActivityRollup(modes_used=()),
        ship="Krait Mk II",
        ship_name="Stardust",
    )

    md = MarkdownDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "Krait Mk II" in md
    assert "Stardust" in md


def test_render_tags_timeline_with_mode_label() -> None:
    md = MarkdownDebriefExporter().render(_populated_view()).decode("utf-8")

    assert "## Session Log" in md
    assert "[Ship]" in md  # control-mode label tag on a beat


def test_render_includes_rank_progress_when_present() -> None:
    md = MarkdownDebriefExporter().render(_populated_view()).decode("utf-8")

    assert "## Rank Progress" in md


def test_rank_progress_and_milestones_precede_the_session_log() -> None:
    md = MarkdownDebriefExporter().render(_populated_view()).decode("utf-8")

    # Both summaries sit above the log so they are not lost beneath a long one.
    log_at = md.index("## Session Log")
    assert md.index("## Rank Progress") < log_at
    assert md.index("## Milestones") < log_at


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
    debrief = build.debrief(beats=(), activity=build.full_activity(), ranks=(steady,))

    md = MarkdownDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "(no change)" in md


def test_render_includes_rank_progress_percentage() -> None:
    md = MarkdownDebriefExporter().render(_populated_view()).decode("utf-8")

    assert "10%" in md  # combat is 10% toward the next tier


def test_render_omits_optional_sections_when_empty() -> None:
    debrief = build.debrief(beats=(), activity=ActivityRollup(modes_used=()), ranks=())

    md = MarkdownDebriefExporter().render(_present(debrief)).decode("utf-8")

    assert "## Rank Progress" not in md
    assert "## Session Log" not in md
    assert "## Headline" in md
