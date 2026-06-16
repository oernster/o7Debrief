"""SessionViewModel: a thin tray-facing adapter over the SessionRecorder.

The tray needs a single live status string and a way to be told when that
string changes. This view model owns neither timing nor presentation policy:
it simply polls the injected recorder on demand and re-publishes the
recorder's own headline, emitting a Qt signal so the tray can refresh its
status line. Timing (how often to poll) lives in the tray's QTimer, not here.

The recorder is injected and used purely by shape (``poll`` and ``status``),
so a fake recorder drives this model in tests without any real journal or
infrastructure. The concrete ``SessionRecorder`` type is referenced only
under ``TYPE_CHECKING`` to keep this module a strict client of the
application layer with no runtime cross-layer import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:  # pragma: no cover - type-only import, no runtime dependency
    from o7debrief.application.services.session_recorder import (
        SessionRecorder,
        SessionStatus,
    )

__all__ = ["SessionViewModel"]


class SessionViewModel(QObject):
    """Adapts a SessionRecorder into a status string and a change signal."""

    # Emitted with the latest status headline whenever the model refreshes.
    status_changed = Signal(str)

    def __init__(self, recorder: SessionRecorder) -> None:
        super().__init__()
        self._recorder = recorder
        self._status: SessionStatus = recorder.status()

    @property
    def status_text(self) -> str:
        """Return the recorder's current headline as last observed."""
        return self._status.headline

    @property
    def is_recording(self) -> bool:
        """Return whether the recorder currently holds any session events."""
        return self._status.is_recording

    @property
    def event_count(self) -> int:
        """Return how many events the recorder has accumulated so far."""
        return self._status.event_count

    def refresh(self) -> str:
        """Poll the recorder, cache its status and emit the new headline.

        Returns the fresh headline so a caller can use it directly without
        waiting on the signal. Polling appends only newly written events, so
        repeated refreshes accumulate the session cheaply.
        """
        self._recorder.poll()
        self._status = self._recorder.status()
        headline = self._status.headline
        self.status_changed.emit(headline)
        return headline
