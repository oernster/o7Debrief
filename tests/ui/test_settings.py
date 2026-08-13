"""Tests for the SettingsDialog: export format, output folder and startup."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from o7debrief.application.dto.preferences import FORMAT_HTML, FORMAT_MARKDOWN
from o7debrief.ui.windows.settings import SettingsDialog

_DIR = "C:/Users/Cmdr/Downloads"

# Controls that paint their own caption instead of using a QLabel, so the
# theme's QLabel colour rule does not reach them.
_CAPTION_CONTROL_SELECTORS = ("QRadioButton", "QCheckBox")


def _noop_save(_fmt, _on, _dir):  # type: ignore[no-untyped-def]
    """A save callback that ignores its arguments."""
    return


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


def test_settings_dialog_theme_sets_a_colour_for_every_caption_control(
    qapp: QApplication,
) -> None:
    """Every control that paints its own caption needs an explicit colour.

    A QRadioButton and a QCheckBox draw their captions themselves rather than
    through a QLabel, so the theme's QLabel rule never reached them and they
    fell back to the desktop palette: near black on this near black dialog,
    invisible on a dark Linux desktop while readable on Windows.

    This asserts the rule exists rather than sampling the rendered pixels. A
    pixel test cannot fail here: the offscreen platform used by the suite
    supplies its own light default palette, so the captions render legibly
    with or without the fix and the very palette dependency that caused the
    defect is the thing the test environment does not reproduce.
    """
    dialog = SettingsDialog(FORMAT_HTML, False, _DIR, _noop_save)
    sheet = dialog.styleSheet()

    for selector in _CAPTION_CONTROL_SELECTORS:
        assert f"{selector} {{ color:" in sheet
