"""Startup splash for o7Debrief: a brief, rounded, frameless card.

Shown once at launch, it carries the application icon, the name and version, and
a short note that the app keeps running in the system tray after the splash
fades. It stays on screen long enough to read, then dismisses itself, so it
never gets in the way.

This module belongs to the ui layer and imports PySide6 only.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

__all__ = ["SplashScreen"]

_APP_NAME = "o7 Debrief"
_TRAY_MESSAGE = (
    "Now running in the background. Look for the icon in your system tray "
    "(bottom-right) and right-click it any time."
)

# How long the splash stays on screen before it dismisses itself. Chosen to be
# long enough to comfortably read the tray message rather than just glimpse it.
_DEFAULT_DURATION_MS = 8000

# Card geometry and palette (the dark-dossier look, with rounded corners).
_WIDTH_PX = 440
_HEIGHT_PX = 280
_ICON_PX = 76
_CORNER_RADIUS_PX = 18
_SPACING_PX = 8
_NO_MARGIN = 0
_BACKGROUND = "#16161d"
_EDGE = "#2a2a33"
_ACCENT = "#f07b05"
_TEXT = "#d7d7da"
_MUTED = "#8a8a93"
_NAME_POINT_SIZE = 24


class SplashScreen(QWidget):
    """A brief, rounded, frameless splash shown while the app starts up."""

    def __init__(
        self,
        icon: QIcon | None = None,
        version: str = "",
        duration_ms: int = _DEFAULT_DURATION_MS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._duration_ms = duration_ms
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(_WIDTH_PX, _HEIGHT_PX)
        self._build_ui(icon, version)

    def _build_ui(self, icon: QIcon | None, version: str) -> None:
        """Lay out the rounded card with the icon, name, version and message."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(_NO_MARGIN, _NO_MARGIN, _NO_MARGIN, _NO_MARGIN)

        card = QFrame()
        card.setObjectName("splashCard")
        card.setStyleSheet(
            f"#splashCard {{ background: {_BACKGROUND}; "
            f"border: 1px solid {_EDGE}; border-radius: {_CORNER_RADIUS_PX}px; }}"
        )
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(_SPACING_PX)

        if icon is not None and not icon.isNull():
            image = QLabel()
            image.setPixmap(icon.pixmap(QSize(_ICON_PX, _ICON_PX)))
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image)

        name = QLabel(_APP_NAME)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(
            f"color: {_ACCENT}; font-size: {_NAME_POINT_SIZE}px; font-weight: bold;"
        )
        layout.addWidget(name)

        version_label = QLabel(f"Version {version}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"color: {_MUTED};")
        layout.addWidget(version_label)

        message = QLabel(_TRAY_MESSAGE)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setStyleSheet(f"color: {_TEXT};")
        layout.addWidget(message)

    def show_briefly(self) -> None:
        """Centre the splash on screen, show it and dismiss it after a moment."""
        self._centre_on_screen()
        self.show()
        QTimer.singleShot(self._duration_ms, self.close)

    def _centre_on_screen(self) -> None:
        """Move the splash to the centre of the primary screen, if there is one."""
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            centre = screen.availableGeometry().center()
            self.move(centre - self.rect().center())
