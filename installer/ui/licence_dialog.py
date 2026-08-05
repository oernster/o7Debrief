"""A themed, scrollable view of the bundled licence text.

Licence texts arrive hard-wrapped, so the view does not wrap them again: it is
sized to the widest line instead, which keeps the original layout readable
rather than reflowing it into ragged pairs of lines. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from installer.constants import APP_DISPLAY_NAME
from installer.ui.icons import app_icon
from installer.ui.themes import (
    BORDER_PX,
    BUTTON_GAP,
    DIALOG_MARGIN,
    LICENCE_DIALOG_HEIGHT,
    LICENCE_VIEW,
    SECONDARY_ACTION,
    SIDES,
    STYLESHEET,
    TEXT_PADDING_PX,
    WIDTH_SAFETY_PX,
)

CLOSE_LABEL = "Close"


def licence_view_width(view: QTextEdit, text: str) -> int:
    """Return the pixel width that shows the widest licence line in full."""
    view.ensurePolished()
    metrics = view.fontMetrics()
    lines = text.splitlines() or [text]
    widest = max(metrics.horizontalAdvance(line) for line in lines)
    doc_margin = round(view.document().documentMargin())
    scrollbar = view.verticalScrollBar().sizeHint().width()
    chrome = SIDES * (doc_margin + TEXT_PADDING_PX + BORDER_PX)
    return widest + scrollbar + chrome + WIDTH_SAFETY_PX


def close_row(dialog: QDialog) -> QHBoxLayout:
    """Return the shared trailing row holding a single Close button."""
    close = QPushButton(CLOSE_LABEL)
    close.setObjectName(SECONDARY_ACTION)
    close.clicked.connect(dialog.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(close)
    return row


class LicenceDialog(QDialog):
    """A themed, scrollable view of the bundled licence text."""

    def __init__(self, licence_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} Licence")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        view = QTextEdit()
        view.setObjectName(LICENCE_VIEW)
        view.setReadOnly(True)
        view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        view.setPlainText(licence_text)
        layout.addWidget(view)

        width = licence_view_width(view, licence_text)
        view.setMinimumWidth(width)
        self.resize(width + SIDES * DIALOG_MARGIN, LICENCE_DIALOG_HEIGHT)

        layout.addLayout(close_row(self))
