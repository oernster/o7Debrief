"""Tests for the LicenceDialog: it shows the injected licence text, scrollable.

The dialog is display-only and receives the licence text by injection (the
composition root reads the bundled LICENCE file), so these tests pass a sample
in rather than reading the real file.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton, QTextBrowser

from o7debrief.ui.windows.licence import LicenceDialog

_SAMPLE = (
    "GNU LESSER GENERAL PUBLIC LICENSE\n"
    "Version 3, 29 June 2007\n\n"
    "This is the body of the licence text used in tests.\n"
)


def _body_text(dialog: LicenceDialog) -> str:
    return dialog.findChild(QTextBrowser).toPlainText()


def test_licence_dialog_shows_the_injected_text(qapp: QApplication) -> None:
    text = _body_text(LicenceDialog(_SAMPLE))

    assert "GNU LESSER GENERAL PUBLIC LICENSE" in text
    assert "body of the licence text" in text


def test_licence_dialog_title_names_lgpl(qapp: QApplication) -> None:
    assert "LGPL-3.0" in LicenceDialog(_SAMPLE).windowTitle()


def test_licence_dialog_preserves_multiple_lines(qapp: QApplication) -> None:
    # The full licence is multi-line; the dialog must not collapse it.
    text = _body_text(LicenceDialog(_SAMPLE))

    assert "Version 3, 29 June 2007" in text


def test_licence_dialog_has_a_close_button(qapp: QApplication) -> None:
    dialog = LicenceDialog(_SAMPLE)

    captions = [button.text() for button in dialog.findChildren(QPushButton)]
    assert "Close" in captions
