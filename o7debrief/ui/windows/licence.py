"""Licence dialog for o7Debrief: shows the full LGPL-3.0 licence text.

o7Debrief links the LGPL-3.0 PySide6/Qt libraries, so the application itself is
distributed under the GNU Lesser General Public Licence v3.0. This dialog shows
the full licence text verbatim in a scrollable, read-only view. The text is
injected by the composition root, which reads the bundled LICENCE file, so the
dialog performs no file or network I/O and the LICENCE file stays the single
source of truth for the licence.

This module belongs to the ui layer and imports PySide6 only.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from o7debrief.ui.windows.dialog_theme import apply_dialog_theme

__all__ = ["LicenceDialog"]

_TITLE = "Licence - LGPL-3.0"
_CLOSE_TEXT = "Close"
_MIN_HEIGHT_PX = 560
# Monospace family for the pre-formatted licence text; falls back to the
# platform monospace face when this exact family is absent.
_MONOSPACE_FAMILY = "Consolas"
# Breathing room added to the measured text width so the widest licence line is
# not left flush against the scrollbar.
_WIDTH_PAD_PX = 8


class LicenceDialog(QDialog):
    """Shows the full LGPL-3.0 licence text in a scrollable, read-only view."""

    def __init__(self, licence_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_TITLE)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setPlainText(licence_text)
        font = QFont(_MONOSPACE_FAMILY)
        font.setStyleHint(QFont.StyleHint.Monospace)
        body.setFont(font)
        body.setMinimumWidth(self._text_width(body, licence_text))
        layout.addWidget(body)

        row = QHBoxLayout()
        close_button = QPushButton(_CLOSE_TEXT)
        close_button.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)

        self.setMinimumHeight(_MIN_HEIGHT_PX)

    def _text_width(self, body: QTextBrowser, licence_text: str) -> int:
        """Return the pixel width needed to show the widest licence line.

        Measuring from the body's own monospace font sizes the dialog to the
        text instead of a fixed guess, then widens it for the document margin,
        the vertical scrollbar and a little breathing room.
        """
        metrics = QFontMetrics(body.font())
        widest = max(
            (metrics.horizontalAdvance(line) for line in licence_text.splitlines()),
            default=0,
        )
        margin = 2 * int(body.document().documentMargin())
        scrollbar = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        return widest + margin + scrollbar + _WIDTH_PAD_PX
