"""OneShotDebriefService: produce a debrief for the most recent session.

This is the top application use case. It reads the latest session from the
journal, identifies the commander, reconciles rank progression against the
saved snapshot, builds the domain debrief, presents it and exports it,
persisting a fresh rank snapshot for next time. Every domain-touching step
is delegated to an injected collaborator, so this module imports only the
application layer and refers to the domain objects it passes through as
forward references read by duck typing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.errors import ApplicationError

if TYPE_CHECKING:
    from o7debrief.application.dto.export_result import ExportResult
    from o7debrief.application.ports.clock import Clock
    from o7debrief.application.ports.journal_source import JournalSource
    from o7debrief.application.ports.preferences_store import PreferencesStore
    from o7debrief.application.ports.rank_snapshot_store import RankSnapshotStore
    from o7debrief.application.services.debrief_builder import DebriefBuilder
    from o7debrief.application.services.debrief_export_service import (
        DebriefExportService,
    )
    from o7debrief.application.services.debrief_presenter import DebriefPresenter
    from o7debrief.application.services.rank_analyzer import RankAnalyzer
    from o7debrief.domain.value_objects.commander_id import CommanderId

__all__ = ["OneShotDebriefService"]


class OneShotDebriefService:
    """Runs the full read-build-present-export flow for the last session."""

    def __init__(
        self,
        journal_source: JournalSource,
        debrief_builder: DebriefBuilder,
        presenter: DebriefPresenter,
        export_service: DebriefExportService,
        preferences_store: PreferencesStore,
        rank_store: RankSnapshotStore,
        rank_analyzer: RankAnalyzer,
        clock: Clock,
    ) -> None:
        self._journal_source = journal_source
        self._debrief_builder = debrief_builder
        self._presenter = presenter
        self._export_service = export_service
        self._preferences_store = preferences_store
        self._rank_store = rank_store
        self._rank_analyzer = rank_analyzer
        self._clock = clock

    def debrief_last_session(
        self,
        commander_hint: CommanderId | None = None,
        request: RenderRequest | None = None,
    ) -> ExportResult:
        """Read the latest session, then build, present and export its debrief.

        ``commander_hint`` overrides commander detection from the events.
        ``request`` overrides the default formats and output directory.
        """
        events = self._journal_source.read_latest_session()
        commander = self._resolve_commander(events, commander_hint)
        snapshot = self._rank_store.load(commander)
        start_tiers, start_pcts = _snapshot_starts(snapshot)
        deltas, end_pcts = self._rank_analyzer.analyse(events, start_tiers, start_pcts)
        debrief = self._debrief_builder.build(commander, events, deltas)
        view = self._presenter.present(debrief)
        fresh = _fresh_snapshot(commander, deltas, end_pcts, self._clock.now_utc())
        self._rank_store.save(commander, fresh)
        return self._export_service.export(view, request or self._default_request())

    def debrief_all_history(
        self,
        commander_hint: CommanderId | None = None,
        request: RenderRequest | None = None,
    ) -> ExportResult:
        """Read all journal history to date, then build, present and export it.

        Unlike the last-session debrief this reads every recorded event. It
        loads the saved rank snapshot to present the rank diff against it but
        never saves a new one, so presenting the diff stays read-only and the
        all-history view cannot overwrite the last-session baseline. Handy for
        reviewing or for testing the app without playing a fresh session.
        """
        events = self._journal_source.read_all()
        commander = self._resolve_commander(events, commander_hint)
        snapshot = self._rank_store.load(commander)
        start_tiers, start_pcts = _snapshot_starts(snapshot)
        deltas, _end_pcts = self._rank_analyzer.analyse(events, start_tiers, start_pcts)
        debrief = self._debrief_builder.build(commander, events, deltas)
        view = self._presenter.present(debrief)
        return self._export_service.export(view, request or self._default_request())

    def _resolve_commander(
        self, events: tuple[object, ...], hint: CommanderId | None
    ) -> CommanderId:
        """Return the hint, else the detected commander, else raise."""
        if hint is not None:
            return hint
        detected = self._rank_analyzer.extract_commander(events)
        if detected is None:
            raise ApplicationError("No commander identity found in the session events.")
        return detected

    def _default_request(self) -> RenderRequest:
        """Return the default render request from the user's preferences.

        Both the export format and the output directory come from the saved
        preferences, so a debrief generated with no explicit request honours
        them. An empty output directory means the sink's default location.
        """
        preferences = self._preferences_store.load()
        return RenderRequest(
            formats=(preferences.export_format,),
            output_dir=preferences.output_dir,
        )


def _snapshot_starts(
    snapshot: RankSnapshot | None,
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    """Return the snapshot's start tiers and percentages, empty when absent."""
    if snapshot is None:
        return (), ()
    return snapshot.tiers, snapshot.pcts


def _fresh_snapshot(
    commander: CommanderId,
    deltas: tuple[object, ...],
    end_pcts: tuple[tuple[str, int], ...] | None,
    captured_iso: str,
) -> RankSnapshot:
    """Build a fresh snapshot from the session's closing rank state.

    Tiers come from the computed deltas' closing tiers (read by attribute);
    percentages come from the closing percentages when known, else empty.
    """
    tiers = tuple((delta.ladder.name.lower(), delta.to_tier) for delta in deltas)
    pcts = () if end_pcts is None else end_pcts
    return RankSnapshot(
        commander_fid=commander.fid,
        tiers=tiers,
        pcts=pcts,
        captured_iso=captured_iso,
    )
