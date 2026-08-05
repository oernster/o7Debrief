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
# needs afterwards (the installed executable path, or None).
Operation = Callable[[ProgressCallback], object]

NO_ERROR = ""
UNEXPECTED_ERROR = "The operation failed: {detail}"


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
    """Owns the worker thread for one operation and cleans it up afterwards."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: OperationWorker | None = None

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

        thread.started.connect(worker.run)
        worker.progressed.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.finished.connect(lambda *_: self._stop())

        self._thread = thread
        self._worker = worker
        thread.start()

    def _stop(self) -> None:
        """Quit and wait for the worker thread, then release both objects."""
        thread = self._thread
        if thread is not None:
            thread.quit()
            thread.wait()
        self._thread = None
        self._worker = None
