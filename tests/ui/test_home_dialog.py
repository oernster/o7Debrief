"""Tests for HomeDialog: the left-click front door is a pure view.

Qt is real (offscreen). The dialog must own no behaviour: every button reports
through the injected callable, mirroring the tray menu so both entry points
drive the same use cases. The full path is preserved on each recent entry even
though the button shows only the file name.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea

from o7debrief.ui.windows.dialog_theme import HEADING_COLOUR
from o7debrief.ui.windows.home import HomeDialog

_STATUS = "Recording session: 4 events."
_HTML_PATH = "C:/out/debrief_2026.html"
_MD_PATH = "C:/out/debrief_2026.md"
_NO_RECENT = "No debriefs yet."

# Geometry, sampling offsets and colour tolerance for the scrolled-recents
# render check. The offsets land on the button's accent fill, left of its
# centred caption, so a sample is never taken on the dark glyphs.
_GRAB_WIDTH_PX = 460
_GRAB_HEIGHT_PX = 600
_LAYOUT_PASSES = 3
_FILL_SAMPLE_OFFSETS_PX = (16, 28, 40)
_COLOUR_TOLERANCE = 60


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


def _make_paged(
    recent: tuple[str, ...], page_index: int, page_count: int
) -> tuple[HomeDialog, list[int], list[int]]:
    """Build a HomeDialog on a given page; return it with the prev/next logs."""
    prev_calls: list[int] = []
    next_calls: list[int] = []
    dialog = HomeDialog(
        _STATUS,
        recent,
        on_debrief_last=lambda: None,
        on_debrief_history=lambda: None,
        on_settings=lambda: None,
        on_about=lambda: None,
        on_open_recent=lambda _path: None,
        on_prev_page=lambda: prev_calls.append(1),
        on_next_page=lambda: next_calls.append(1),
        page_index=page_index,
        page_count=page_count,
    )
    return dialog, prev_calls, next_calls


def _buttons(dialog: HomeDialog) -> dict[str, QPushButton]:
    """Map each button's caption to the button, for lookup by text."""
    return {b.text(): b for b in dialog.findChildren(QPushButton)}


def _colours_close(actual: QColor, expected: QColor, tolerance: int) -> bool:
    """Return whether two colours match within a per-channel tolerance."""
    return (
        abs(actual.red() - expected.red()) <= tolerance
        and abs(actual.green() - expected.green()) <= tolerance
        and abs(actual.blue() - expected.blue()) <= tolerance
    )


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
    """With no debriefs in the directory, a muted placeholder is shown."""
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


def test_set_status_updates_caption(qapp: QApplication) -> None:
    """set_status rebinds the live status caption in place."""
    dialog, _, _ = _make()

    dialog.set_status("Recording session: 99 events.")

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert "Recording session: 99 events." in texts


def test_show_recent_page_replaces_the_list(qapp: QApplication) -> None:
    """show_recent_page swaps an empty list for a page of reopenable buttons."""
    dialog, _, opened = _make(recent=())
    assert _NO_RECENT in [label.text() for label in dialog.findChildren(QLabel)]

    dialog.show_recent_page((_HTML_PATH, _MD_PATH), 0, 1)

    assert _NO_RECENT not in [label.text() for label in dialog.findChildren(QLabel)]
    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in (_HTML_PATH, _MD_PATH)
    ]
    assert len(recent_buttons) == 2
    for button in recent_buttons:
        button.click()
    assert opened == [_HTML_PATH, _MD_PATH]


def test_show_recent_page_to_empty_restores_placeholder(qapp: QApplication) -> None:
    """Showing an empty page swaps the list back to the placeholder."""
    dialog, _, _ = _make(recent=(_HTML_PATH, _MD_PATH))

    dialog.show_recent_page((), 0, 1)

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert _NO_RECENT in texts
    leftover = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in (_HTML_PATH, _MD_PATH)
    ]
    assert leftover == []


def test_show_recent_page_past_threshold_scrolls(qapp: QApplication) -> None:
    """A page longer than the threshold wraps the rebuilt list in a scroll area."""
    dialog, _, _ = _make(recent=())
    paths = tuple(f"C:/out/debrief_{index}.html" for index in range(8))

    dialog.show_recent_page(paths, 0, 1)

    assert dialog.findChildren(QScrollArea)
    recent_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() in paths
    ]
    assert len(recent_buttons) == 8


def test_pager_hidden_for_a_single_page(qapp: QApplication) -> None:
    """The pager is hidden when there is only one page of recents."""
    dialog, _, _ = _make_paged((_HTML_PATH,), 0, 1)

    assert dialog._pager.isHidden() is True


def test_pager_reflects_a_middle_page(qapp: QApplication) -> None:
    """On a middle page the pager shows the position with both arrows live."""
    dialog, _, _ = _make_paged((_HTML_PATH,), 1, 3)

    assert dialog._pager.isHidden() is False
    assert dialog._page_label.text() == "Page 2 of 3"
    assert dialog._prev_button.isEnabled() is True
    assert dialog._next_button.isEnabled() is True


def test_pager_disables_prev_on_the_first_page(qapp: QApplication) -> None:
    """Previous is disabled on the first page; next stays live."""
    dialog, _, _ = _make_paged((_HTML_PATH,), 0, 3)

    assert dialog._prev_button.isEnabled() is False
    assert dialog._next_button.isEnabled() is True


def test_pager_disables_next_on_the_last_page(qapp: QApplication) -> None:
    """Next is disabled on the last page; previous stays live."""
    dialog, _, _ = _make_paged((_HTML_PATH,), 2, 3)

    assert dialog._prev_button.isEnabled() is True
    assert dialog._next_button.isEnabled() is False


def test_prev_and_next_buttons_invoke_callbacks(qapp: QApplication) -> None:
    """The pager arrows report through their injected callbacks."""
    dialog, prev_calls, next_calls = _make_paged((_HTML_PATH,), 1, 3)

    dialog._prev_button.click()
    dialog._next_button.click()

    assert prev_calls == [1]
    assert next_calls == [1]


def test_bring_to_front_clears_minimised_state(qapp: QApplication) -> None:
    """bring_to_front restores a minimised dialog by clearing the state flag."""
    dialog, _, _ = _make()
    dialog.show()
    dialog.setWindowState(Qt.WindowState.WindowMinimized)

    dialog.bring_to_front()

    assert not (dialog.windowState() & Qt.WindowState.WindowMinimized)
    dialog.close()


def test_scrollable_recents_keep_visible_buttons(qapp: QApplication) -> None:
    """More than five recents stay visible: the scrolled buttons still paint.

    A blanket transparent stylesheet on the scroll viewport used to cascade onto
    the buttons, leaving dark text on the dark dialog. This grabs the dialog and
    asserts the first scrolled recent button still paints in the accent colour.
    """
    paths = tuple(f"C:/out/debrief_{index}.html" for index in range(8))
    dialog, _, _ = _make(recent=paths)
    dialog.resize(_GRAB_WIDTH_PX, _GRAB_HEIGHT_PX)
    dialog.show()
    for _ in range(_LAYOUT_PASSES):
        qapp.processEvents()

    button = next(b for b in dialog.findChildren(QPushButton) if b.toolTip() in paths)
    left = button.mapTo(dialog, button.rect().topLeft())
    middle = button.mapTo(dialog, button.rect().center())
    image = dialog.grab().toImage()
    accent = QColor(HEADING_COLOUR)
    painted = any(
        _colours_close(
            image.pixelColor(left.x() + dx, middle.y()), accent, _COLOUR_TOLERANCE
        )
        for dx in _FILL_SAMPLE_OFFSETS_PX
    )
    dialog.close()

    assert painted, "scrolled recent buttons are not painted in the accent colour"
