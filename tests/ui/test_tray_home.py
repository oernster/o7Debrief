"""Tray-driven home dialog tests: opening, reuse, close and live refresh.

Qt is real (offscreen); only the application services and the dialog itself are
faked. A left-click opens the modeless home dialog, a second left-click reuses
it, closing it drops the reference and a debrief generated while it is open
refreshes its recent list in place. The fake dialog stands in for HomeDialog so
these run without a real window.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from o7debrief.application.dto.export_result import ExportResult
from o7debrief.ui.tray.tray_controller import TrayController

from tests.ui.fakes import FakeOneShot, FakeRecorder, RecordingOpener

# Captions and sample report paths shared by the tray-home tests.
_LAST_SESSION_TEXT = "Debrief my last session"
_HTML_PATH = "C:/out/debrief_2026.html"
_MD_PATH = "C:/out/debrief_2026.md"


@pytest.fixture
def view_model():  # type: ignore[no-untyped-def]
    """Return a real SessionViewModel wrapping a fake recorder."""
    from o7debrief.ui.view_models.session_view_model import SessionViewModel

    return SessionViewModel(FakeRecorder())


def _menu_of(controller: TrayController) -> QMenu:
    """Return the controller's context menu via the public tray surface."""
    return controller._tray.contextMenu()


def _action_named(menu: QMenu, text: str):  # type: ignore[no-untyped-def]
    """Return the first top-level action with a given caption."""
    for action in menu.actions():
        if action.text() == text:
            return action
    raise AssertionError(f"menu action not found: {text}")


class _FakeSignal:
    """A minimal stand-in for a Qt signal exposing connect and emit."""

    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, slot) -> None:  # type: ignore[no-untyped-def]
        """Register a slot to receive emissions."""
        self._slots.append(slot)

    def emit(self, value: int = 0) -> None:
        """Invoke every connected slot with the given value."""
        for slot in self._slots:
            slot(value)


class _FakeHome:
    """A fake home dialog that records its modeless lifecycle without a window.

    Standing in for HomeDialog lets the activation tests run without a real
    window. The latest instance is captured on the class so a test can inspect
    what the controller passed, drive the callbacks it wired, observe in-place
    refreshes and simulate a close through the ``finished`` signal.
    """

    last: _FakeHome | None = None

    def __init__(self, status_text: str, recent: object, **callbacks: object) -> None:
        self.status_text = status_text
        self.recent = recent
        self.callbacks = callbacks
        self.show_calls = 0
        self.bring_to_front_calls = 0
        self.refreshes: list[tuple[str, object]] = []
        self.finished = _FakeSignal()
        _FakeHome.last = self

    def show(self) -> None:
        """Record the modeless show."""
        self.show_calls += 1

    def bring_to_front(self) -> None:
        """Record a request to surface an already-open dialog."""
        self.bring_to_front_calls += 1

    def refresh(self, status_text: str, recent: object) -> None:
        """Record an in-place refresh of the status line and recent list."""
        self.status_text = status_text
        self.recent = recent
        self.refreshes.append((status_text, recent))

    def close(self) -> None:
        """Simulate the user closing the dialog by emitting finished."""
        self.finished.emit(0)


def test_left_click_opens_home_dialog(qapp: QApplication, view_model) -> None:
    """A left-click (Trigger) builds and shows the home dialog with status."""
    _FakeHome.last = None
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)

    assert _FakeHome.last is not None
    assert _FakeHome.last.show_calls == 1
    assert _FakeHome.last.status_text == view_model.status_text


def test_right_click_does_not_open_home_dialog(qapp: QApplication, view_model) -> None:
    """A context (right-click) activation must not open the home dialog."""
    _FakeHome.last = None
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)

    assert _FakeHome.last is None


def test_home_dialog_actions_drive_the_same_use_cases(
    qapp: QApplication, view_model
) -> None:
    """The callbacks handed to the home dialog run the tray's own use cases."""
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH,)))
    opener = RecordingOpener()
    controller = TrayController(
        one_shot=one_shot,
        session=view_model,
        opener=opener,
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert _FakeHome.last is not None
    callbacks = _FakeHome.last.callbacks
    callbacks["on_debrief_history"]()
    callbacks["on_debrief_last"]()

    assert one_shot.history_calls == 1
    assert one_shot.calls == 1
    assert opener.opened == [_HTML_PATH, _HTML_PATH]


def test_second_left_click_brings_open_home_to_front(
    qapp: QApplication, view_model
) -> None:
    """A second left-click surfaces the open dialog rather than opening another."""
    _FakeHome.last = None
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    first = _FakeHome.last
    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)

    assert _FakeHome.last is first
    assert first.show_calls == 1
    assert first.bring_to_front_calls == 1


def test_home_reopens_after_being_closed(qapp: QApplication, view_model) -> None:
    """Once closed, the next left-click builds a fresh dialog rather than none."""
    _FakeHome.last = None
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    first = _FakeHome.last
    first.close()
    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)

    assert _FakeHome.last is not first
    assert _FakeHome.last.show_calls == 1


def test_debrief_refreshes_open_home(qapp: QApplication, view_model) -> None:
    """A debrief generated while home is open refreshes its recent list in place."""
    _FakeHome.last = None
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH, _MD_PATH)))
    controller = TrayController(
        one_shot=one_shot,
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    controller._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()

    assert _FakeHome.last is not None
    assert _FakeHome.last.refreshes  # the open dialog was refreshed
    status, recent = _FakeHome.last.refreshes[-1]
    assert status == view_model.status_text
    assert recent == (_HTML_PATH, _MD_PATH)


def test_debrief_with_home_closed_refreshes_nothing(
    qapp: QApplication, view_model
) -> None:
    """With no home open, generating a debrief refreshes nothing and is safe."""
    _FakeHome.last = None
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH,)))
    controller = TrayController(
        one_shot=one_shot,
        session=view_model,
        opener=RecordingOpener(),
        home_factory=_FakeHome,
    )

    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()

    assert _FakeHome.last is None
