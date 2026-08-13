"""SummonRequest and SummonWatcher: reaching a running instance that has no window.

o7 Debrief has no window of its own; it lives in the tray. On Windows that is
always reachable; a Linux desktop need not draw a tray at all. On one that does
not, the running app becomes unreachable: it is watching the journal and
generating debriefs with nothing on screen to click. Launching the app again is
the natural thing to try; until now it did nothing visible at all. The second
process found the single-instance lock held and exited in silence.

So launching again is the summon route. The second process leaves a marker file
in the per-user lock directory and exits; the running instance polls for that
marker, removes it and opens its home window, which already carries every
operation the app has (live status, both debrief actions, recent reports,
Settings, About and Close). The installed desktop entry therefore summons the
window: no tray is needed to reach the app.

A file was chosen over a socket deliberately. A socket would mean the app
listens for something; o7 Debrief accepts no inbound connection of any kind. It
makes exactly one outbound call (the update check) and nothing reaches in. That
is a stated property of the product rather than an implementation detail, so the
signalling stays on the filesystem where it cannot become a network surface. The
marker carries no instruction either; its presence is the whole message, so
nothing a second process writes can steer the running one.

This module belongs to the ui layer and imports the application layer not at
all: it needs the standard library plus Qt's timer for the watcher.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer

from o7debrief.ui.tray.single_instance import user_lock_dir

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from collections.abc import Callable

__all__ = ["SummonRequest", "SummonWatcher"]

# Marker file left by a second launch, beside the lock file it failed to take.
_SUMMON_FILE_NAME = "o7debrief.summon"

# How often, in milliseconds, the running instance looks for a marker. This is
# the delay a Commander sees between launching again and the window appearing,
# so it is short; the check is a single stat of one file, so it stays cheap.
_POLL_INTERVAL_MS = 250


class SummonRequest:
    """A one-shot cross-process request to show the running instance's window."""

    def __init__(self, directory: Path | None = None) -> None:
        self._path = (directory or user_lock_dir()) / _SUMMON_FILE_NAME

    @property
    def path(self) -> Path:
        """Return the marker file path this request reads and writes."""
        return self._path

    def send(self) -> bool:
        """Leave a marker asking the running instance to show its window.

        Reports whether the marker was written. A failure is not fatal and is
        never raised: the second process is exiting either way; all that is lost
        is the window appearing. The caller uses the answer to say which of
        those happened rather than to decide what to do next.

        The pid goes in the file for the same reason the lock file carries one:
        it makes a stray marker traceable to the launch that left it. Nothing
        reads the contents back.
        """
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            return False
        return True

    def take(self) -> bool:
        """Remove any pending marker; report whether one was there.

        Removal and detection are one act deliberately. Checking first and
        deleting after would leave a window in which a marker arriving between
        the two is consumed without ever being seen; the Commander's launch
        would be swallowed.
        """
        try:
            self._path.unlink()
        except OSError:
            return False
        return True


class SummonWatcher(QObject):
    """Polls a summon request and runs a handler when one arrives."""

    def __init__(
        self,
        request: SummonRequest,
        on_summon: Callable[[], None],
        interval_ms: int = _POLL_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._on_summon = on_summon
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        """Discard any stale marker, then begin watching for a new one.

        A marker outlives the process that wrote it if the running instance dies
        between the write and the next poll. Clearing it here means a crash
        cannot make the next launch open a window nobody asked for.
        """
        self._request.take()
        self._timer.start()

    def stop(self) -> None:
        """Stop watching. Safe to call whether or not the watcher started."""
        self._timer.stop()

    def _poll(self) -> None:
        """Run the handler if a summon is pending."""
        if self._request.take():
            self._on_summon()
