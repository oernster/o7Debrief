"""Tests for the tray's update check: prompt answers, skip and triggers.

Qt is real (offscreen); the update service and the prompt are faked. The
check runs on a worker thread and reports back through a queued signal, so
each test turns the event loop until the observable outcome lands.
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication, QMenu

from o7debrief.application.dto.update_status import UpdateStatus
from o7debrief.ui.tray.tray_controller import TrayController
from tests.ui.fakes import (
    FakeOneShot,
    FakeRecorder,
    FakeUpdateService,
    RecordingOpener,
)

# Releases page carried by the status and opened as the download fallback.
_RELEASES_URL = "https://example.test/o7Debrief/releases/latest"

# How long each event-loop turn sleeps while waiting for the worker result.
_SPIN_SLEEP_S = 0.01

# The caption of the tray menu's manual update action.
_CHECK_UPDATES_TEXT = "Check for updates"


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


class _RecordingPrompt:
    """A prompt fake returning a preset answer and recording each status."""

    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.statuses: list[UpdateStatus] = []

    def __call__(self, status: UpdateStatus) -> str:
        self.statuses.append(status)
        return self._answer


def _spin_until(qapp: QApplication, predicate, timeout_s: float = 2.0) -> bool:
    """Process events until the predicate holds or the deadline passes."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(_SPIN_SLEEP_S)
    return False


def _update_controller(
    view_model,
    status: UpdateStatus,
    web_opener: RecordingOpener,
    prompt: _RecordingPrompt,
    save_skipped,
) -> TrayController:
    """Build a TrayController wired for one update-check scenario."""
    return TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        update_service=FakeUpdateService(status),
        web_opener=web_opener,
        save_skipped_version=save_skipped,
        update_prompt=prompt,
    )


def test_check_updates_download_opens_the_platform_asset(
    qapp: QApplication, view_model
) -> None:
    """Answering Download opens the asset URL carried by the status."""
    web_opener = RecordingOpener()
    prompt = _RecordingPrompt("download")
    controller = _update_controller(
        view_model,
        UpdateStatus(
            current="1.1.0",
            latest="9.9.9",
            update_available=True,
            download_url="https://example.test/win.exe",
            page_url=_RELEASES_URL,
        ),
        web_opener,
        prompt,
        save_skipped=lambda _version: None,
    )

    _action_named(_menu_of(controller), _CHECK_UPDATES_TEXT).trigger()

    assert _spin_until(qapp, lambda: web_opener.opened)
    assert web_opener.opened == ["https://example.test/win.exe"]
    assert len(prompt.statuses) == 1


def test_check_updates_download_falls_back_to_the_releases_page(
    qapp: QApplication, view_model
) -> None:
    """With no matching asset, Download opens the releases page instead."""
    web_opener = RecordingOpener()
    prompt = _RecordingPrompt("download")
    controller = _update_controller(
        view_model,
        UpdateStatus(
            current="1.1.0",
            latest="9.9.9",
            update_available=True,
            download_url=None,
            page_url=_RELEASES_URL,
        ),
        web_opener,
        prompt,
        save_skipped=lambda _version: None,
    )

    _action_named(_menu_of(controller), _CHECK_UPDATES_TEXT).trigger()

    assert _spin_until(qapp, lambda: web_opener.opened)
    assert web_opener.opened == [_RELEASES_URL]


def test_check_updates_skip_persists_the_offered_version(
    qapp: QApplication, view_model
) -> None:
    """Answering Skip saves the offered version and opens nothing."""
    web_opener = RecordingOpener()
    prompt = _RecordingPrompt("skip")
    saved: list[str] = []
    controller = _update_controller(
        view_model,
        UpdateStatus(
            current="1.1.0",
            latest="9.9.9",
            update_available=True,
            download_url="https://example.test/win.exe",
            page_url=_RELEASES_URL,
        ),
        web_opener,
        prompt,
        save_skipped=saved.append,
    )

    _action_named(_menu_of(controller), _CHECK_UPDATES_TEXT).trigger()

    assert _spin_until(qapp, lambda: saved)
    assert saved == ["9.9.9"]
    assert web_opener.opened == []


def test_check_updates_prompts_nothing_when_up_to_date(
    qapp: QApplication, view_model
) -> None:
    """An up-to-date manual check raises no prompt and opens no page."""
    web_opener = RecordingOpener()
    prompt = _RecordingPrompt("download")
    service = FakeUpdateService(
        UpdateStatus(current="1.1.0", latest="1.1.0", update_available=False)
    )
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        update_service=service,
        web_opener=web_opener,
        update_prompt=prompt,
    )

    _action_named(_menu_of(controller), _CHECK_UPDATES_TEXT).trigger()

    assert _spin_until(qapp, lambda: service.calls)
    qapp.processEvents()
    assert prompt.statuses == []
    assert web_opener.opened == []


def test_automatic_check_passes_the_skipped_version_in(
    qapp: QApplication, view_model
) -> None:
    """The automatic path loads and passes the persisted skipped version."""
    service = FakeUpdateService(
        UpdateStatus(current="1.1.0", latest="1.1.0", update_available=False)
    )
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=view_model,
        opener=RecordingOpener(),
        update_service=service,
        load_skipped_version=lambda: "9.9.9",
        update_prompt=_RecordingPrompt("later"),
    )

    controller._update_controller.check_automatically()

    assert _spin_until(qapp, lambda: service.calls)
    assert service.skipped_versions == ["9.9.9"]
