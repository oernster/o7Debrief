"""The one-shot debrief service wired against fakes, shared across suites.

Every collaborator is real except the journal source, the stores, the clock
and the exporters, which are the hand-written fakes in ``fakes.py``. Kept in
one place so a suite that needs the service does not restate its wiring.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.debrief_export_service import (
    DebriefExportService,
)
from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.application.services.one_shot_debrief_service import (
    OneShotDebriefService,
)
from o7debrief.application.services.rank_analyzer import RankAnalyzer
from tests.application.fakes import (
    FakeJournalSource,
    FakePreferencesStore,
    FakeRankStore,
    FakeSink,
    FixedClock,
    number_format,
    spec,
)

CLOCK_ISO = "2026-06-15T12:00:00Z"


def build_one_shot_service(
    *,
    latest=(),
    all_events=(),
    event_batches=None,
    store: FakeRankStore,
    exporters,
    preferences_store=None,
    unreadable_lines: int = 0,
) -> OneShotDebriefService:
    """Return the service over a fake source holding the given events."""
    source = FakeJournalSource(
        latest=latest,
        all_events=all_events,
        event_batches=event_batches,
        unreadable_lines=unreadable_lines,
    )
    the_spec = spec()
    return OneShotDebriefService(
        journal_source=source,
        debrief_builder=DebriefBuilder(the_spec),
        presenter=DebriefPresenter(the_spec, number_format(), app_version="1.2.3"),
        export_service=DebriefExportService(
            exporters=exporters,
            sink=FakeSink(),
            clock=FixedClock(CLOCK_ISO),
        ),
        preferences_store=preferences_store or FakePreferencesStore(),
        rank_store=store,
        rank_analyzer=RankAnalyzer(),
        clock=FixedClock(CLOCK_ISO),
        spec=the_spec,
    )
