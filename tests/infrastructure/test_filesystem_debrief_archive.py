"""Tests for FilesystemDebriefArchive: listing, ordering, filtering and paging.

A real temporary directory stands in for the output folder. Files are named like
generated debriefs (and some unrelated ones), so the tests assert the archive
lists only debriefs, newest first, slices pages correctly, follows the
configured output directory and tolerates a missing directory.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.application.dto.preferences import Preferences
from o7debrief.infrastructure.archive.filesystem_debrief_archive import (
    FilesystemDebriefArchive,
)

from tests.application.fakes import FakePreferencesStore


def _write(directory: Path, name: str) -> None:
    """Create a small file ``name`` inside ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(b"x")


def _names(paths: tuple[str, ...]) -> list[str]:
    """Return just the file names of a tuple of full paths."""
    return [Path(path).name for path in paths]


def test_lists_debrief_files_newest_first(tmp_path: Path) -> None:
    """Debriefs are returned ordered by their timestamped name, newest first."""
    _write(tmp_path, "debrief_2026-06-15_10-00-00.html")
    _write(tmp_path, "debrief_2026-06-15_11-00-00.html")
    _write(tmp_path, "debrief_2026-06-14_09-00-00.md")
    archive = FilesystemDebriefArchive(tmp_path, FakePreferencesStore())

    assert archive.count() == 3
    assert _names(archive.list_page(0, 10)) == [
        "debrief_2026-06-15_11-00-00.html",
        "debrief_2026-06-15_10-00-00.html",
        "debrief_2026-06-14_09-00-00.md",
    ]


def test_ignores_non_debrief_and_temporary_files(tmp_path: Path) -> None:
    """Only files with the debrief prefix and a valid export suffix are listed."""
    _write(tmp_path, "debrief_2026-06-15_10-00-00.html")
    _write(tmp_path, "debrief_2026-06-15_10-00-00.html.tmp")
    _write(tmp_path, "notes.txt")
    _write(tmp_path, "report.html")
    archive = FilesystemDebriefArchive(tmp_path, FakePreferencesStore())

    assert _names(archive.list_page(0, 10)) == ["debrief_2026-06-15_10-00-00.html"]


def test_paginates_with_offset_and_limit(tmp_path: Path) -> None:
    """A page is the requested slice of the newest-first list."""
    for hour in range(5):
        _write(tmp_path, f"debrief_2026-06-15_1{hour}-00-00.html")
    archive = FilesystemDebriefArchive(tmp_path, FakePreferencesStore())

    assert _names(archive.list_page(0, 2)) == [
        "debrief_2026-06-15_14-00-00.html",
        "debrief_2026-06-15_13-00-00.html",
    ]
    assert _names(archive.list_page(2, 2)) == [
        "debrief_2026-06-15_12-00-00.html",
        "debrief_2026-06-15_11-00-00.html",
    ]
    assert _names(archive.list_page(4, 2)) == ["debrief_2026-06-15_10-00-00.html"]


def test_configured_output_dir_overrides_default(tmp_path: Path) -> None:
    """When preferences name an output directory, the archive reads from it."""
    default_dir = tmp_path / "default"
    chosen_dir = tmp_path / "chosen"
    _write(default_dir, "debrief_2026-06-15_10-00-00.html")
    _write(chosen_dir, "debrief_2026-06-16_10-00-00.html")
    preferences = FakePreferencesStore(Preferences(output_dir=str(chosen_dir)))
    archive = FilesystemDebriefArchive(default_dir, preferences)

    assert _names(archive.list_page(0, 10)) == ["debrief_2026-06-16_10-00-00.html"]


def test_missing_directory_returns_empty(tmp_path: Path) -> None:
    """A directory that does not exist yields no debriefs and does not raise."""
    archive = FilesystemDebriefArchive(tmp_path / "nope", FakePreferencesStore())

    assert archive.count() == 0
    assert archive.list_page(0, 10) == ()
