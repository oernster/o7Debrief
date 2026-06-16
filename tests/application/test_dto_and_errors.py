"""Tests for the application DTOs and error hierarchy."""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import (
    DebriefView,
    DomainSection,
    DomainStat,
    FooterView,
    HeaderView,
    HeadlineItem,
    Milestone,
    RankChange,
    TimelineCategory,
    TimelineEntry,
)
from o7debrief.application.dto.export_result import ExportResult
from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.errors import (
    ApplicationError,
    ConfigSchemaMismatchError,
)

# Contract key sets for each section of the to_context dict.
_HEADER_KEYS = {
    "commander",
    "ship",
    "ship_name",
    "session_start",
    "session_end",
    "duration",
    "start_system",
    "end_system",
    "systems_visited",
}
_HEADLINE_KEYS = {"label", "value_display", "delta_display", "delta_class"}
_DOMAIN_KEYS = {"key", "title", "icon", "stats", "note"}
_STAT_KEYS = {"label", "value_display"}
_TIMELINE_KEYS = {
    "time_display",
    "mode",
    "mode_label",
    "mode_tag",
    "icon",
    "text",
    "system",
}
_TIMELINE_CATEGORY_KEYS = {"key", "label", "icon", "count", "entries"}
_RANK_KEYS = {
    "ladder_title",
    "from_tier_name",
    "to_tier_name",
    "promoted",
    "note",
    "progress_pct",
}
_MILESTONE_KEYS = {"icon", "text"}
_FOOTER_KEYS = {
    "app_name",
    "app_version",
    "license",
    "generated",
    "journal_first",
    "journal_last",
}


def _sample_view() -> DebriefView:
    """Build a fully populated DebriefView for shape assertions."""
    return DebriefView(
        header=HeaderView(
            commander="Jameson",
            ship="Cobra",
            session_start="2026-06-15 10:00:00",
            session_end="2026-06-15 10:00:59",
            duration="0h 0m",
            start_system="Sol",
            end_system="Achenar",
            systems_visited="2",
        ),
        headline=(
            HeadlineItem(
                label="Net credits",
                value_display="100 Cr",
                delta_display="+100 Cr",
                delta_class="positive",
            ),
        ),
        domains=(
            DomainSection(
                key="travel",
                title="Travel",
                icon="rocket",
                stats=(DomainStat(label="Jumps", value_display="3"),),
                note="A note.",
            ),
        ),
        timeline=(
            TimelineEntry(
                time_display="10:00:00",
                mode="ship",
                mode_label="Ship",
                mode_tag="S",
                icon="rocket",
                text="Jumped.",
                system="Sol",
            ),
        ),
        ranks=(
            RankChange(
                ladder_title="Combat",
                from_tier_name="Novice",
                to_tier_name="Competent",
                promoted=True,
                note="",
                progress_pct=42,
            ),
        ),
        milestones=(Milestone(icon="medal", text="Promoted."),),
        footer=FooterView(
            app_name="o7Debrief",
            app_version="1",
            license="LGPL-3.0-or-later",
            generated="",
            journal_first="2026-06-15 10:00:00",
            journal_last="2026-06-15 10:00:59",
        ),
        timeline_categories=(
            TimelineCategory(
                key="travel",
                label="Travel",
                icon="rocket",
                count=1,
                entries=(
                    TimelineEntry(
                        time_display="10:00:00",
                        mode="ship",
                        mode_label="Ship",
                        mode_tag="S",
                        icon="rocket",
                        text="Jumped.",
                        system="Sol",
                    ),
                ),
            ),
        ),
    )


def test_to_context_yields_exact_contract_shape() -> None:
    context = _sample_view().to_context()

    assert set(context) == {
        "header",
        "headline",
        "domains",
        "timeline",
        "timeline_categories",
        "ranks",
        "milestones",
        "footer",
    }
    assert set(context["header"]) == _HEADER_KEYS
    assert set(context["footer"]) == _FOOTER_KEYS
    assert set(context["headline"][0]) == _HEADLINE_KEYS
    assert set(context["domains"][0]) == _DOMAIN_KEYS
    assert set(context["domains"][0]["stats"][0]) == _STAT_KEYS
    assert set(context["timeline"][0]) == _TIMELINE_KEYS
    assert set(context["timeline_categories"][0]) == _TIMELINE_CATEGORY_KEYS
    assert set(context["timeline_categories"][0]["entries"][0]) == _TIMELINE_KEYS
    assert set(context["ranks"][0]) == _RANK_KEYS
    assert set(context["milestones"][0]) == _MILESTONE_KEYS


def test_to_context_produces_plain_dicts_and_lists() -> None:
    context = _sample_view().to_context()

    assert isinstance(context["headline"], list)
    assert isinstance(context["domains"][0]["stats"], list)
    assert isinstance(context["header"], dict)
    assert context["ranks"][0]["promoted"] is True
    assert context["domains"][0]["note"] == "A note."


def test_empty_collections_yield_empty_lists() -> None:
    view = DebriefView(
        header=_sample_view().header,
        headline=(),
        domains=(),
        timeline=(),
        ranks=(),
        milestones=(),
        footer=_sample_view().footer,
    )

    context = view.to_context()

    assert context["headline"] == []
    assert context["domains"] == []
    assert context["timeline"] == []
    assert context["timeline_categories"] == []
    assert context["ranks"] == []
    assert context["milestones"] == []


def test_render_request_and_export_result_hold_tuples() -> None:
    request = RenderRequest(formats=("md", "html"), output_dir="/out")
    result = ExportResult(paths=("a.md", "b.html"))

    assert request.formats == ("md", "html")
    assert request.output_dir == "/out"
    assert result.paths == ("a.md", "b.html")


def test_rank_snapshot_holds_pairs() -> None:
    snapshot = RankSnapshot(
        commander_fid="F1",
        tiers=(("combat", 4),),
        pcts=(("combat", 30),),
        captured_iso="2026-06-15T10:00:00Z",
    )

    assert snapshot.commander_fid == "F1"
    assert snapshot.tiers == (("combat", 4),)
    assert snapshot.pcts == (("combat", 30),)
    assert snapshot.captured_iso == "2026-06-15T10:00:00Z"


def test_config_schema_mismatch_error_carries_versions() -> None:
    error = ConfigSchemaMismatchError(expected="1", actual="2")

    assert isinstance(error, ApplicationError)
    assert error.expected == "1"
    assert error.actual == "2"
    assert "expected '1'" in str(error)
    assert "got '2'" in str(error)
