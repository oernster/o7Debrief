"""Conformance checks that each fake satisfies its application port.

Importing the port modules here exercises their declarations, and binding a
fake to each port-typed name documents (and, via the type checker, enforces)
that the hand-written fakes implement the Protocols the services depend on.
The Protocol method bodies are ellipses excluded from coverage; these tests
cover the class and signature lines that remain.
"""

from __future__ import annotations

from tests.application.fakes import (
    FakeArchive,
    FakeConfigProvider,
    FakeExporter,
    FakeJournalSource,
    FakePreferencesStore,
    FakeRankStore,
    FakeReleaseSource,
    FakeSink,
    FixedClock,
    spec,
)

from o7debrief.application.ports.clock import Clock
from o7debrief.application.ports.config_provider import ConfigProvider
from o7debrief.application.ports.debrief_archive import DebriefArchive
from o7debrief.application.ports.debrief_exporter import DebriefExporter
from o7debrief.application.ports.debrief_sink import DebriefSink
from o7debrief.application.ports.journal_source import JournalSource
from o7debrief.application.ports.preferences_store import PreferencesStore
from o7debrief.application.ports.rank_snapshot_store import RankSnapshotStore
from o7debrief.application.ports.release_source import ReleaseSource


def test_fakes_conform_to_their_ports() -> None:
    journal: JournalSource = FakeJournalSource()
    config: ConfigProvider = FakeConfigProvider(spec(), spec().schema_version)
    exporter: DebriefExporter = FakeExporter("md", b"")
    sink: DebriefSink = FakeSink()
    archive: DebriefArchive = FakeArchive()
    store: RankSnapshotStore = FakeRankStore()
    preferences: PreferencesStore = FakePreferencesStore()
    clock: Clock = FixedClock("2026-06-15T00:00:00Z")
    release: ReleaseSource = FakeReleaseSource("1.2.0")

    # Bound to their port types above; exercise one read on each to confirm
    # the shapes line up at runtime as well as for the type checker.
    assert journal.read_all() == ()
    assert config.schema_version() == spec().schema_version
    assert exporter.extension == "md"
    assert sink.write("n", b"x", "md") == "n.md"
    assert archive.count() == 0
    assert store.load(_AnyCommander()) is None
    assert preferences.load().export_format == "html"
    assert clock.now_utc() == "2026-06-15T00:00:00Z"
    assert release.latest_version() == "1.2.0"


class _AnyCommander:
    """A stand-in commander whose only used attribute is its fid."""

    fid = "F0"
