"""Shared dark-dossier styling for the o7Debrief dialogs.

The About and Licence dialogs adopt the same Elite Dangerous HUD palette as the
rendered report (dark background, light text, HUD-orange accents), so the app
feels of a piece. The palette lives here once and both dialogs apply it. The
heading colour is also exported so the HTML bodies can tint their headings to
match.

This module belongs to the ui layer and imports PySide6 only.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog

__all__ = ["HEADING_COLOUR", "TEXT_COLOUR", "apply_dialog_theme"]

# Elite Dangerous HUD palette, mirroring the HTML report's tokens.
_BACKGROUND = "#0d0d10"
_SURFACE = "#16161d"
_EDGE = "#2a2a33"
_ACCENT_SOFT = "#f8a24a"
TEXT_COLOUR = "#d7d7da"
HEADING_COLOUR = "#f07b05"

_STYLESHEET = f"""
QDialog {{ background: {_BACKGROUND}; }}
QLabel {{ color: {TEXT_COLOUR}; }}
QTextBrowser {{
    border: none;
    background: transparent;
    color: {TEXT_COLOUR};
}}
QLineEdit {{
    background: {_SURFACE}; color: {TEXT_COLOUR};
    border: 1px solid {_EDGE}; border-radius: 4px; padding: 5px 8px;
}}
QPushButton {{
    background: {HEADING_COLOUR};
    color: {_BACKGROUND};
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    font-weight: bold;
}}
QPushButton:hover {{ background: {_ACCENT_SOFT}; }}
"""


def apply_dialog_theme(dialog: QDialog) -> None:
    """Apply the dark-dossier palette to a dialog and its child widgets."""
    dialog.setStyleSheet(_STYLESHEET)
