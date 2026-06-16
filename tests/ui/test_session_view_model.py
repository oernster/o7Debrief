"""Tests for SessionViewModel: status exposure, polling and signal emission."""

from __future__ import annotations

from o7debrief.ui.view_models.session_view_model import SessionViewModel

from tests.ui.fakes import FakeRecorder

# The fake adds this many events per poll; mirrored here for the assertions.
_EVENTS_PER_POLL = 2


def test_initial_status_reflects_idle_recorder() -> None:
    """A fresh model exposes the recorder's idle status without polling."""
    recorder = FakeRecorder()
    model = SessionViewModel(recorder)

    assert model.is_recording is False
    assert model.event_count == 0
    assert "No session" in model.status_text
    assert recorder.poll_calls == 0


def test_refresh_polls_and_returns_new_headline() -> None:
    """Refreshing polls the recorder once and returns the updated headline."""
    recorder = FakeRecorder()
    model = SessionViewModel(recorder)

    headline = model.refresh()

    assert recorder.poll_calls == 1
    assert model.is_recording is True
    assert model.event_count == _EVENTS_PER_POLL
    assert headline == model.status_text
    assert str(_EVENTS_PER_POLL) in headline


def test_refresh_emits_status_changed_signal() -> None:
    """Each refresh emits status_changed carrying the new headline."""
    recorder = FakeRecorder()
    model = SessionViewModel(recorder)
    received: list[str] = []
    model.status_changed.connect(received.append)

    returned = model.refresh()

    assert received == [returned]


def test_repeated_refresh_accumulates_events() -> None:
    """Polling accumulates: two refreshes double the observed count."""
    recorder = FakeRecorder()
    model = SessionViewModel(recorder)

    model.refresh()
    model.refresh()

    assert recorder.poll_calls == 2
    assert model.event_count == _EVENTS_PER_POLL + _EVENTS_PER_POLL
