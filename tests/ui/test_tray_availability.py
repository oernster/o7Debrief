"""Tests for TrayAvailabilityWatcher: settling whether the desktop draws a tray.

The probe is injected throughout, so no test needs a real system tray to be
present or absent on the machine running it. That is the point of the seam: the
suite runs on an offscreen platform that reports no tray, on a developer's
Ubuntu session that reports one, and in CI, and every one of these cases has to
be exercised regardless of which of those it is running on.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from o7debrief.ui.tray.tray_availability import TrayAvailabilityWatcher

# A poll interval and grace period for the tests. The grace is a small multiple
# of the interval so the expiry arrives after a known number of polls, and both
# are derived from that one relationship rather than stated twice.
_INTERVAL_MS = 10
_POLLS_BEFORE_EXPIRY = 3
_GRACE_MS = _INTERVAL_MS * _POLLS_BEFORE_EXPIRY


def _make(
    answers: list[bool], settled: list[bool]
) -> tuple[TrayAvailabilityWatcher, list[bool]]:
    """Build a watcher whose probe returns each answer in turn.

    The final answer repeats once the list runs out, so a test states only the
    answers that change rather than padding the list to the poll count.
    """

    def probe() -> bool:
        return answers.pop(0) if len(answers) > 1 else answers[0]

    watcher = TrayAvailabilityWatcher(
        settled.append,
        is_available=probe,
        interval_ms=_INTERVAL_MS,
        grace_period_ms=_GRACE_MS,
    )
    return watcher, settled


def _pump(qapp: QApplication, times: int) -> None:
    """Drive the event loop long enough for a number of polls to fire."""
    for _ in range(times):
        qapp.processEvents()
        QApplication.instance().thread().msleep(_INTERVAL_MS)
        qapp.processEvents()


def test_a_desktop_with_a_tray_settles_at_once(qapp: QApplication) -> None:
    """The common case costs one query and starts no timer."""
    settled: list[bool] = []
    watcher, _ = _make([True], settled)

    watcher.start()

    assert settled == [True]
    assert watcher.settled is True


def test_a_tray_appearing_late_still_settles_available(qapp: QApplication) -> None:
    """A panel that registers after the app started is what this exists for."""
    settled: list[bool] = []
    watcher, _ = _make([False, False, True], settled)

    watcher.start()
    assert settled == []

    _pump(qapp, _POLLS_BEFORE_EXPIRY)

    assert settled == [True]


def test_no_tray_within_the_grace_period_settles_unavailable(
    qapp: QApplication,
) -> None:
    """Only the grace period expiring concludes that there is no tray."""
    settled: list[bool] = []
    watcher, _ = _make([False], settled)

    watcher.start()
    _pump(qapp, _POLLS_BEFORE_EXPIRY + 1)

    assert settled == [False]


def test_the_answer_is_reported_once_only(qapp: QApplication) -> None:
    """A settled watcher stays settled however long the loop keeps running."""
    settled: list[bool] = []
    watcher, _ = _make([False], settled)

    watcher.start()
    _pump(qapp, _POLLS_BEFORE_EXPIRY * 3)

    assert settled == [False]


def test_stopping_before_the_grace_period_reports_nothing(
    qapp: QApplication,
) -> None:
    """Shutting down mid-wait must not fire the fallback on the way out."""
    settled: list[bool] = []
    watcher, _ = _make([False], settled)

    watcher.start()
    watcher.stop()
    _pump(qapp, _POLLS_BEFORE_EXPIRY + 1)

    assert settled == []
    assert watcher.settled is False


def test_stop_is_safe_before_start(qapp: QApplication) -> None:
    settled: list[bool] = []
    watcher, _ = _make([False], settled)

    watcher.stop()

    assert settled == []
