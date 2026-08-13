"""TrayAvailabilityWatcher: settling whether this desktop draws a system tray.

o7 Debrief lives in the tray and a tray is not something a Linux desktop owes
anyone. Assume nothing: GNOME draws none without an extension, Ubuntu ships
that extension enabled, KDE, XFCE, MATE, Cinnamon and LXQt each provide one by
their own route and any of them can have it turned off. The app therefore asks
the running desktop rather than the platform name and it asks more than once.

Asking once is the trap this module exists to avoid. ``isSystemTrayAvailable``
answers for the desktop as it stands at that instant and the instant the app
cares about is the worst one to ask in: started from the autostart entry, o7
Debrief launches while the session is still assembling, before the panel or the
shell extension that hosts tray icons has registered itself. A single check
there reports no tray on a machine that is about to have one and the app would
draw its fallback window over a session that never needed it.

So the question is asked repeatedly over a short grace period and settles once:
available as soon as a tray appears, unavailable only when the grace period ends
with none. Settling unavailable is what lets the composition root put the home
window on screen, so the app is never left running with nothing on screen to
click. That is the safe direction: a redundant window costs a Commander one
click, while an unreachable background process costs them the app.

The watcher stops at the first answer rather than tracking the tray for the
process's life. A tray that disappears later leaves the app reachable anyway,
because launching it again summons the home window (see ``summon``), so nothing
here needs to keep watching to preserve that guarantee.

This module belongs to the ui layer and imports Qt only. The availability probe
is injected, so the tests state the desktop's answer instead of needing a real
tray to be present or absent on the machine running them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QSystemTrayIcon

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from collections.abc import Callable

__all__ = ["TrayAvailabilityWatcher"]

# How often the desktop is asked. Short enough that a tray appearing during
# login is picked up while the splash is still on screen and cheap enough to
# repeat: the probe is a single query of the platform integration.
_POLL_INTERVAL_MS = 500

# How long to keep asking before concluding this desktop draws no tray. Sized
# for the slow case rather than the fast one: a cold login on a loaded machine
# can bring the panel or the shell extension up seconds after the autostart
# entry has already launched the app. Concluding early is the costly mistake,
# because it puts a window on screen that the session did not need.
_GRACE_PERIOD_MS = 15000


def _qt_tray_available() -> bool:
    """Return whether Qt can see a system tray on the running desktop."""
    return QSystemTrayIcon.isSystemTrayAvailable()


class TrayAvailabilityWatcher(QObject):
    """Reports once whether this desktop draws a system tray."""

    def __init__(
        self,
        on_settled: Callable[[bool], None],
        is_available: Callable[[], bool] = _qt_tray_available,
        interval_ms: int = _POLL_INTERVAL_MS,
        grace_period_ms: int = _GRACE_PERIOD_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_settled = on_settled
        self._is_available = is_available
        self._grace_period_ms = grace_period_ms
        self._waited_ms = 0
        self._settled = False
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll)

    @property
    def settled(self) -> bool:
        """Return whether an answer has been reported."""
        return self._settled

    def start(self) -> None:
        """Ask the desktop now and keep asking until an answer settles.

        A desktop that already draws a tray answers immediately and no timer
        ever runs, so the common case costs one query and nothing else.
        """
        if self._is_available():
            self._settle(True)
            return
        self._timer.start()

    def stop(self) -> None:
        """Stop asking. Safe to call whether or not the watcher started."""
        self._timer.stop()

    def _poll(self) -> None:
        """Ask again, settling on a tray appearing or on the grace period."""
        if self._is_available():
            self._settle(True)
            return
        self._waited_ms += self._timer.interval()
        if self._waited_ms >= self._grace_period_ms:
            self._settle(False)

    def _settle(self, available: bool) -> None:
        """Report the answer once and stop asking."""
        if self._settled:
            return
        self._settled = True
        self._timer.stop()
        self._on_settled(available)
