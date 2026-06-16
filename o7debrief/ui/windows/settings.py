"""Settings dialog for o7Debrief: export format and startup behaviour.

The user-facing preferences are the format a generated debrief is saved as (a
self-contained HTML report by default, or Markdown for Discord or Reddit) and
whether o7Debrief starts in the system tray when they sign in to Windows. The
dialog preselects the current values and reports the chosen values through an
injected ``on_save`` callback. It performs no file, registry or network I/O
itself; the composition root applies the choices, so the ui stays free of
infrastructure.

This module belongs to the ui layer and imports the application layer (the
format identifiers) and PySide6.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from o7debrief.application.dto.preferences import (
    DEFAULT_EXPORT_FORMAT,
    FORMAT_HTML,
    FORMAT_MARKDOWN,
)
from o7debrief.ui.windows.dialog_theme import HEADING_COLOUR, apply_dialog_theme

__all__ = ["SettingsDialog"]

_TITLE = "Settings"
_SAVE_TEXT = "Save"
_CANCEL_TEXT = "Cancel"
_MIN_WIDTH_PX = 470
_FORMAT_HEADING = "Export format"
_FORMAT_PROMPT = "When a debrief is generated, save it as:"
_STARTUP_HEADING = "Startup"
_AUTOSTART_LABEL = "Start o7 Debrief in the system tray when I sign in to Windows"
_OUTPUT_HEADING = "Output folder"
_OUTPUT_PROMPT = "Save generated debrief files to:"
_BROWSE_TEXT = "Browse..."
_BROWSE_TITLE = "Choose the debrief output folder"

# Each export format and the label shown for it, in display order.
_CHOICES = (
    (FORMAT_HTML, "HTML  (a self-contained report, recommended)"),
    (FORMAT_MARKDOWN, "Markdown  (for pasting into Discord or Reddit)"),
)


def _heading(text: str) -> QLabel:
    """Return a section heading label in the accent colour."""
    label = QLabel(text)
    label.setStyleSheet(f"color: {HEADING_COLOUR}; font-weight: bold;")
    return label


def _default_dir_chooser(parent: QWidget, title: str, start: str) -> str:
    """Open a native folder picker; return the chosen path or an empty string."""
    return QFileDialog.getExistingDirectory(parent, title, start)


class SettingsDialog(QDialog):
    """Lets the user choose the export format and startup behaviour."""

    def __init__(
        self,
        current_format: str,
        autostart_enabled: bool,
        current_output_dir: str,
        on_save: Callable[[str, bool, str], None],
        dir_chooser: Callable[[QWidget, str, str], str] = _default_dir_chooser,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_TITLE)
        self.setMinimumWidth(_MIN_WIDTH_PX)
        apply_dialog_theme(self)
        self._on_save = on_save
        self._dir_chooser = dir_chooser
        self._buttons: dict[str, QRadioButton] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(_heading(_FORMAT_HEADING))
        layout.addWidget(QLabel(_FORMAT_PROMPT))

        selected = (
            current_format
            if current_format in dict(_CHOICES)
            else DEFAULT_EXPORT_FORMAT
        )
        group = QButtonGroup(self)
        for value, label in _CHOICES:
            radio = QRadioButton(label)
            radio.setChecked(value == selected)
            group.addButton(radio)
            layout.addWidget(radio)
            self._buttons[value] = radio

        layout.addWidget(_heading(_OUTPUT_HEADING))
        layout.addWidget(QLabel(_OUTPUT_PROMPT))
        self._output_edit = QLineEdit(current_output_dir)
        browse_button = QPushButton(_BROWSE_TEXT)
        browse_button.clicked.connect(self._on_browse)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_edit)
        output_row.addWidget(browse_button)
        layout.addLayout(output_row)

        layout.addWidget(_heading(_STARTUP_HEADING))
        self._autostart = QCheckBox(_AUTOSTART_LABEL)
        self._autostart.setChecked(autostart_enabled)
        layout.addWidget(self._autostart)

        row = QHBoxLayout()
        cancel_button = QPushButton(_CANCEL_TEXT)
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton(_SAVE_TEXT)
        save_button.clicked.connect(self._on_save_clicked)
        row.addStretch()
        row.addWidget(cancel_button)
        row.addWidget(save_button)
        layout.addLayout(row)

    def selected_format(self) -> str:
        """Return the format identifier of the checked radio button."""
        for value, radio in self._buttons.items():
            if radio.isChecked():
                return value
        return DEFAULT_EXPORT_FORMAT

    def autostart_enabled(self) -> bool:
        """Return whether the autostart checkbox is ticked."""
        return self._autostart.isChecked()

    def selected_output_dir(self) -> str:
        """Return the chosen output directory text."""
        return self._output_edit.text().strip()

    def _on_browse(self) -> None:
        """Let the user pick an output directory, updating the field."""
        chosen = self._dir_chooser(self, _BROWSE_TITLE, self._output_edit.text())
        if chosen:
            self._output_edit.setText(chosen)

    def _on_save_clicked(self) -> None:
        """Report the chosen format, startup and output preferences; close."""
        self._on_save(
            self.selected_format(),
            self.autostart_enabled(),
            self.selected_output_dir(),
        )
        self.accept()
