"""Run the update check from the tray: triggers, worker and the prompt.

The controller runs the check on a worker thread (a menu click or a timer
must never block the ui for a network timeout) and the result crosses back
through a Signal connected to a bound method of this ui-thread QObject, so
delivery is a queued connection. An automatic check runs shortly after
launch and once a day; both honour the skipped version and stay silent on
every outcome except an available update. The manual tray action ignores
the skip and reports every outcome through tray notifications.

An available update raises the Download / Skip this version / Later prompt.
o7Debrief has no main window, so the prompt parents to nothing and simply
appears; the prompt itself is injected so tests can script an answer
without a dialog. Download opens the platform's installer asset, falling
back to the releases page; Skip persists the offered version through the
injected saver so it never prompts again.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from o7debrief.application.dto.update_status import UpdateStatus
    from o7debrief.application.services.update_service import UpdateService

__all__ = ["UpdateCheckController", "prompt_with_dialog"]

# The launch check waits out startup; the re-check runs daily.
LAUNCH_CHECK_DELAY_MS = 3000
_HOURS_PER_DAY = 24
_MINUTES_PER_HOUR = 60
_SECONDS_PER_MINUTE = 60
_MS_PER_SECOND = 1000
RECHECK_INTERVAL_MS = (
    _HOURS_PER_DAY * _MINUTES_PER_HOUR * _SECONDS_PER_MINUTE * _MS_PER_SECOND
)

# Prompt answers the injected prompt callable returns.
ANSWER_DOWNLOAD = "download"
ANSWER_SKIP = "skip"
ANSWER_LATER = "later"

# Dialog and notification texts.
_PROMPT_TITLE = "Update available"
_PROMPT_BODY = "o7 Debrief {latest} is available. You are running {current}."
_DOWNLOAD_TEXT = "Download"
_SKIP_TEXT = "Skip this version"
_LATER_TEXT = "Later"
_UP_TO_DATE_TITLE = "Up to date"
_UP_TO_DATE_BODY = "You are running the latest version."
_CHECK_FAILED_TITLE = "Update check failed"
_CHECK_FAILED_BODY = "The update check could not reach GitHub. Please try again later."


def prompt_with_dialog(status: UpdateStatus) -> str:
    """Show the update prompt as a dialog and return the chosen answer."""
    box = QMessageBox()
    box.setWindowTitle(_PROMPT_TITLE)
    box.setText(_PROMPT_BODY.format(latest=status.latest, current=status.current))
    download = box.addButton(_DOWNLOAD_TEXT, QMessageBox.AcceptRole)
    skip = box.addButton(_SKIP_TEXT, QMessageBox.DestructiveRole)
    box.addButton(_LATER_TEXT, QMessageBox.RejectRole)
    box.setDefaultButton(download)
    box.exec()
    clicked = box.clickedButton()
    if clicked is download:
        return ANSWER_DOWNLOAD
    if clicked is skip:
        return ANSWER_SKIP
    return ANSWER_LATER


class UpdateCheckController(QObject):
    """Runs the update check off the ui thread and presents the outcome."""

    _result_ready = Signal(object, bool)

    def __init__(
        self,
        service: UpdateService,
        notify: Callable[[str, str], None],
        web_opener: Callable[[str], bool],
        load_skipped: Callable[[], str | None],
        save_skipped: Callable[[str], None],
        prompt: Callable[[UpdateStatus], str] = prompt_with_dialog,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._notify = notify
        self._web_opener = web_opener
        self._load_skipped = load_skipped
        self._save_skipped = save_skipped
        self._prompt = prompt
        self._result_ready.connect(self._present_result)
        self._recheck_timer = QTimer(self)
        self._recheck_timer.setInterval(RECHECK_INTERVAL_MS)
        self._recheck_timer.timeout.connect(self.check_automatically)

    def start(self) -> None:
        """Schedule the launch check and start the daily re-check."""
        QTimer.singleShot(LAUNCH_CHECK_DELAY_MS, self.check_automatically)
        self._recheck_timer.start()

    def stop(self) -> None:
        """Stop the daily re-check."""
        self._recheck_timer.stop()

    def check_automatically(self) -> None:
        """Run a check that honours the skip and stays silent on failure."""
        self._start_worker(manual=False)

    def check_manually(self) -> None:
        """Run a check that ignores the skip and reports every outcome."""
        self._start_worker(manual=True)

    def _start_worker(self, manual: bool) -> None:
        skipped = None if manual else self._load_skipped()

        def run() -> None:
            try:
                status = self._service.check(skipped)
            except Exception:  # noqa: BLE001 (any error reads as unreachable)
                status = None
            self._result_ready.emit(status, manual)

        threading.Thread(target=run, daemon=True).start()

    def _present_result(self, status: UpdateStatus | None, manual: bool) -> None:
        unreachable = status is None or status.latest is None
        if unreachable:
            if manual:
                self._notify(_CHECK_FAILED_TITLE, _CHECK_FAILED_BODY)
            return
        if status.update_available:
            self._handle_answer(self._prompt(status), status)
            return
        if manual:
            self._notify(_UP_TO_DATE_TITLE, _UP_TO_DATE_BODY)

    def _handle_answer(self, answer: str, status: UpdateStatus) -> None:
        if answer == ANSWER_DOWNLOAD:
            url = status.download_url or status.page_url
            if url:
                self._web_opener(url)
        elif answer == ANSWER_SKIP and status.latest:
            self._save_skipped(status.latest)
