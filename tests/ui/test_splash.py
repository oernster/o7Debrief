"""Tests for the SplashScreen: identity, version and the tray message."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from o7debrief.ui.windows.splash import SplashScreen

# The splash must stay up long enough to actually read the tray message, not
# just glimpse it. This is the minimum on-screen time the default must meet.
_READABLE_MIN_MS = 8000


def _all_text(splash: SplashScreen) -> str:
    return " ".join(label.text() for label in splash.findChildren(QLabel))


def test_splash_shows_name_version_and_tray_message(qapp: QApplication) -> None:
    splash = SplashScreen(QIcon(), "1.2.3")

    text = _all_text(splash)
    assert "o7 Debrief" in text
    assert "1.2.3" in text
    assert "system tray" in text


def test_splash_is_frameless(qapp: QApplication) -> None:
    splash = SplashScreen(QIcon(), "1.2.3")

    assert bool(splash.windowFlags() & Qt.WindowType.FramelessWindowHint)


def test_splash_default_duration_is_long_enough_to_read(
    qapp: QApplication,
) -> None:
    # The default must keep the splash up for at least the readable minimum so
    # users can read the tray message before it dismisses itself.
    splash = SplashScreen(QIcon(), "1.2.3")

    assert splash._duration_ms >= _READABLE_MIN_MS
