"""Tests for HomeDialog: the left-click front door is a pure view.

Qt is real (offscreen). The dialog must own no behaviour: every button reports
through the injected callable, mirroring the tray menu so both entry points
drive the same use cases. The full path is preserved on each recent entry even
though the button shows only the file name.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea

from o7debrief.ui.windows.home import HomeDialog

_STATUS = "Recording session: 4 events."
_HTML_PATH = "C:/out/debrief_2026.html"
_MD_PATH = "C:/out/debrief_2026.md"
_NO_RECENT = "No debriefs yet this run."


def _make(recent: tuple[str, ...] = ()):  # type: ignore[no-untyped-def]
    """Build a HomeDialog with recording callbacks; return it with the logs."""
    calls: list[str] = []
    opened: list[str] = []
    dialog = HomeDialog(
        _STATUS,
        recent,
        on_debrief_last=lambda: calls.append("last"),
        on_debrief_history=lambda: calls.append("history"),
        on_settings=lambda: calls.append("settings"),
        on_about=lambda: calls.append("about"),
        on_open_recent=opened.append,
    )
    return dialog, calls, opened


def _buttons(dialog: HomeDialog) -> dict[str, QPushButton]:
    """Map each button's caption to the button, for lookup by text."""
    return {b.text(): b for b in dialog.findChildren(QPushButton)}


def test_debrief_buttons_invoke_their_callbacks(qapp: QApplication) -> None:
    """The two debrief buttons each call their injected handler in order."""
    dialog, calls, _ = _make()
    buttons = _buttons(dialog)

    buttons["Debrief my last session"].click()
    buttons["Debrief my history to date"].click()

    assert calls == ["last", "history"]


def test_settings_and_about_buttons_invoke_callbacks(qapp: QApplication) -> None:
    """The footer Settings and About buttons report through their handlers."""
    dialog, calls, _ = _make()
    buttons = _buttons(dialog)

    buttons["Settings"].click()
    buttons["About"].click()

    assert calls == ["settings", "about"]


def test_recent_entries_reopen_by_full_path(qapp: QApplication) -> None:
    """Each recent button reopens its full path through on_open_recent."""
    dialog, _, opened = _make(recent=(_HTML_PATH, _MD_PATH))
    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in (_HTML_PATH, _MD_PATH)
    ]

    assert len(recent_buttons) == 2
    for button in recent_buttons:
        button.click()

    assert opened == [_HTML_PATH, _MD_PATH]


def test_many_recents_are_scrollable(qapp: QApplication) -> None:
    """A long run of debriefs is capped in a scroll area, all still reachable."""
    paths = tuple(f"C:/out/debrief_{index}.html" for index in range(8))
    dialog, _, _ = _make(recent=paths)

    assert dialog.findChildren(QScrollArea)  # the list is wrapped to scroll
    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in paths
    ]
    assert len(recent_buttons) == 8


def test_status_headline_is_shown(qapp: QApplication) -> None:
    """The current recording status headline appears in the dialog."""
    dialog, _, _ = _make()
    texts = [label.text() for label in dialog.findChildren(QLabel)]

    assert _STATUS in texts


def test_empty_recent_shows_placeholder(qapp: QApplication) -> None:
    """With no debriefs this run, a muted placeholder is shown instead."""
    dialog, _, opened = _make(recent=())
    texts = [label.text() for label in dialog.findChildren(QLabel)]

    assert _NO_RECENT in texts
    assert opened == []


def test_showing_the_dialog_brings_it_to_front(qapp: QApplication) -> None:
    """Showing runs the raise-and-activate path without error and is visible."""
    dialog, _, _ = _make()

    dialog.show()

    assert dialog.isVisible() is True
    dialog.close()


def test_refresh_updates_status_and_recent(qapp: QApplication) -> None:
    """refresh rebinds the status caption and rebuilds the recent list in place."""
    dialog, _, opened = _make(recent=())
    assert _NO_RECENT in [label.text() for label in dialog.findChildren(QLabel)]

    new_status = "Recording session: 9 events."
    dialog.refresh(new_status, (_HTML_PATH, _MD_PATH))

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert new_status in texts
    assert _NO_RECENT not in texts

    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in (_HTML_PATH, _MD_PATH)
    ]
    assert len(recent_buttons) == 2
    for button in recent_buttons:
        button.click()
    assert opened == [_HTML_PATH, _MD_PATH]


def test_refresh_to_empty_restores_placeholder(qapp: QApplication) -> None:
    """Refreshing to no recents swaps the list back to the placeholder."""
    dialog, _, _ = _make(recent=(_HTML_PATH, _MD_PATH))

    dialog.refresh(_STATUS, ())

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert _NO_RECENT in texts
    leftover = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in (_HTML_PATH, _MD_PATH)
    ]
    assert leftover == []


def test_refresh_past_threshold_becomes_scrollable(qapp: QApplication) -> None:
    """Refreshing past the threshold wraps the rebuilt list in a scroll area."""
    dialog, _, _ = _make(recent=())
    paths = tuple(f"C:/out/debrief_{index}.html" for index in range(8))

    dialog.refresh(_STATUS, paths)

    assert dialog.findChildren(QScrollArea)
    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in paths
    ]
    assert len(recent_buttons) == 8


def test_bring_to_front_clears_minimised_state(qapp: QApplication) -> None:
    """bring_to_front restores a minimised dialog by clearing the state flag."""
    dialog, _, _ = _make()
    dialog.show()
    dialog.setWindowState(Qt.WindowState.WindowMinimized)

    dialog.bring_to_front()

    assert not (dialog.windowState() & Qt.WindowState.WindowMinimized)
    dialog.close()
