"""FilesystemDebriefArchive: list debriefs in the configured output directory.

Implements the application ``DebriefArchive`` port by globbing the directory the
sink writes to for files named like a generated debrief (the shared stem plus a
valid export suffix) and ordering them newest first by their timestamped name.
The effective directory is resolved on each call from the saved preferences, so
the archive follows the user's chosen output location. Listing is a cheap
directory read; only the ui decides how many entries to realise, via the page
slice, so a large back-catalogue never builds every entry at once.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from o7debrief.application.dto.preferences import VALID_EXPORT_FORMATS
from o7debrief.application.services.debrief_naming import debrief_prefix
from o7debrief.infrastructure.render.html_bundle_exporter import (
    BUNDLE_DIRECTORY_NAME,
)

if TYPE_CHECKING:  # pragma: no cover - type-only import, no runtime dependency
    from o7debrief.application.ports.preferences_store import PreferencesStore

__all__ = ["FilesystemDebriefArchive"]

# Separator between a suffix and the rest of a filename, e.g. the dot in ".html".
_SUFFIX_DOT = "."
# The file a reader opens inside a history bundle. The bundle is a directory
# rather than a file, so the archive lists this rather than the directory: the
# recents list and the browser both want something openable.
_BUNDLE_ENTRY = "index.html"


class FilesystemDebriefArchive:
    """Lists debrief files in the output directory (port: DebriefArchive)."""

    def __init__(self, default_dir: Path | str, preferences: PreferencesStore) -> None:
        self._default_dir = Path(default_dir)
        self._preferences = preferences

    def count(self) -> int:
        """Return how many debrief files are in the effective directory."""
        return len(self._sorted_paths())

    def list_page(self, offset: int, limit: int) -> tuple[str, ...]:
        """Return up to ``limit`` debrief paths from ``offset``, newest first."""
        return tuple(self._sorted_paths()[offset : offset + limit])

    def _effective_dir(self) -> Path:
        """Return the configured output directory, else the default."""
        configured = self._preferences.load().output_dir
        return Path(configured) if configured else self._default_dir

    def _sorted_paths(self) -> list[str]:
        """Return every debrief file path in the directory, newest first.

        Matching is by the shared debrief filename prefix and a valid export
        suffix, so in-flight temporary files and unrelated files are ignored.
        The timestamped name sorts lexically, so a reverse name sort is exactly
        newest first without reading any file modification time.

        The history bundle heads the list whenever it exists. It is not dated,
        because it is rewritten in place rather than produced afresh each run,
        so it is always the current one rather than one of a series.
        """
        directory = self._effective_dir()
        if not directory.is_dir():
            return []
        prefix = debrief_prefix()
        suffixes = {f"{_SUFFIX_DOT}{fmt}" for fmt in VALID_EXPORT_FORMATS}
        matches = [
            entry
            for entry in directory.iterdir()
            if entry.is_file()
            and entry.name.startswith(prefix)
            and entry.suffix in suffixes
        ]
        matches.sort(key=lambda entry: entry.name, reverse=True)
        return _bundle_first(directory) + [str(entry) for entry in matches]


def _bundle_first(directory: Path) -> list[str]:
    """Return the history bundle's entry point if the bundle is present.

    A bundle is a directory, so the ordinary file scan cannot see it and the
    recents list would silently lose the history report the moment it stopped
    being one document.
    """
    entry = directory / BUNDLE_DIRECTORY_NAME / _BUNDLE_ENTRY
    return [str(entry)] if entry.is_file() else []
