"""End-to-end tests for the OneShotDebriefService flow."""

from __future__ import annotations

import pytest

from tests.application.fakes import (
    FakeExporter,
    FakeJournalSource,
    FakePreferencesStore,
    FakeRankStore,
    FixedClock,
    commander,
    event,
    number_format,
    spec,
)

from o7debrief.application.dto.preferences import FORMAT_MARKDOWN, Preferences
from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.errors import ApplicationError
from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.debrief_export_service import (
    DebriefExportService,
)
from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.application.services.one_shot_debrief_service import (
    OneShotDebriefService,
)
from o7debrief.application.services.rank_analyzer import RankAnalyzer

_CLOCK_ISO = "2026-06-15T12:00:00Z"


def _session_events():
    """A minimal but complete session with identity, ranks and a shutdown."""
    return (
        event("Commander", 0, Name="Jameson", FID="F1234"),
        event("LoadGame", 1, Ship="cobramkiii"),
        event("Promotion", 2, Combat=4),
        event("Progress", 3, Combat=15),
        event("Shutdown", 4),
    )


def _history_events():
    """All-history events spanning two sessions: identity, promotion, bounty."""
    return (
        event("Commander", 0, Name="Jameson", FID="F1234"),
        event("LoadGame", 1, Ship="cobramkiii"),
        event("Promotion", 2, Combat=4),
        event("Shutdown", 3),
        event("LoadGame", 4, Ship="cobramkiii"),
        event("Bounty", 5, Target="Pirate", TotalReward=500000),
        event("Shutdown", 6),
    )


class _RecordingSink:
    """A minimal sink returning a deterministic path per write."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, bytes, str, str]] = []

    def write(
        self, name: str, content: bytes, suffix: str, output_dir: str = ""
    ) -> str:
        self.writes.append((name, content, suffix, output_dir))
        return f"{name}.{suffix}"


def _build_service(
    *,
    latest=(),
    all_events=(),
    store: FakeRankStore,
    exporters,
    preferences_store=None,
):
    source = FakeJournalSource(latest=latest, all_events=all_events)
    the_spec = spec()
    return OneShotDebriefService(
        journal_source=source,
        debrief_builder=DebriefBuilder(the_spec),
        presenter=DebriefPresenter(the_spec, number_format()),
        export_service=DebriefExportService(
            exporters=exporters,
            sink=_RecordingSink(),
            clock=FixedClock(_CLOCK_ISO),
        ),
        preferences_store=preferences_store or FakePreferencesStore(),
        rank_store=store,
        rank_analyzer=RankAnalyzer(),
        clock=FixedClock(_CLOCK_ISO),
    )


def test_debrief_last_session_defaults_to_the_html_format() -> None:
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    html = FakeExporter("html", b"<h1>debrief</h1>")
    service = _build_service(
        latest=_session_events(), store=store, exporters=(md, html)
    )

    result = service.debrief_last_session()

    # The default preference is HTML, so only the HTML format is written.
    assert len(result.paths) == 1
    assert len(html.rendered) == 1
    assert len(md.rendered) == 0
    # The commander was detected from the events and a fresh snapshot saved.
    assert store.load_calls == ["F1234"]
    assert len(store.saved) == 1
    saved_fid, snapshot = store.saved[0]
    assert saved_fid == "F1234"
    assert snapshot.tiers == (("combat", 4),)
    assert snapshot.pcts == (("combat", 15),)
    assert snapshot.captured_iso == _CLOCK_ISO


def test_debrief_last_session_honours_the_markdown_preference() -> None:
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    html = FakeExporter("html", b"<h1>debrief</h1>")
    service = _build_service(
        latest=_session_events(),
        store=store,
        exporters=(md, html),
        preferences_store=FakePreferencesStore(
            Preferences(export_format=FORMAT_MARKDOWN)
        ),
    )

    result = service.debrief_last_session()

    # The Markdown preference writes only the Markdown format.
    assert len(result.paths) == 1
    assert len(md.rendered) == 1
    assert len(html.rendered) == 0


def test_debrief_last_session_honours_commander_hint_and_request() -> None:
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    # No identity events; the hint must supply the commander.
    latest = (event("FSDJump", 0, StarSystem="Sol"), event("Shutdown", 1))
    service = _build_service(latest=latest, store=store, exporters=(md,))
    request = RenderRequest(formats=("md",), output_dir="/custom")

    result = service.debrief_last_session(commander_hint=commander(), request=request)

    assert len(result.paths) == 1
    assert store.load_calls == [commander().fid]
    assert store.saved[0][0] == commander().fid


def test_debrief_last_session_uses_loaded_snapshot_as_start() -> None:
    preset = RankSnapshot(
        commander_fid="F1234",
        tiers=(("combat", 3),),
        pcts=(("combat", 5),),
        captured_iso="2026-06-14T00:00:00Z",
    )
    store = FakeRankStore(preset=preset)
    md = FakeExporter("md", b"# debrief")
    service = _build_service(latest=_session_events(), store=store, exporters=(md,))

    service.debrief_last_session(request=RenderRequest(("md",), "/out"))

    # The saved snapshot reflects the session close (tier 4, 15 percent).
    _, snapshot = store.saved[0]
    assert snapshot.tiers == (("combat", 4),)
    assert snapshot.pcts == (("combat", 15),)


def test_debrief_last_session_raises_without_a_commander() -> None:
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    # No identity events and no hint leaves the commander unresolved.
    latest = (event("FSDJump", 0, StarSystem="Sol"), event("Shutdown", 1))
    service = _build_service(latest=latest, store=store, exporters=(md,))

    with pytest.raises(ApplicationError):
        service.debrief_last_session()


def test_debrief_last_session_without_progress_saves_empty_pcts() -> None:
    # A promotion but no Progress event: closing percentages are unknown, so
    # the saved snapshot carries empty percentages (the None branch).
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    latest = (
        event("Commander", 0, Name="Jameson", FID="F1234"),
        event("Promotion", 1, Combat=4),
        event("Shutdown", 2),
    )
    service = _build_service(latest=latest, store=store, exporters=(md,))

    service.debrief_last_session(request=RenderRequest(("md",), "/out"))

    _, snapshot = store.saved[0]
    assert snapshot.tiers == (("combat", 4),)
    assert snapshot.pcts == ()


def test_debrief_all_history_loads_snapshot_for_the_diff_but_never_saves() -> None:
    # A saved snapshot below the current tier makes the rank diff real
    # (combat 3 -> 4), so the rank section should appear in the report.
    preset = RankSnapshot(
        commander_fid="F1234",
        tiers=(("combat", 3),),
        pcts=(),
        captured_iso="2026-06-14T00:00:00Z",
    )
    store = FakeRankStore(preset=preset)
    md = FakeExporter("md", b"# debrief")
    html = FakeExporter("html", b"<h1>debrief</h1>")
    # latest is empty on purpose: had the use case read the latest session it
    # would find no events and fail to resolve a commander. It must read all.
    service = _build_service(
        latest=(),
        all_events=_history_events(),
        store=store,
        exporters=(md, html),
    )

    result = service.debrief_all_history()

    # The default preference is HTML, so one HTML report is produced.
    assert len(result.paths) == 1
    assert len(html.rendered) == 1
    assert len(md.rendered) == 0
    # The snapshot is loaded so the rank diff can be presented...
    assert store.load_calls == ["F1234"]
    # ...but it is never saved, so the last-session baseline is preserved.
    assert store.saved == []
    # ...and the resulting rank change appears in the rendered view.
    assert html.rendered[0].ranks != ()


def test_debrief_all_history_honours_an_explicit_request() -> None:
    store = FakeRankStore()
    md = FakeExporter("md", b"# debrief")
    service = _build_service(all_events=_history_events(), store=store, exporters=(md,))

    result = service.debrief_all_history(request=RenderRequest(("md",), "/out"))

    assert len(result.paths) == 1
    assert len(md.rendered) == 1
    assert store.saved == []


def test_default_request_uses_the_preferred_output_dir() -> None:
    store = FakeRankStore()
    service = _build_service(
        latest=_session_events(),
        store=store,
        exporters=(FakeExporter("html", b"<h1>debrief</h1>"),),
        preferences_store=FakePreferencesStore(Preferences(output_dir="D:/Debriefs")),
    )

    request = service._default_request()

    assert request.formats == ("html",)
    assert request.output_dir == "D:/Debriefs"
