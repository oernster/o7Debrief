"""Which journal files are read and in what order.

The game names every file for the moment its run started, so the name is the
order. A modification time is not: a journal restored from a backup or copied
from another machine carries a new one; a file ordered by it would make a
years-old session read as the latest. A copy of a file beside its original is
not a second run either, so only names the game itself writes are read.
"""

from __future__ import annotations

import os

from o7debrief.infrastructure.journal.file_journal_source import FileJournalSource
from o7debrief.infrastructure.journal.paths import (
    get_journal_files,
    get_latest_journal_file,
)

# Two names in the game's current format and one in the format it wrote before
# 2021 (two-digit year, no separators).
_CURRENT = "Journal.2026-01-02T100000.01.log"
_CURRENT_PART_TWO = "Journal.2026-01-02T100000.02.log"
_LEGACY = "Journal.200101100000.01.log"
# A copy an operating system makes beside the original.
_COPY = "Journal.2026-01-02T100000.01 - Copy.log"

# Modification times pinned so the newest by mtime is the oldest by name.
_OLD_MTIME = 1_000_000_000
_NEW_MTIME = 2_000_000_000

_RUN_2020 = [
    {"timestamp": "2020-01-01T10:00:00Z", "event": "LoadGame", "FID": "F1"},
    {"timestamp": "2020-01-01T10:05:00Z", "event": "Shutdown"},
    {"timestamp": "2020-01-01T11:00:00Z", "event": "LoadGame", "FID": "F1"},
    {"timestamp": "2020-01-01T11:10:00Z", "event": "Shutdown"},
]
_RUN_2026 = [
    {"timestamp": "2026-01-02T10:00:00Z", "event": "LoadGame", "FID": "F1"},
    {"timestamp": "2026-01-02T10:05:00Z", "event": "MissionCompleted"},
    {"timestamp": "2026-01-02T10:30:00Z", "event": "Shutdown"},
]


def _pin(path, mtime: int) -> None:
    os.utime(path, (mtime, mtime))


def test_a_restored_old_journal_never_becomes_the_latest(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    _pin(write_journal_lines(journal_dir, _RUN_2026, name=_CURRENT), _OLD_MTIME)
    _pin(write_journal_lines(journal_dir, _RUN_2020, name=_LEGACY), _NEW_MTIME)

    events = FileJournalSource(journal_dir).read_latest_session()

    assert events[0].event_time.iso_utc == "2026-01-02T10:00:00Z"
    assert get_latest_journal_file(journal_dir) == journal_dir / _CURRENT


def test_parts_of_one_run_follow_their_part_number(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    _pin(write_journal_lines(journal_dir, [], name=_CURRENT_PART_TWO), _OLD_MTIME)
    _pin(write_journal_lines(journal_dir, [], name=_CURRENT), _NEW_MTIME)

    assert [path.name for path in get_journal_files(journal_dir)] == [
        _CURRENT,
        _CURRENT_PART_TWO,
    ]


def test_a_copy_of_a_journal_is_not_read_twice(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _RUN_2026, name=_CURRENT)
    write_journal_lines(journal_dir, _RUN_2026, name=_COPY)

    events = FileJournalSource(journal_dir).read_all()

    missions = [e for e in events if e.event_type == "MissionCompleted"]
    assert len(missions) == 1


def test_a_name_with_an_impossible_date_is_not_a_game_name(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, [], name=_CURRENT)
    write_journal_lines(journal_dir, [], name="Journal.2026-13-40T100000.01.log")

    assert [path.name for path in get_journal_files(journal_dir)] == [_CURRENT]


def test_a_folder_with_no_game_names_is_still_read_by_mtime(
    journal_dir_factory, write_journal_lines
) -> None:
    # A folder of files the game did not name is still read rather than
    # reported empty; absence of a stamp is no reason to show nothing.
    journal_dir = journal_dir_factory()
    _pin(write_journal_lines(journal_dir, [], name="Journal.b.01.log"), _OLD_MTIME)
    _pin(write_journal_lines(journal_dir, [], name="Journal.a.01.log"), _NEW_MTIME)

    assert [path.name for path in get_journal_files(journal_dir)] == [
        "Journal.b.01.log",
        "Journal.a.01.log",
    ]
