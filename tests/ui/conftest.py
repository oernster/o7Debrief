"""Qt fixtures for the ui tests.

A single QApplication is shared across the ui test session (Qt allows only
one per process), and an autouse fixture drains pending events and disposes of
any orphaned top-level widgets after each test so windows from one test cannot
leak into the next. The offscreen platform is already set by the repository
conftest, so these tests run headless without a display server.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    """Provide the one shared QApplication for the ui test session."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _drain_events(qapp: QApplication) -> Iterator[None]:
    """Process and clear pending Qt events around each ui test."""
    yield
    qapp.processEvents()
    for widget in qapp.topLevelWidgets():
        widget.deleteLater()
    qapp.processEvents()
