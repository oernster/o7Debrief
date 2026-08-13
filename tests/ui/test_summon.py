"""Tests for the summon route: the marker, its consumption and the watcher.

The marker lives in the per-user lock directory, so every test points the
environment variables that name that directory at a temporary one; nothing here
touches the real %LOCALAPPDATA% or an XDG runtime directory, so no test can
collide with a running app.

The watcher is driven by a real QTimer on a short interval and a real event loop
is run, rather than by reaching in and firing the timeout by hand. That way the
test proves the wiring a running app depends on. A nested loop is used rather
than ``processEvents``, which returns as soon as the queue is empty and so never
waits for a timer that has not come due yet.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from o7debrief.ui.tray.summon import SummonRequest, SummonWatcher

# Environment variables the lock directory is resolved from.
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG_RUNTIME = "XDG_RUNTIME_DIR"
_ENV_XDG_CACHE = "XDG_CACHE_HOME"
_ENV_FLATPAK_ID = "FLATPAK_ID"

# Timer interval used by the watcher tests. The waits are expressed as multiples
# of it: a test expecting the handler to run stops the loop the moment it does
# and only needs a generous ceiling for a loaded machine, while a test expecting
# silence has to sit through several polls to have proved anything.
_TEST_INTERVAL_MS = 10
_SUMMON_CEILING_INTERVALS = 100
_QUIET_INTERVALS = 8
_SUMMON_CEILING_MS = _TEST_INTERVAL_MS * _SUMMON_CEILING_INTERVALS
_QUIET_WAIT_MS = _TEST_INTERVAL_MS * _QUIET_INTERVALS


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every per-user base the marker might use at a temporary directory."""
    target = str(tmp_path)
    monkeypatch.setenv(_ENV_LOCALAPPDATA, target)
    monkeypatch.setenv(_ENV_XDG_RUNTIME, target)
    monkeypatch.setenv(_ENV_XDG_CACHE, target)
    monkeypatch.delenv(_ENV_FLATPAK_ID, raising=False)


def _run_for(milliseconds: int) -> QEventLoop:
    """Return an event loop that quits on its own after the given time.

    The loop is returned rather than run so a caller can also quit it early,
    which is how a test that expects the handler to fire finishes in a few
    milliseconds instead of sitting out the whole ceiling.
    """
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    return loop


def test_send_writes_a_marker_that_take_finds(tmp_path: Path) -> None:
    """A sent request leaves a marker on disk that take then removes."""
    request = SummonRequest(tmp_path)

    assert request.send() is True
    assert request.path.exists()
    assert request.take() is True
    assert not request.path.exists()


def test_take_reports_nothing_when_no_request_is_pending(tmp_path: Path) -> None:
    """Taking with no marker present reports False and does not raise."""
    assert SummonRequest(tmp_path).take() is False


def test_take_is_one_shot(tmp_path: Path) -> None:
    """A single send is consumed once, however many times take is called."""
    request = SummonRequest(tmp_path)
    request.send()

    assert request.take() is True
    assert request.take() is False


def test_two_sends_before_a_take_summon_the_window_once(tmp_path: Path) -> None:
    """Two launches in quick succession leave one request, not two.

    The marker's presence is the message, so a second launch arriving before the
    running instance polls does not queue a second window.
    """
    request = SummonRequest(tmp_path)
    request.send()
    request.send()

    assert request.take() is True
    assert request.take() is False


def test_a_separate_request_object_sees_the_same_marker(tmp_path: Path) -> None:
    """The marker is the shared state, not the object; that is what makes it work.

    In the real app the sender and the receiver are different processes, so the
    receiving object never sees the sending one.
    """
    SummonRequest(tmp_path).send()

    assert SummonRequest(tmp_path).take() is True


def test_send_reports_failure_rather_than_raising(tmp_path: Path) -> None:
    """A marker that cannot be written reports False and lets the caller exit.

    A file standing where the directory should be makes the write impossible,
    which stands in for any unwritable location. The second process is exiting
    either way, so this can never be fatal.
    """
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")

    assert SummonRequest(blocked).send() is False


def test_the_default_directory_is_the_per_user_lock_directory(tmp_path: Path) -> None:
    """With no directory given, the marker sits beside the lock file."""
    assert SummonRequest().path.parent == tmp_path / "o7Debrief"


def test_the_watcher_runs_the_handler_when_a_request_arrives(tmp_path: Path) -> None:
    """A request sent while the watcher runs opens the window exactly once."""
    request = SummonRequest(tmp_path)
    summoned: list[int] = []
    loop = _run_for(_SUMMON_CEILING_MS)

    def on_summon() -> None:
        summoned.append(1)
        loop.quit()

    watcher = SummonWatcher(request, on_summon, interval_ms=_TEST_INTERVAL_MS)
    watcher.start()
    try:
        request.send()
        loop.exec()
    finally:
        watcher.stop()

    assert summoned == [1]


def test_the_watcher_stays_quiet_when_nothing_is_sent(tmp_path: Path) -> None:
    """No request means no window; the poll costs a stat and nothing more."""
    summoned: list[int] = []
    watcher = SummonWatcher(
        SummonRequest(tmp_path),
        lambda: summoned.append(1),
        interval_ms=_TEST_INTERVAL_MS,
    )
    watcher.start()
    try:
        _run_for(_QUIET_WAIT_MS).exec()
    finally:
        watcher.stop()

    assert summoned == []


def test_starting_discards_a_marker_left_by_a_crashed_instance(tmp_path: Path) -> None:
    """A stale marker never opens a window nobody asked for."""
    request = SummonRequest(tmp_path)
    request.send()

    summoned: list[int] = []
    watcher = SummonWatcher(
        request, lambda: summoned.append(1), interval_ms=_TEST_INTERVAL_MS
    )
    watcher.start()
    try:
        _run_for(_QUIET_WAIT_MS).exec()
    finally:
        watcher.stop()

    assert summoned == []
    assert not request.path.exists()


def test_a_stopped_watcher_ignores_a_request(tmp_path: Path) -> None:
    """Once stopped the watcher polls no further, so a late marker is left alone."""
    request = SummonRequest(tmp_path)
    summoned: list[int] = []
    watcher = SummonWatcher(
        request, lambda: summoned.append(1), interval_ms=_TEST_INTERVAL_MS
    )
    watcher.start()
    watcher.stop()

    request.send()
    _run_for(_QUIET_WAIT_MS).exec()

    assert summoned == []
    assert request.path.exists()


def test_stopping_without_starting_is_safe(tmp_path: Path) -> None:
    """Stopping a watcher that never started does nothing and does not raise."""
    SummonWatcher(SummonRequest(tmp_path), lambda: None).stop()
