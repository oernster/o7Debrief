"""Home dialog for o7Debrief: the front door opened by a left-click on the tray.

A left-click on the tray icon opens this dialog; a right-click still shows the
full context menu. It presents the live recording status, the two debrief
actions, any debriefs produced this run and quick links to Settings and About.
The dialog owns no behaviour of its own: every button reports through an
injected callable, exactly as the tray menu does, so both entry points drive
the same use cases and this stays a pure view.

This module belongs to the ui layer and imports the ui theme helper and PySide6
only.
"""

from __future__ import annotations

from pathlib import PurePath
from typing import Callable, Sequence

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from o7debrief.ui.windows.dialog_theme import HEADING_COLOUR, apply_dialog_theme

__all__ = ["HomeDialog"]

_TITLE = "o7 Debrief"
_TAGLINE = "Commander Mission Debrief"

# Button and section captions, held as named constants so wording lives in one
# place and the tests can find widgets by their text.
_LAST_SESSION_TEXT = "Debrief my last session"
_HISTORY_TEXT = "Debrief my history to date"
_SETTINGS_TEXT = "Settings"
_ABOUT_TEXT = "About"
_CLOSE_TEXT = "Close"
_RECENT_HEADING = "Recent debriefs"
_NO_RECENT_TEXT = "No debriefs yet this run."

# Dialog geometry and typography, as named layout constants.
_ICON_PX = 64
_MIN_WIDTH_PX = 460
_SPACING_PX = 10
_DIVIDER_PX = 1
_NO_MARGIN = 0
# Beyond this many recent debriefs the list scrolls inside a capped panel
# rather than growing the dialog past the bottom of the screen.
_RECENT_SCROLL_THRESHOLD = 5
_RECENT_MAX_HEIGHT_PX = 220

# Title styling, mirroring the heading colour from the shared dialog theme.
_TITLE_STYLE = f"color: {HEADING_COLOUR}; font-size: 20px; font-weight: bold;"
_HEADING_STYLE = f"color: {HEADING_COLOUR}; font-weight: bold;"


def _heading(text: str) -> QLabel:
    """Return a section heading label in the accent colour."""
    label = QLabel(text)
    label.setStyleSheet(_HEADING_STYLE)
    return label


def _divider() -> QFrame:
    """Return a thin horizontal divider line."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(_DIVIDER_PX)
    return line


class HomeDialog(QDialog):
    """The left-click front door: status, debrief actions and quick links."""

    def __init__(
        self,
        status_text: str,
        recent: Sequence[str],
        *,
        on_debrief_last: Callable[[], None],
        on_debrief_history: Callable[[], None],
        on_settings: Callable[[], None],
        on_about: Callable[[], None],
        on_open_recent: Callable[[str], None],
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_TITLE)
        self.setMinimumWidth(_MIN_WIDTH_PX)
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)
        apply_dialog_theme(self)
        self._on_open_recent = on_open_recent

        layout = QVBoxLayout(self)
        layout.setSpacing(_SPACING_PX)
        layout.addLayout(self._build_header(icon))

        status = QLabel(status_text)
        status.setWordWrap(True)
        layout.addWidget(status)

        layout.addWidget(_divider())
        layout.addWidget(self._action_button(_LAST_SESSION_TEXT, on_debrief_last))
        layout.addWidget(self._action_button(_HISTORY_TEXT, on_debrief_history))

        layout.addWidget(_heading(_RECENT_HEADING))
        layout.addWidget(self._build_recent(recent))

        layout.addWidget(_divider())
        layout.addLayout(self._build_footer(on_settings, on_about))

    def showEvent(self, event: QShowEvent) -> None:
        """Raise and focus the dialog when shown so it lands in front.

        Opened from a tray left-click the app is not the foreground window;
        without this the dialog can surface behind other windows. The click
        grants the process focus rights; clearing any minimised state then
        raising and activating here brings it reliably to the front.
        """
        super().showEvent(event)
        self.setWindowState(
            (self.windowState() & ~Qt.WindowState.WindowMinimized)
            | Qt.WindowState.WindowActive
        )
        self.raise_()
        self.activateWindow()

    def _build_header(self, icon: QIcon | None) -> QHBoxLayout:
        """Build the header row: the app icon beside the name and tagline."""
        header = QHBoxLayout()
        if icon is not None and not icon.isNull():
            badge = QLabel()
            badge.setPixmap(icon.pixmap(QSize(_ICON_PX, _ICON_PX)))
            header.addWidget(badge)
        titles = QVBoxLayout()
        title = QLabel(_TITLE)
        title.setStyleSheet(_TITLE_STYLE)
        titles.addWidget(title)
        titles.addWidget(QLabel(_TAGLINE))
        header.addLayout(titles)
        header.addStretch()
        return header

    def _action_button(self, text: str, handler: Callable[[], None]) -> QPushButton:
        """Return a primary action button wired to a no-argument handler."""
        button = QPushButton(text)
        button.clicked.connect(lambda _checked=False: handler())
        return button

    def _build_recent(self, recent: Sequence[str]) -> QWidget:
        """Build the recent-debriefs list, or a muted placeholder when empty.

        A long run can produce many debriefs, so once the list passes a
        threshold it is capped and scrolls rather than growing the dialog past
        the bottom of the screen.
        """
        if not recent:
            empty = QLabel(_NO_RECENT_TEXT)
            empty.setEnabled(False)
            return empty
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(_NO_MARGIN, _NO_MARGIN, _NO_MARGIN, _NO_MARGIN)
        column.setSpacing(_SPACING_PX)
        for path in recent:
            column.addWidget(self._recent_button(path))
        if len(recent) <= _RECENT_SCROLL_THRESHOLD:
            return container
        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setFixedHeight(_RECENT_MAX_HEIGHT_PX)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        return scroll

    def _recent_button(self, path: str) -> QPushButton:
        """Return a button that reopens one produced debrief by its path."""
        button = QPushButton(PurePath(path).name or path)
        button.setToolTip(path)
        button.clicked.connect(
            lambda _checked=False, target=path: self._on_open_recent(target)
        )
        return button

    def _build_footer(
        self, on_settings: Callable[[], None], on_about: Callable[[], None]
    ) -> QHBoxLayout:
        """Build the footer row: Settings, About and Close."""
        row = QHBoxLayout()
        settings_button = QPushButton(_SETTINGS_TEXT)
        settings_button.clicked.connect(lambda _checked=False: on_settings())
        about_button = QPushButton(_ABOUT_TEXT)
        about_button.clicked.connect(lambda _checked=False: on_about())
        close_button = QPushButton(_CLOSE_TEXT)
        close_button.clicked.connect(self.accept)
        row.addWidget(settings_button)
        row.addWidget(about_button)
        row.addStretch()
        row.addWidget(close_button)
        return row
