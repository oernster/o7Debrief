"""Tests for the AboutDialog: identity, version and credits content."""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton, QTextBrowser

from o7debrief import __version__
from o7debrief.ui.windows.about import AboutDialog


def _body_text(dialog: AboutDialog) -> str:
    return dialog.findChild(QTextBrowser).toPlainText()


def test_about_dialog_shows_identity_and_version(qapp: QApplication) -> None:
    dialog = AboutDialog(QIcon())

    assert dialog.windowTitle() == "About o7 Debrief"
    text = _body_text(dialog)
    assert "o7 Debrief" in text
    assert "Commander Mission Debrief" in text
    assert __version__ in text
    assert "Oliver Ernster" in text
    assert "LGPL-3.0" in text


def test_about_dialog_credits_real_dependencies(qapp: QApplication) -> None:
    text = _body_text(AboutDialog(QIcon()))

    for project in ("Python", "PySide6", "Jinja2", "Nuitka", "pytest", "flake8"):
        assert project in text
    assert "Python community" in text


def test_about_dialog_omits_unused_dependencies(qapp: QApplication) -> None:
    # o7Debrief uses stdlib ctypes/msvcrt and Nuitka, not these libraries.
    text = _body_text(AboutDialog(QIcon()))

    for absent in ("SQLite", "bcrypt", "pywin32", "PyInstaller"):
        assert absent not in text


def test_about_dialog_has_a_close_button(qapp: QApplication) -> None:
    dialog = AboutDialog(QIcon())

    captions = [button.text() for button in dialog.findChildren(QPushButton)]
    assert "Close" in captions
