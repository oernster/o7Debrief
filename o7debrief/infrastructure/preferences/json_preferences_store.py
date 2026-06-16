"""JsonPreferencesStore: persist the user's preferences as JSON.

This adapter implements the application ``PreferencesStore`` port. Preferences
are stored as a small JSON file under a configured directory and written
atomically (a temporary file plus ``os.replace``). A missing, unreadable or
invalid file loads as the defaults, so a first run or a hand-edited file never
crashes the app; the export format is normalised to a known format, defaulting
to HTML.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from o7debrief.application.dto.preferences import (
    DEFAULT_EXPORT_FORMAT,
    VALID_EXPORT_FORMATS,
    Preferences,
)

__all__ = ["JsonPreferencesStore"]

# Filename and atomic-write temp suffix for the stored preferences.
_FILE_NAME = "preferences.json"
_TEMP_SUFFIX = ".tmp"
_ENCODING = "utf-8"
# JSON keys for the stored preferences.
_EXPORT_FORMAT_KEY = "export_format"
_OUTPUT_DIR_KEY = "output_dir"
# Default output directory: empty means the application's default location.
_DEFAULT_OUTPUT_DIR = ""


def _format_from(data: object) -> str:
    """Return a valid export format from decoded JSON, else the default."""
    if isinstance(data, dict):
        value = data.get(_EXPORT_FORMAT_KEY)
        if isinstance(value, str) and value in VALID_EXPORT_FORMATS:
            return value
    return DEFAULT_EXPORT_FORMAT


def _output_dir_from(data: object) -> str:
    """Return the stored output directory string, else the default."""
    if isinstance(data, dict):
        value = data.get(_OUTPUT_DIR_KEY)
        if isinstance(value, str):
            return value
    return _DEFAULT_OUTPUT_DIR


class JsonPreferencesStore:
    """Persists the user's preferences as JSON (port: PreferencesStore)."""

    def __init__(self, directory: Path | str) -> None:
        self._directory = Path(directory)

    def load(self) -> Preferences:
        """Return the saved preferences, or the defaults when absent or odd."""
        try:
            text = self._path().read_text(encoding=_ENCODING)
        except OSError:
            return Preferences()
        try:
            data = json.loads(text)
        except ValueError:
            return Preferences()
        return Preferences(
            export_format=_format_from(data),
            output_dir=_output_dir_from(data),
        )

    def save(self, preferences: Preferences) -> None:
        """Persist the given preferences atomically as JSON."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._path()
        temporary = path.with_name(f"{path.name}{_TEMP_SUFFIX}")
        payload = {
            _EXPORT_FORMAT_KEY: preferences.export_format,
            _OUTPUT_DIR_KEY: preferences.output_dir,
        }
        temporary.write_text(json.dumps(payload), encoding=_ENCODING)
        os.replace(temporary, path)

    def _path(self) -> Path:
        """Return the preferences file path."""
        return self._directory / _FILE_NAME
