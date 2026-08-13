"""Builders for whole-history views, used by the paging and bundle tests.

A history debrief differs from a session one only in how much it holds and how
far it spans, so these build real moments at real instants across months and
present them through the real presenter. Nothing is faked but the journal.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

__all__ = ["history_options", "moment_at", "spread", "view_of"]

# The domains the generated history cycles through, so every fixture holds
# several categories and the per-category assertions have something to bite on.
_CYCLE = (
    (ActivityDomain.TRAVEL, MomentKind.JUMP),
    (ActivityDomain.COMBAT, MomentKind.BOUNTY),
    (ActivityDomain.MISSIONS, MomentKind.PROMOTION),
    (ActivityDomain.SRV, MomentKind.SRV_DEPLOY),
)
# Journal instant format, matching what Elite Dangerous writes.
_JOURNAL_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def moment_at(
    iso: str,
    domain: ActivityDomain = ActivityDomain.TRAVEL,
    kind: MomentKind = MomentKind.JUMP,
) -> ConceptualMoment:
    """Build one moment at an explicit UTC instant."""
    return ConceptualMoment(
        kind=kind,
        domain=domain,
        mode=ActivityMode.SHIP,
        occurred_at=EventTime.parse(iso),
        label=kind.name,
        magnitude=0.0,
        credits_delta=Credits(0),
        coins_delta=Credits(0),
        detail=(),
        text_template="",
    )


def spread(
    count: int, start: str = "2025-09-01T08:00:00Z", minutes: int = 47
) -> tuple[ConceptualMoment, ...]:
    """Build ``count`` moments at a fixed spacing from ``start``, oldest first.

    The spacing is deliberately not a factor of a day, so the generated rows
    fall across every hour and cross both day and month boundaries, which is
    what the paging and separator assertions need.
    """
    base = datetime.fromisoformat(start)
    built = []
    for index in range(count):
        domain, kind = _CYCLE[index % len(_CYCLE)]
        when = (base + timedelta(minutes=index * minutes)).astimezone(UTC)
        built.append(moment_at(when.strftime(_JOURNAL_FORMAT), domain, kind))
    return tuple(built)


def view_of(moments: tuple[ConceptualMoment, ...]) -> DebriefView:
    """Present a debrief holding exactly these moments."""
    debrief = build.debrief(moments=moments, activity=build.full_activity())
    return DebriefPresenter(spec(), number_format(), app_version="1.2.3").present(
        debrief
    )


def history_options(**overrides) -> HistoryOptions:
    """Return the taxonomy's history limits, with any field overridden."""
    defaults = {
        "entries_per_page": 1000,
        "page_bytes_target": 512000,
        "bytes_per_entry_estimate": 400,
        "single_file": False,
        "single_file_max_entries": 2000,
        "truncation_notice_format": (
            "Showing the most recent {shown} log entries. "
            "{omitted} older entries are not in this file."
        ),
        "rollup_enabled": False,
        "rollup_after_days": 90,
        "rollup_text_format": "{count} {label} entries",
    }
    return HistoryOptions(**{**defaults, **overrides})
