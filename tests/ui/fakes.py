"""Fake application collaborators for the ui tests.

These stand in for the application services the ui depends on. They implement
only the shape the ui uses (the application defines its services as concrete
classes, but the ui consumes them by attribute access, so a fake suffices) and
record their calls so a test can assert how the ui drove them. No real domain
or infrastructure is imported here.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.application.dto.export_result import ExportResult

# Headlines mirroring the recorder's own wording, used by the fake recorder.
_IDLE_HEADLINE = "No session recorded yet."
_RECORDING_HEADLINE = "Recording session: {count} events."
# Number of events each poll adds, so a test can observe accumulation.
_EVENTS_PER_POLL = 2
# Starting event count before any poll.
_START_COUNT = 0


@dataclass(frozen=True, slots=True)
class FakeStatus:
    """A stand-in for the recorder's SessionStatus snapshot."""

    is_recording: bool
    event_count: int
    headline: str


class FakeRecorder:
    """A SessionRecorder stand-in whose count grows on each poll.

    ``poll`` returns the preset event tuple for each successive call (and an
    empty tuple once the presets run out), so a test can feed a sequence of
    journal snapshots through the view model without any real journal.
    """

    def __init__(self, poll_results: tuple[tuple[object, ...], ...] = ()) -> None:
        self._count = _START_COUNT
        self.poll_calls = 0
        self._poll_results = poll_results

    def poll(self) -> tuple[object, ...]:
        """Pretend to read new events, growing the running count."""
        index = self.poll_calls
        self.poll_calls += 1
        self._count += _EVENTS_PER_POLL
        if index < len(self._poll_results):
            return self._poll_results[index]
        return ()

    def status(self) -> FakeStatus:
        """Return a status snapshot reflecting the current count."""
        recording = self._count > _START_COUNT
        if recording:
            headline = _RECORDING_HEADLINE.format(count=self._count)
        else:
            headline = _IDLE_HEADLINE
        return FakeStatus(
            is_recording=recording,
            event_count=self._count,
            headline=headline,
        )


class FakeOneShot:
    """An OneShotDebriefService stand-in returning a preset result.

    When ``error`` is set, ``debrief_last_session`` raises it instead, so a
    test can drive the controller's failure path. Each call is counted.
    """

    def __init__(
        self,
        result: ExportResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result if result is not None else ExportResult(paths=())
        self._error = error
        self.calls = 0
        self.history_calls = 0

    def debrief_last_session(self) -> ExportResult:
        """Return the preset result, or raise the preset error."""
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result

    def debrief_all_history(self) -> ExportResult:
        """Return the preset result for the all-history path, or raise."""
        self.history_calls += 1
        if self._error is not None:
            raise self._error
        return self._result


class RecordingOpener:
    """A callable that records every path it was asked to open."""

    def __init__(self) -> None:
        self.opened: list[str] = []

    def __call__(self, path: str) -> bool:
        self.opened.append(path)
        return True


class FakeArchive:
    """A DebriefArchive returning a preset list of paths, newest first.

    The list is public so a test can replace it to mimic a debrief landing on
    disk between calls.
    """

    def __init__(self, paths: tuple[str, ...] = ()) -> None:
        self.paths = paths

    def count(self) -> int:
        return len(self.paths)

    def list_page(self, offset: int, limit: int) -> tuple[str, ...]:
        return self.paths[offset : offset + limit]
