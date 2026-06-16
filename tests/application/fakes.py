"""Hand-written port fakes and domain-object builders for application tests.

The fakes implement the application ports by shape (the ports are Protocols)
and record their calls so tests can assert how the services drove them. The
builders construct real domain objects so the services run against the true
domain, never a mock of it. No infrastructure is imported here.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.dto.preferences import Preferences
from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.application.services.value_formatter import NumberFormat
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.domain.value_objects.event_time import EventTime

# Threshold values used across the tests, mirroring the taxonomy magnitudes.
LONG_JUMP_LY = 50.0
BIG_PAYOUT = 1000000
HIGH_VALUE_EXOBIO = 5000000

# A fixed schema version the fakes agree on by default.
SCHEMA_VERSION = "1"

# A base instant the time helper offsets from, kept as a recognisable date.
_BASE_ISO = "2026-06-15T10:00:"


def at(second: int) -> EventTime:
    """Return an EventTime at a given second within a fixed base minute."""
    return EventTime.parse(f"{_BASE_ISO}{second:02d}Z")


def event(event_type: str, second: int, **fields: object) -> RawEvent:
    """Build a RawEvent of a type at a second with arbitrary fields."""
    return RawEvent(
        event_type=event_type,
        event_time=at(second),
        fields=tuple(fields.items()),
    )


def commander() -> CommanderId:
    """Return a stable commander identity for tests."""
    return CommanderId(fid="F1234", name="Jameson")


def number_format() -> NumberFormat:
    """Return a NumberFormat mirroring the taxonomy [format] table."""
    return NumberFormat(
        credits_suffix="Cr",
        distance_suffix="ly",
        thousands=True,
        duration_format="{hours}h {minutes}m",
        time_format="%H:%M:%S",
        datetime_format="%Y-%m-%d %H:%M:%S",
    )


def spec(labels: tuple[tuple[str, str], ...] = ()) -> RollupSpec:
    """Return a RollupSpec with the taxonomy thresholds and given labels.

    Rules are empty by default; tests that build moments do so directly rather
    than through the moment factory, so no event-to-moment rules are needed here.
    """
    return RollupSpec(
        schema_version=SCHEMA_VERSION,
        rules=(),
        thresholds=ThresholdSet(
            long_jump_ly=LONG_JUMP_LY,
            big_payout_credits=BIG_PAYOUT,
            high_value_exobio_credits=HIGH_VALUE_EXOBIO,
        ),
        labels=labels,
    )


class FakeJournalSource:
    """A JournalSource whose returns are set per method by the test."""

    def __init__(
        self,
        all_events: tuple[RawEvent, ...] = (),
        latest: tuple[RawEvent, ...] = (),
        new_batches: tuple[tuple[tuple[RawEvent, ...], int], ...] = (),
    ) -> None:
        self._all = all_events
        self._latest = latest
        self._new_batches = list(new_batches)
        self.read_new_calls: list[int] = []

    def read_all(self) -> tuple[RawEvent, ...]:
        return self._all

    def read_latest_session(self) -> tuple[RawEvent, ...]:
        return self._latest

    def read_new(self, since_offset: int) -> tuple[tuple[RawEvent, ...], int]:
        self.read_new_calls.append(since_offset)
        if self._new_batches:
            return self._new_batches.pop(0)
        return (), since_offset


class FakeReleaseSource:
    """A ReleaseSource returning a preset latest version (or None)."""

    def __init__(self, latest: str | None = None) -> None:
        self._latest = latest

    def latest_version(self) -> str | None:
        return self._latest


class FakeConfigProvider:
    """A ConfigProvider returning a preset spec and expected version."""

    def __init__(self, the_spec: RollupSpec, expected_version: str) -> None:
        self._spec = the_spec
        self._expected = expected_version
        self.load_calls = 0

    def load(self) -> RollupSpec:
        self.load_calls += 1
        return self._spec

    def schema_version(self) -> str:
        return self._expected


class FakeExporter:
    """A DebriefExporter recording each render call and its view."""

    def __init__(self, extension: str, payload: bytes) -> None:
        self.extension = extension
        self._payload = payload
        self.rendered: list[DebriefView] = []

    def render(self, view: DebriefView) -> bytes:
        self.rendered.append(view)
        return self._payload


class FakeSink:
    """A DebriefSink recording writes and returning a synthesised path."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, bytes, str, str]] = []

    def write(
        self, name: str, content: bytes, suffix: str, output_dir: str = ""
    ) -> str:
        self.writes.append((name, content, suffix, output_dir))
        return f"{name}.{suffix}"


class FakeArchive:
    """A DebriefArchive returning a preset list of paths, newest first."""

    def __init__(self, paths: tuple[str, ...] = ()) -> None:
        self._paths = paths

    def count(self) -> int:
        return len(self._paths)

    def list_page(self, offset: int, limit: int) -> tuple[str, ...]:
        return self._paths[offset : offset + limit]


class FakeRankStore:
    """A RankSnapshotStore backed by an in-memory dict keyed by fid."""

    def __init__(self, preset: RankSnapshot | None = None) -> None:
        self._preset = preset
        self.saved: list[tuple[str, RankSnapshot]] = []
        self.load_calls: list[str] = []

    def load(self, commander: CommanderId) -> RankSnapshot | None:
        self.load_calls.append(commander.fid)
        return self._preset

    def save(self, commander: CommanderId, snapshot: RankSnapshot) -> None:
        self.saved.append((commander.fid, snapshot))


class FakePreferencesStore:
    """A PreferencesStore backed by an in-memory Preferences value."""

    def __init__(self, preferences: Preferences | None = None) -> None:
        self._preferences = preferences if preferences is not None else Preferences()
        self.saved: list[Preferences] = []

    def load(self) -> Preferences:
        return self._preferences

    def save(self, preferences: Preferences) -> None:
        self.saved.append(preferences)
        self._preferences = preferences


class FixedClock:
    """A Clock returning a fixed ISO string, recording each read."""

    def __init__(self, iso: str) -> None:
        self._iso = iso
        self.reads = 0

    def now_utc(self) -> str:
        self.reads += 1
        return self._iso
