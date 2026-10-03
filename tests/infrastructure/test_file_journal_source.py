"""Tests for FileJournalSource: session isolation, ordering and tail reads."""

from __future__ import annotations

import json
import os
from pathlib import Path

from o7debrief.infrastructure.journal import file_journal_source as fjs
from o7debrief.infrastructure.journal.file_journal_source import FileJournalSource

# Two play sessions in one file: an older one to exclude, the latest to keep.
_OLDER_SESSION = [
    {"timestamp": "2026-06-14T10:00:00Z", "event": "LoadGame", "FID": "F1"},
    {"timestamp": "2026-06-14T10:05:00Z", "event": "FSDJump", "StarSystem": "Lave"},
    {"timestamp": "2026-06-14T10:10:00Z", "event": "Shutdown"},
]
_LATEST_SESSION = [
    {"timestamp": "2026-06-15T20:00:00Z", "event": "LoadGame", "FID": "F1"},
    {"timestamp": "2026-06-15T20:05:00Z", "event": "FSDJump", "StarSystem": "Sol"},
    {"timestamp": "2026-06-15T20:30:00Z", "event": "Shutdown"},
]
_CONTINUED = {"timestamp": "2026-06-15T20:06:00Z", "event": "Continued", "Part": 2}


def test_read_latest_session_returns_only_the_most_recent(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _OLDER_SESSION + _LATEST_SESSION)

    events = FileJournalSource(journal_dir).read_latest_session()

    assert [event.event_type for event in events] == [
        "LoadGame",
        "FSDJump",
        "Shutdown",
    ]
    systems = [e.get("StarSystem") for e in events if e.event_type == "FSDJump"]
    assert systems == ["Sol"]


def test_read_all_returns_every_event_in_time_order(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _OLDER_SESSION + _LATEST_SESSION)

    events = FileJournalSource(journal_dir).read_all()

    assert len(events) == len(_OLDER_SESSION) + len(_LATEST_SESSION)
    epochs = [event.event_time.epoch_s for event in events]
    assert epochs == sorted(epochs)


def test_read_new_tails_only_appended_events(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    path = write_journal_lines(journal_dir, _LATEST_SESSION[:1])
    source = FileJournalSource(journal_dir)

    first, offset = source.read_new(0)
    assert [event.event_type for event in first] == ["LoadGame"]

    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(_LATEST_SESSION[1]) + "\n")

    second, new_offset = source.read_new(offset)
    assert [event.event_type for event in second] == ["FSDJump"]
    assert new_offset > offset


def test_read_new_holds_a_partial_line_until_completed(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    path = write_journal_lines(journal_dir, _LATEST_SESSION[:1])
    source = FileJournalSource(journal_dir)
    _, offset = source.read_new(0)

    # Append a line with no trailing newline: incomplete, so nothing maps yet.
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(_LATEST_SESSION[1]))
    held, held_offset = source.read_new(offset)
    assert held == ()

    # Completing the line with a newline yields the event on the next read.
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n")
    completed, _ = source.read_new(held_offset)
    assert [event.event_type for event in completed] == ["FSDJump"]


_FIRST_RUN_FILE = "Journal.2026-06-15T200000.01.log"
_NEXT_RUN_FILE = "Journal.2026-06-15T210000.01.log"
_CONTINUATION_FILE = "Journal.2026-06-15T200000.02.log"


def _line(event: dict) -> str:
    return json.dumps(event) + "\n"


def test_read_new_starts_a_new_latest_file_from_its_first_byte(
    journal_dir_factory, write_journal_lines
) -> None:
    # A short menu-only run is tailed; the next run's file is already larger
    # than the old offset at the next poll. Its opening lines must be read.
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, [_LATEST_SESSION[2]], name=_FIRST_RUN_FILE)
    source = FileJournalSource(journal_dir)
    _, offset = source.read_new(0)
    write_journal_lines(journal_dir, _LATEST_SESSION * 2, name=_NEXT_RUN_FILE)

    events, _ = source.read_new(offset)

    assert [event.event_type for event in events] == [
        "LoadGame",
        "FSDJump",
        "Shutdown",
    ] * 2


def test_read_new_finishes_the_old_file_before_its_continuation(
    journal_dir_factory, write_journal_lines
) -> None:
    # The game rotates mid-run: lines land at the end of the old file, then a
    # continuation file opens. Nothing written to either may be lost.
    journal_dir = journal_dir_factory()
    old = write_journal_lines(journal_dir, _LATEST_SESSION[:1], name=_FIRST_RUN_FILE)
    source = FileJournalSource(journal_dir)
    _, offset = source.read_new(0)
    with open(old, "a", encoding="utf-8") as handle:
        handle.write(_line(_LATEST_SESSION[1]))
        # A last line with no newline is still the end of a finished file.
        handle.write(json.dumps(_CONTINUED))
    write_journal_lines(journal_dir, _LATEST_SESSION[2:], name=_CONTINUATION_FILE)

    events, _ = source.read_new(offset)

    assert [event.event_type for event in events] == [
        "FSDJump",
        "Continued",
        "Shutdown",
    ]


def test_lines_that_cannot_be_read_are_counted_per_read(journal_dir_factory) -> None:
    # A torn line and a line with no timestamp are each a line not read; a
    # blank line held nothing. The count belongs to one read, so a second
    # read starts again rather than adding to it.
    journal_dir = journal_dir_factory()
    torn = '{"timestamp": "2026-06-15T20:01:00Z", "event": "LoadG\n'
    no_time = json.dumps({"event": "FSDJump"}) + "\n"
    (journal_dir / _FIRST_RUN_FILE).write_text(
        _line(_LATEST_SESSION[0]) + torn + "\n" + no_time + _line(_LATEST_SESSION[2]),
        encoding="utf-8",
    )
    source = FileJournalSource(journal_dir)
    assert source.unreadable_lines() == 0

    events = source.read_latest_session()
    assert [event.event_type for event in events] == ["LoadGame", "Shutdown"]
    assert source.unreadable_lines() == 2

    assert len(list(source.iter_event_batches())) == 1
    assert source.unreadable_lines() == 2


def test_read_new_without_a_journal_file_is_empty(journal_dir_factory) -> None:
    journal_dir = journal_dir_factory()

    events, offset = FileJournalSource(journal_dir).read_new(0)

    assert events == ()
    assert offset == 0


def test_read_latest_session_only_reads_back_to_the_session_boundary(
    journal_dir_factory, write_journal_lines, monkeypatch
) -> None:
    journal_dir = journal_dir_factory()
    # Three separate per-launch files, each a complete run ending in Shutdown.
    older = [
        {"timestamp": "2026-06-13T10:00:00Z", "event": "LoadGame", "FID": "F1"},
        {"timestamp": "2026-06-13T10:10:00Z", "event": "Shutdown"},
    ]
    middle = [
        {"timestamp": "2026-06-14T10:00:00Z", "event": "LoadGame", "FID": "F1"},
        {"timestamp": "2026-06-14T10:10:00Z", "event": "Shutdown"},
    ]
    latest = [
        {"timestamp": "2026-06-15T20:00:00Z", "event": "LoadGame", "FID": "F1"},
        {"timestamp": "2026-06-15T20:05:00Z", "event": "FSDJump", "StarSystem": "Sol"},
        {"timestamp": "2026-06-15T20:30:00Z", "event": "Shutdown"},
    ]
    older_path = write_journal_lines(
        journal_dir, older, name="Journal.2026-06-13.01.log"
    )
    middle_path = write_journal_lines(
        journal_dir, middle, name="Journal.2026-06-14.01.log"
    )
    latest_path = write_journal_lines(
        journal_dir, latest, name="Journal.2026-06-15.01.log"
    )
    # Pin modification times so "newest" is unambiguous whatever order the files
    # were written in: older < middle < latest.
    base = 1_000_000_000
    step = 100
    os.utime(older_path, (base, base))
    os.utime(middle_path, (base + step, base + step))
    os.utime(latest_path, (base + step + step, base + step + step))

    real_read_lines = fjs.read_lines
    parsed: list[Path] = []

    def spy(path):
        parsed.append(Path(path))
        return real_read_lines(path)

    monkeypatch.setattr(fjs, "read_lines", spy)

    events = FileJournalSource(journal_dir).read_latest_session()

    assert [e.event_type for e in events] == ["LoadGame", "FSDJump", "Shutdown"]
    systems = [e.get("StarSystem") for e in events if e.event_type == "FSDJump"]
    assert systems == ["Sol"]
    # The backward scan walked back only to the previous Shutdown: the latest
    # and middle files were parsed, the oldest was not, so a debrief never
    # parses the whole journal history.
    assert latest_path in parsed
    assert middle_path in parsed
    assert older_path not in parsed


def test_iter_event_batches_yields_one_ordered_batch_per_file(
    journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    older = [
        {"timestamp": "2026-06-14T10:00:00Z", "event": "LoadGame", "FID": "F1"},
        {"timestamp": "2026-06-14T10:05:00Z", "event": "FSDJump", "StarSystem": "Lave"},
    ]
    newer = [
        {"timestamp": "2026-06-15T20:00:00Z", "event": "LoadGame", "FID": "F1"},
        {"timestamp": "2026-06-15T20:30:00Z", "event": "Shutdown"},
    ]
    older_path = write_journal_lines(
        journal_dir, older, name="Journal.2026-06-14.01.log"
    )
    newer_path = write_journal_lines(
        journal_dir, newer, name="Journal.2026-06-15.01.log"
    )
    base = 1_000_000_000
    step = 100
    os.utime(older_path, (base, base))
    os.utime(newer_path, (base + step, base + step))

    batches = list(FileJournalSource(journal_dir).iter_event_batches())

    # One batch per file, oldest file first.
    assert len(batches) == 2
    assert [e.event_type for e in batches[0]] == ["LoadGame", "FSDJump"]
    assert [e.event_type for e in batches[1]] == ["LoadGame", "Shutdown"]
    # Each batch is ordered by event-time within its file.
    for batch in batches:
        epochs = [e.event_time.epoch_s for e in batch]
        assert epochs == sorted(epochs)
