"""Tests for the SessionRecorder polling and status snapshot."""

from __future__ import annotations

from tests.application.fakes import FakeJournalSource, event

from o7debrief.application.services.session_recorder import SessionRecorder


def test_latest_session_events_reads_from_source() -> None:
    events = (event("LoadGame", 0), event("FSDJump", 1))
    source = FakeJournalSource(latest=events)
    recorder = SessionRecorder(source)

    assert recorder.latest_session_events() == events


def test_status_is_idle_before_any_events() -> None:
    recorder = SessionRecorder(FakeJournalSource())

    status = recorder.status()

    assert status.is_recording is False
    assert status.event_count == 0
    assert "No session" in status.headline


def test_poll_accumulates_new_events_and_tracks_offset() -> None:
    first = (event("LoadGame", 0),)
    second = (event("FSDJump", 1), event("Scan", 2))
    source = FakeJournalSource(
        new_batches=((first, 1), (second, 3)),
    )
    recorder = SessionRecorder(source)

    after_first = recorder.poll()
    after_second = recorder.poll()

    assert after_first == first
    assert after_second == first + second
    # The second poll resumes from the offset the first one returned.
    assert source.read_new_calls == [0, 1]


def test_status_reports_recording_after_polling() -> None:
    source = FakeJournalSource(new_batches=(((event("LoadGame", 0),), 1),))
    recorder = SessionRecorder(source)
    recorder.poll()

    status = recorder.status()

    assert status.is_recording is True
    assert status.event_count == 1
    assert "1 events" in status.headline


def test_poll_with_no_new_events_keeps_offset() -> None:
    source = FakeJournalSource()
    recorder = SessionRecorder(source)

    result = recorder.poll()

    assert result == ()
    assert source.read_new_calls == [0]
