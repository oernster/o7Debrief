"""Running an installer operation off the UI thread.

Install, repair and uninstall all move hundreds of megabytes, so running them on
the UI thread froze the window for the whole operation and left the progress bar
unable to paint. Each runs on a worker thread instead and reports back through
signals. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from installer.ops.errors import InstallerError
from installer.ops.progress import ProgressCallback

# An operation receives a progress reporter and returns whatever the caller
# needs afterwards (the installed executable path, else None).
Operation = Callable[[ProgressCallback], object]

NO_ERROR = ""
UNEXPECTED_ERROR = "The operation failed: {detail}"

# The longest the interface thread will wait for a worker thread to stop.
# The wait must be bounded. It runs on the interface thread, so a thread that
# never stops would freeze the whole setup program with no window left to
# report it, which is exactly how launching the app on finish hung the
# installer: the window closed, shutdown began and an unbounded wait never
# returned. A worker that has already reported finished is done, so this
# bound is reached only by a wedged thread.
THREAD_STOP_TIMEOUT_MS = 5000


class OperationWorker(QObject):
    """Runs one operation and reports its progress, then its outcome."""

    progressed = Signal(int, str)
    finished = Signal(str, object)

    def __init__(self, operation: Operation) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        """Run the operation, reporting failure as a message rather than raising.

        A worker thread that raises would tear down the thread with nothing
        shown, so every failure is turned into the message the window displays.
        """
        try:
            result = self._operation(self._report)
        except InstallerError as error:
            self.finished.emit(str(error), None)
            return
        except Exception as error:  # noqa: BLE001
            # Last resort: an unexpected failure must still reach the user
            # rather than disappearing with the thread.
            self.finished.emit(UNEXPECTED_ERROR.format(detail=error), None)
            return
        self.finished.emit(NO_ERROR, result)

    def _report(self, pct: int, message: str) -> None:
        """Forward one progress update to the UI thread."""
        self.progressed.emit(pct, message)


class OperationRunner(QObject):
    """Owns the worker thread for one operation and cleans it up afterwards.

    The worker's signals are connected to bound methods of this object, never
    to bare callables. A signal connected to a plain function with no receiver
    runs in the SENDER's thread. The sender here lives on the worker
    thread. That is not a detail: it put the caller's callbacks on the worker
    thread, so the window was touched and closed from a thread that must never
    touch it. The teardown below then called ``wait()`` on the very thread it
    was running in, which is a deadlock by definition. This object lives on the
    interface thread, so a bound method of it is delivered there instead.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: OperationWorker | None = None
        self._on_progress: Callable[[int, str], None] | None = None
        self._on_finished: Callable[[str, object], None] | None = None

    def is_idle(self) -> bool:
        """Return whether no worker thread is currently held."""
        return self._thread is None

    def start(
        self,
        operation: Operation,
        on_progress: Callable[[int, str], None],
        on_finished: Callable[[str, object], None],
    ) -> None:
        """Run ``operation`` on a worker thread and report back on the UI thread."""
        thread = QThread(self)
        worker = OperationWorker(operation)
        worker.moveToThread(thread)

        self._on_progress = on_progress
        self._on_finished = on_finished

        thread.started.connect(worker.run)
        worker.progressed.connect(self._forward_progress)
        worker.finished.connect(self._forward_finished)

        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(int, str)
    def _forward_progress(self, pct: int, message: str) -> None:
        """Hand one progress update to the caller, on the interface thread."""
        if self._on_progress is not None:
            self._on_progress(pct, message)

    @Slot(str, object)
    def _forward_finished(self, error: str, result: object) -> None:
        """Release the thread, then hand the outcome to the caller.

        The thread is released first, so by the time the caller runs there is
        nothing left to wait on. The caller may close the window and end the
        program; it must never do that with a teardown still pending.
        """
        self._stop()
        callback = self._on_finished
        self._on_progress = None
        self._on_finished = None
        if callback is not None:
            callback(error, result)

    def _stop(self) -> None:
        """Quit and wait for the worker thread, then release both objects.

        The references are dropped first, so a second call cannot wait on a
        thread already being torn down. The thread and worker are deleted
        through the event loop rather than by falling out of scope, then only
        once the thread has actually finished: deleting a running QThread
        aborts the process.
        """
        thread = self._thread
        worker = self._worker
        self._thread = None
        self._worker = None
        if thread is None:
            return
        thread.quit()
        thread.wait(THREAD_STOP_TIMEOUT_MS)
        if not thread.isFinished():
            return
        if worker is not None:
            worker.deleteLater()
        thread.deleteLater()
