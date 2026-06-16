"""MarkdownDebriefExporter: render a DebriefView as Discord/Reddit Markdown.

This adapter implements the application ``DebriefExporter`` port for the ``md``
format. It produces a compact Markdown report suited to pasting into Discord or
Reddit: a header, a fenced headline block, per-domain stat lists, a session
timeline tagged by control mode, any rank changes and milestones, and a footer.
It consumes only ``DebriefView.to_context()``; every value is already formatted.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.infrastructure.render.icons import emoji_for

__all__ = ["MarkdownDebriefExporter"]

# File-type suffix (no dot) this exporter produces; matched by the export
# service against the requested formats.
_EXTENSION = "md"
_ENCODING = "utf-8"
_NEWLINE = "\n"
_BLANK = ""

# Markdown tokens used when composing the report.
_FENCE = "```"
_BULLET = "- "
_ARROW = " -> "
# Separator before a rank's progress-to-next-tier percentage.
_PROGRESS_SEPARATOR = "|"

# Section headings, declared once so the wording lives in a single place.
_TITLE = "# Commander Mission Debrief"
_H_HEADLINE = "## Headline"
_H_ACTIVITY = "## Activity"
_H_LOG = "## Session Log"
_H_RANKS = "## Rank Progress"
_H_MILESTONES = "## Milestones"


def _header(lines: list[str], header: dict, footer: dict) -> None:
    """Append the report title and the session header block."""
    lines.append(_TITLE)
    lines.append(_BLANK)
    lines.append(f"**CMDR {header['commander']}** | {header['ship']}")
    lines.append(
        f"{header['session_start']} to {header['session_end']} "
        f"({header['duration']})"
    )
    lines.append(
        f"{header['start_system']}{_ARROW}{header['end_system']} | "
        f"{header['systems_visited']} systems visited"
    )
    lines.append(_BLANK)


def _headline(lines: list[str], headline: list[dict]) -> None:
    """Append the headline metrics as a fenced code block."""
    lines.append(_H_HEADLINE)
    lines.append(_FENCE)
    for item in headline:
        row = f"{item['label']}: {item['value_display']}"
        if item["delta_display"]:
            row += f" ({item['delta_display']})"
        lines.append(row)
    lines.append(_FENCE)
    lines.append(_BLANK)


def _domains(lines: list[str], domains: list[dict]) -> None:
    """Append a sub-section of stats for each active domain."""
    if not domains:
        return
    lines.append(_H_ACTIVITY)
    lines.append(_BLANK)
    for domain in domains:
        lines.append(f"### {emoji_for(domain['icon'])} {domain['title']}")
        for stat in domain["stats"]:
            lines.append(f"{_BULLET}{stat['label']}: {stat['value_display']}")
        if domain["note"]:
            lines.append(f"_{domain['note']}_")
        lines.append(_BLANK)


def _timeline(lines: list[str], timeline: list[dict]) -> None:
    """Append the chronological session log, tagged by control mode."""
    if not timeline:
        return
    lines.append(_H_LOG)
    lines.append(_BLANK)
    for entry in timeline:
        system = f" ({entry['system']})" if entry["system"] else _BLANK
        lines.append(
            f"{_BULLET}`{entry['time_display']}` "
            f"[{entry['mode_label']}] {entry['text']}{system}"
        )
    lines.append(_BLANK)


def _ranks(lines: list[str], ranks: list[dict]) -> None:
    """Append the full rank standing: promotions as moves, the rest steady."""
    if not ranks:
        return
    lines.append(_H_RANKS)
    lines.append(_BLANK)
    for rank in ranks:
        if rank["promoted"]:
            progression = f"{rank['from_tier_name']}{_ARROW}{rank['to_tier_name']}"
        else:
            progression = f"{rank['to_tier_name']} {rank['note']}"
        lines.append(
            f"{_BULLET}**{rank['ladder_title']}**: {progression} "
            f"{_PROGRESS_SEPARATOR} {rank['progress_pct']}%"
        )
    lines.append(_BLANK)


def _milestones(lines: list[str], milestones: list[dict]) -> None:
    """Append the milestone highlights, if any."""
    if not milestones:
        return
    lines.append(_H_MILESTONES)
    lines.append(_BLANK)
    for milestone in milestones:
        lines.append(f"{_BULLET}{emoji_for(milestone['icon'])} {milestone['text']}")
    lines.append(_BLANK)


def _footer(lines: list[str], footer: dict) -> None:
    """Append the footer: app identity and the journal span."""
    generated = f"Generated {footer['generated']} | " if footer["generated"] else _BLANK
    lines.append(
        f"_{footer['app_name']} v{footer['app_version']} | {footer['license']}_"
    )
    lines.append(
        f"_{generated}Journal {footer['journal_first']} to "
        f"{footer['journal_last']}_"
    )


class MarkdownDebriefExporter:
    """Renders a DebriefView into Markdown bytes (port: DebriefExporter)."""

    extension = _EXTENSION

    def render(self, view: DebriefView) -> bytes:
        """Render the view's context into Markdown bytes."""
        context = view.to_context()
        lines: list[str] = []
        _header(lines, context["header"], context["footer"])
        _headline(lines, context["headline"])
        _domains(lines, context["domains"])
        _ranks(lines, context["ranks"])
        _milestones(lines, context["milestones"])
        _timeline(lines, context["timeline"])
        _footer(lines, context["footer"])
        text = _NEWLINE.join(lines) + _NEWLINE
        return text.encode(_ENCODING)
