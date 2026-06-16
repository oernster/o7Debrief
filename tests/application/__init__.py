"""Unit tests for the o7Debrief application layer.

These tests exercise the application services and DTOs against hand-written
fakes for every port. They build real domain objects as inputs (never
mocking the domain) and assert the formatted DebriefView contract shape.
No infrastructure is imported.
"""

from __future__ import annotations
