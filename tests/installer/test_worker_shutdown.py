"""Tests for tearing down the installer's worker thread without hanging.

The setup program hung after launching the application on finish. The cause
was in this seam: the worker's finished signal drives two slots, the first of
which closed the window (starting application shutdown) while the second was
still to wait on the worker thread. That wait had no bound, so the process
never exited and the installer hung with its window already gone.

These cover the guarantees that make it impossible: the wait is bounded, the
thread is released whether the operation succeeds or fails, plus a second
teardown that is inert rather than waiting on a thread that has already gone.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QEventLoop, QThread  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from installer.ui.worker import (  # noqa: E402
    THREAD_STOP_TIMEOUT_MS,
    OperationRunner,
)

# How long a test will wait for a worker to run and report back, plus how
# long one turn of the event loop is given to deliver queued signals.
_SETTLE_LIMIT_S = 5.0
_TURN_MS = 20


@pytest.fixture(name="app", scope="session")
def _app():
    """Return the one shared Qt application, creating it if needed.

    A QApplication, not a bare QCoreApplication: Qt permits one application
    object per process and the ui tests need the widget-capable kind, so
    creating the smaller one here would make whichever suite ran second fail.
    The offscreen platform is set by the repository conftest.
    """
    return QApplication.instance() or QApplication([])


def _settle(predicate, limit_s: float = _SETTLE_LIMIT_S) -> bool:
    """Pump the event loop until ``predicate`` holds or the limit is reached."""
    deadline = time.monotonic() + limit_s
    while time.monotonic() < deadline:
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, _TURN_MS)
        if predicate():
            return True
    return False


def _run(runner: OperationRunner, operation) -> list[tuple[str, object]]:
    """Start an operation and pump until it has reported back."""
    outcomes: list[tuple[str, object]] = []
    runner.start(
        operation,
        lambda pct, message: None,
        lambda error, result: outcomes.append((error, result)),
    )
    _settle(lambda: bool(outcomes) and runner.is_idle())
    return outcomes


def test_the_wait_for_a_worker_thread_is_bounded(app) -> None:
    # An unbounded wait runs on the interface thread, so it can never be
    # recovered from: it freezes the program with no window left to report it.
    assert THREAD_STOP_TIMEOUT_MS > 0


def test_an_operation_reports_back_and_releases_its_thread(app) -> None:
    runner = OperationRunner()

    outcomes = _run(runner, lambda report: "done")

    assert outcomes == [("", "done")]
    assert runner.is_idle()


def test_a_failing_operation_still_releases_its_thread(app) -> None:
    def explode(_report: object) -> object:
        raise RuntimeError("boom")

    runner = OperationRunner()

    outcomes = _run(runner, explode)

    assert outcomes and "boom" in outcomes[0][0]
    assert runner.is_idle()


def test_a_second_teardown_is_inert(app) -> None:
    # This is the call that would have blocked: a wait on a thread already
    # released. It must return at once rather than hold the interface thread.
    runner = OperationRunner()
    _run(runner, lambda report: None)

    started = time.monotonic()
    runner._stop()
    elapsed_s = time.monotonic() - started

    assert runner.is_idle()
    assert elapsed_s < 1.0


def test_the_callbacks_run_on_the_interface_thread(app) -> None:
    """The whole defect in one assertion.

    A signal connected to a bare callable runs in the sender's thread, which
    is the worker thread. That put the window's own handlers there, so the
    installer closed its window off the interface thread and waited on the
    thread it was running in. Both callbacks must arrive here instead.
    """
    main_thread = QThread.currentThread()
    threads: dict[str, object] = {}
    runner = OperationRunner()

    def report_once(report) -> object:
        threads["worker"] = QThread.currentThread()
        report(50, "halfway")
        return "done"

    runner.start(
        report_once,
        lambda pct, message: threads.setdefault("progress", QThread.currentThread()),
        lambda error, result: threads.setdefault("finished", QThread.currentThread()),
    )
    _settle(lambda: "finished" in threads and runner.is_idle())

    # The operation genuinely ran off the interface thread.
    assert threads["worker"] is not main_thread
    # Both callbacks came back to it.
    assert threads["progress"] is main_thread
    assert threads["finished"] is main_thread


def test_the_thread_is_already_released_when_the_caller_runs(app) -> None:
    """The caller may close the window, so nothing may still be pending."""
    idle_when_called: list[bool] = []
    runner = OperationRunner()

    runner.start(
        lambda report: None,
        lambda pct, message: None,
        lambda error, result: idle_when_called.append(runner.is_idle()),
    )
    _settle(lambda: bool(idle_when_called))

    assert idle_when_called == [True]


def test_progress_reaches_the_caller_before_the_outcome(app) -> None:
    seen: list[tuple[int, str]] = []
    runner = OperationRunner()
    outcomes: list[tuple[str, object]] = []

    def report_twice(report) -> object:
        report(10, "extracting")
        report(90, "finishing")
        return "done"

    runner.start(
        report_twice,
        lambda pct, message: seen.append((pct, message)),
        lambda error, result: outcomes.append((error, result)),
    )
    _settle(lambda: bool(outcomes) and runner.is_idle())

    assert seen == [(10, "extracting"), (90, "finishing")]
    assert outcomes == [("", "done")]
