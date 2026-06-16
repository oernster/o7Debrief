"""Smoke tests for TrayController against a real QApplication and fakes.

Qt is real (offscreen); only the application services are faked. The tests
assert that the required menu entries exist and that triggering them drives the
injected services, opens the produced report and records lifecycle correctly.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from o7debrief.application.dto.export_result import ExportResult
from o7debrief.application.errors import ApplicationError
from o7debrief.ui.tray.tray_controller import TrayController

from tests.ui.fakes import FakeOneShot, FakeRecorder, RecordingOpener

# Captions the menu must expose, matching the controller's constants.
_LAST_SESSION_TEXT = "Debrief my last session"
_HISTORY_TEXT = "Debrief my history to date"
_RECENT_TEXT = "Recent debriefs"
_SETTINGS_TEXT = "Settings"
_QUIT_TEXT = "Quit"

# Sample produced report paths used by the success-path tests.
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


def _captions(menu: QMenu) -> list[str]:
    """Return the captions of a menu's top-level actions."""
    return [action.text() for action in menu.actions()]


def _action_named(menu: QMenu, text: str):  # type: ignore[no-untyped-def]
    """Return the first top-level action with a given caption."""
    for action in menu.actions():
        if action.text() == text:
            return action
    raise AssertionError(f"menu action not found: {text}")


def test_menu_has_all_required_entries(qapp: QApplication, view_model) -> None:
    """The menu exposes the status line, both actions, recent, settings, quit."""
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
    )
    captions = _captions(_menu_of(controller))

    for required in (
        _LAST_SESSION_TEXT,
        _HISTORY_TEXT,
        _RECENT_TEXT,
        _SETTINGS_TEXT,
        _QUIT_TEXT,
    ):
        assert required in captions


def test_status_line_is_first_and_disabled(qapp: QApplication, view_model) -> None:
    """The first menu action is the live status line and is disabled."""
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
    )
    first = _menu_of(controller).actions()[0]

    assert first.isEnabled() is False
    assert first.text() == view_model.status_text


def test_debrief_last_action_runs_service(qapp: QApplication, view_model) -> None:
    """Debrief-my-last-session drives the one-shot and opens the primary path."""
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH, _MD_PATH)))
    opener = RecordingOpener()
    controller = TrayController(one_shot=one_shot, session=view_model, opener=opener)

    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()

    assert one_shot.calls == 1
    assert opener.opened == [_HTML_PATH]


def test_generated_paths_populate_recent_submenu(
    qapp: QApplication, view_model
) -> None:
    """Produced paths become reopenable entries in the Recent submenu."""
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH, _MD_PATH)))
    opener = RecordingOpener()
    controller = TrayController(one_shot=one_shot, session=view_model, opener=opener)

    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()
    recent_action = _action_named(_menu_of(controller), _RECENT_TEXT)
    submenu = recent_action.menu()
    entries = [action.text() for action in submenu.actions()]

    assert entries == [_HTML_PATH, _MD_PATH]

    # Opening a recent entry re-invokes the opener with that path.
    submenu.actions()[1].trigger()
    assert opener.opened[-1] == _MD_PATH


def test_empty_result_opens_nothing(qapp: QApplication, view_model) -> None:
    """A run that produces no paths opens nothing and leaves recent empty."""
    one_shot = FakeOneShot(ExportResult(paths=()))
    opener = RecordingOpener()
    controller = TrayController(one_shot=one_shot, session=view_model, opener=opener)

    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()

    assert one_shot.calls == 1
    assert opener.opened == []


def test_application_error_is_handled(qapp: QApplication, view_model) -> None:
    """An ApplicationError from the service does not propagate or open a file."""
    one_shot = FakeOneShot(error=ApplicationError("no commander"))
    opener = RecordingOpener()
    controller = TrayController(one_shot=one_shot, session=view_model, opener=opener)

    _action_named(_menu_of(controller), _LAST_SESSION_TEXT).trigger()

    assert one_shot.calls == 1
    assert opener.opened == []


def test_settings_and_quit_invoke_injected_callables(
    qapp: QApplication, view_model
) -> None:
    """Settings and Quit call their injected handlers; Quit stops the timer."""
    settings_calls: list[int] = []
    quit_calls: list[int] = []
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        on_settings=lambda: settings_calls.append(1),
        on_quit=lambda: quit_calls.append(1),
    )
    controller.show()

    _action_named(_menu_of(controller), _SETTINGS_TEXT).trigger()
    _action_named(_menu_of(controller), _QUIT_TEXT).trigger()

    assert settings_calls == [1]
    assert quit_calls == [1]
    assert controller._timer.isActive() is False


def test_show_starts_timer_and_seeds_status(qapp: QApplication, view_model) -> None:
    """show() starts the refresh timer and seeds the status caption."""
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
    )
    controller.show()

    assert controller._timer.isActive() is True
    first = _menu_of(controller).actions()[0]
    assert first.text() == view_model.status_text
    controller.stop()
    assert controller._timer.isActive() is False


def test_help_menu_about_and_licence_invoke_handlers(
    qapp: QApplication, view_model
) -> None:
    """The Help submenu exposes About and Licence wired to injected handlers."""
    about_calls: list[int] = []
    licence_calls: list[int] = []
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        on_about=lambda: about_calls.append(1),
        on_licence=lambda: licence_calls.append(1),
    )

    help_action = _action_named(_menu_of(controller), "Help")
    entries = {action.text(): action for action in help_action.menu().actions()}

    assert "About o7 Debrief" in entries
    assert "Licence" in entries
    entries["About o7 Debrief"].trigger()
    entries["Licence"].trigger()
    assert about_calls == [1]
    assert licence_calls == [1]


def test_history_action_runs_all_history_use_case(
    qapp: QApplication, view_model
) -> None:
    """Triggering the history action drives the all-history use case only."""
    one_shot = FakeOneShot(ExportResult(paths=(_HTML_PATH,)))
    opener = RecordingOpener()
    controller = TrayController(one_shot=one_shot, session=view_model, opener=opener)

    _action_named(_menu_of(controller), _HISTORY_TEXT).trigger()

    assert one_shot.history_calls == 1
    assert one_shot.calls == 0
    assert opener.opened == [_HTML_PATH]


def test_notify_is_callable(qapp: QApplication, view_model) -> None:
    """_notify must exist and not raise.

    Every debrief outcome calls it; a missing method is otherwise hidden
    because Qt swallows exceptions raised inside a triggered slot.
    """
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
    )

    controller._notify("Title", "Body")


class _FakeHome:
    """A fake home dialog that records construction and exec without blocking.

    Standing in for HomeDialog lets the activation tests run without a real
    modal window. The latest instance is captured on the class so a test can
    inspect what the controller passed and invoke the callbacks it wired.
    """

    last: _FakeHome | None = None

    def __init__(self, status_text: str, recent: object, **callbacks: object) -> None:
        self.status_text = status_text
        self.recent = recent
        self.callbacks = callbacks
        self.exec_calls = 0
        _FakeHome.last = self

    def exec(self) -> int:
        """Record the modal show and return at once rather than blocking."""
        self.exec_calls += 1
        return 0


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
    assert _FakeHome.last.exec_calls == 1
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
