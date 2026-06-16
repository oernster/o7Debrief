"""Tests for the SettingsDialog: export format, output folder and startup."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from o7debrief.application.dto.preferences import FORMAT_HTML, FORMAT_MARKDOWN
from o7debrief.ui.windows.settings import SettingsDialog

_DIR = "C:/Users/Cmdr/Downloads"


def _noop_save(_fmt, _on, _dir):  # type: ignore[no-untyped-def]
    """A save callback that ignores its arguments."""
    return None


def test_settings_dialog_preselects_the_current_format(qapp: QApplication) -> None:
    dialog = SettingsDialog(FORMAT_MARKDOWN, False, _DIR, _noop_save)

    assert dialog.selected_format() == FORMAT_MARKDOWN


def test_settings_dialog_defaults_to_html_for_an_unknown_format(
    qapp: QApplication,
) -> None:
    dialog = SettingsDialog("pdf", False, _DIR, _noop_save)

    assert dialog.selected_format() == FORMAT_HTML


def test_settings_dialog_reflects_the_autostart_state(qapp: QApplication) -> None:
    enabled = SettingsDialog(FORMAT_HTML, True, _DIR, _noop_save)
    disabled = SettingsDialog(FORMAT_HTML, False, _DIR, _noop_save)

    assert enabled.autostart_enabled() is True
    assert disabled.autostart_enabled() is False


def test_settings_dialog_shows_the_current_output_dir(qapp: QApplication) -> None:
    dialog = SettingsDialog(FORMAT_HTML, False, _DIR, _noop_save)

    assert dialog.selected_output_dir() == _DIR


def test_settings_dialog_save_reports_format_autostart_and_output(
    qapp: QApplication,
) -> None:
    saved: list[tuple[str, bool, str]] = []
    dialog = SettingsDialog(
        FORMAT_HTML, False, _DIR, lambda fmt, on, out: saved.append((fmt, on, out))
    )

    dialog._buttons[FORMAT_MARKDOWN].setChecked(True)
    dialog._autostart.setChecked(True)
    dialog._on_save_clicked()

    assert saved == [(FORMAT_MARKDOWN, True, _DIR)]


def test_settings_dialog_browse_updates_the_output_field(qapp: QApplication) -> None:
    chosen = "D:/EliteDebriefs"
    dialog = SettingsDialog(
        FORMAT_HTML,
        False,
        _DIR,
        _noop_save,
        dir_chooser=lambda _parent, _title, _start: chosen,
    )

    dialog._on_browse()

    assert dialog.selected_output_dir() == chosen


def test_settings_dialog_browse_keeps_field_when_cancelled(
    qapp: QApplication,
) -> None:
    dialog = SettingsDialog(
        FORMAT_HTML,
        False,
        _DIR,
        _noop_save,
        dir_chooser=lambda _parent, _title, _start: "",
    )

    dialog._on_browse()

    # A cancelled picker returns empty, leaving the existing value intact.
    assert dialog.selected_output_dir() == _DIR


def test_settings_dialog_cancel_reports_nothing(qapp: QApplication) -> None:
    saved: list[tuple[str, bool, str]] = []
    dialog = SettingsDialog(
        FORMAT_HTML, False, _DIR, lambda fmt, on, out: saved.append((fmt, on, out))
    )

    dialog.reject()

    assert saved == []
