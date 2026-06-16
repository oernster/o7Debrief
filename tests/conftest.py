"""Shared pytest configuration and fixtures for o7Debrief.

This module sets the Qt platform to offscreen at import time so that any test
touching PySide6 runs headless without a display server. It also provides a
couple of dependency-light fixtures for the infrastructure tests authored by
other agents: a temporary journal-directory factory and a helper that writes
newline-delimited JSON journal lines to a file.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

import pytest

# Set the Qt platform before any PySide6 import can occur. Doing this at module
# import time (rather than inside a fixture) guarantees it is in place no matter
# how the importing test is collected, which keeps it autouse-safe.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Type aliases for the factory fixtures, kept here so the signatures read well.
JournalDirFactory = Callable[..., Path]
JournalWriter = Callable[[Path, list[dict[str, Any]]], Path]

# Default basename for a journal file created by the writer helper. Elite
# Dangerous journal files follow a "Journal.<timestamp>.<part>.log" shape; the
# tests only need a stable, recognisable default, overridable per call.
DEFAULT_JOURNAL_NAME = "Journal.test.01.log"


@pytest.fixture
def journal_dir_factory(tmp_path: Path) -> JournalDirFactory:
    """Return a factory that creates fresh journal directories under tmp_path.

    Each call makes a new subdirectory so that tests requiring more than one
    journal location do not collide. The optional name lets a test pick a
    meaningful directory name; it defaults to a numbered directory.
    """
    created: list[Path] = []

    def _make(name: str | None = None) -> Path:
        resolved = name if name is not None else f"journals_{len(created)}"
        path = tmp_path / resolved
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
        return path

    return _make


@pytest.fixture
def write_journal_lines() -> JournalWriter:
    """Return a helper that writes events as newline-delimited JSON.

    The helper serialises each event mapping to a single JSON line and joins
    them with newlines, matching the line-delimited format of Elite Dangerous
    journal files. It returns the path written so a test can read it straight
    back.
    """

    def _write(
        directory: Path,
        events: list[dict[str, Any]],
        name: str = DEFAULT_JOURNAL_NAME,
    ) -> Path:
        path = directory / name
        lines = [json.dumps(event) for event in events]
        # A trailing newline keeps the file well formed for line-by-line reads.
        text = "\n".join(lines)
        if lines:
            text += "\n"
        path.write_text(text, encoding="utf-8")
        return path

    return _write
