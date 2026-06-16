"""UI-layer tests for o7Debrief.

These tests exercise the real PySide6 ui objects against fake application
services (the application ports and services are duck-typed, so a fake stands
in without any real domain or infrastructure). Qt is never mocked: a real
QApplication runs on the offscreen platform set by the top-level conftest.
"""

from __future__ import annotations
