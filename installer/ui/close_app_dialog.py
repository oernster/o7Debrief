"""Offering to close a running application before the files are replaced.

Telling the user to go and close it themselves leaves them to find a tray icon
and come back. Offering to do it is one click, so that is what is offered, with
the consequence stated plainly because the running session ends. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer.constants import APP_DISPLAY_NAME
from installer.ui.icons import app_icon
from installer.ui.themes import (
    BUTTON_GAP,
    DIALOG_MARGIN,
    PRIMARY_ACTION,
    SECONDARY_ACTION,
    STYLESHEET,
)

CONFIRM_LABEL = "Close it and continue"
CANCEL_LABEL = "Cancel"
MESSAGE = (
    f"{APP_DISPLAY_NAME} is running and its files cannot be replaced while it "
    "is open. Close it now and continue? Anything it is part way through will "
    "be ended."
)


class CloseAppDialog(QDialog):
    """A themed confirmation for ending the running application."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Close {APP_DISPLAY_NAME}")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        message = QLabel(MESSAGE)
        message.setWordWrap(True)
        layout.addWidget(message)

        confirm = QPushButton(CONFIRM_LABEL)
        confirm.setObjectName(PRIMARY_ACTION)
        confirm.clicked.connect(self.accept)
        cancel = QPushButton(CANCEL_LABEL)
        cancel.setObjectName(SECONDARY_ACTION)
        cancel.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)
