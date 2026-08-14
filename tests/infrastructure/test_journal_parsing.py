"""Tests for the malformed-input paths in journal parsing and tailing.

The happy paths are exercised by the end-to-end and file-source suites, which
read real sample journals. What those cannot reach is the defensive half: a
truncated line, a rotated file, a line that is valid JSON but not an object.
Those branches exist because a journal is written by another process while it
is being read, so they are the ones that fire on a real machine and never in a
fixture.
"""

from __future__ import annotations

from o7debrief.infrastructure.journal.event_mapper import map_record
from o7debrief.infrastructure.journal.line_parser import parse_line, parse_lines
from o7debrief.infrastructure.journal.tail_reader import (
    EMPTY_OFFSET,
    read_new_bytes,
)

_TIMESTAMP = "2026-08-14T12:00:00Z"
_EVENT = "LoadGame"
# A first line long enough that a truncated read leaves a clear remainder.
_FIRST_LINE = b'{"timestamp": "2026-08-14T12:00:00Z", "event": "LoadGame"}\n'
_SECOND_LINE = b'{"timestamp": "2026-08-14T12:01:00Z", "event": "Shutdown"}\n'


def test_a_blank_line_is_not_an_event() -> None:
    """Journals carry blank lines; they are skipped rather than reported."""
    assert parse_line("   \n") is None


def test_malformed_json_is_skipped() -> None:
    """A half-written line is the normal consequence of reading a live file."""
    assert parse_line('{"event": "LoadGa') is None


def test_valid_json_that_is_not_an_object_is_skipped() -> None:
    """A bare array or number parses cleanly and is still not an event."""
    assert parse_line("[1, 2, 3]") is None
    assert parse_line("42") is None


def test_a_json_object_is_returned() -> None:
    assert parse_line('{"event": "LoadGame"}') == {"event": _EVENT}


def test_parsing_many_lines_drops_only_the_unusable_ones() -> None:
    parsed = parse_lines(('{"event": "LoadGame"}', "", "not json", "[]"))

    assert parsed == ({"event": _EVENT},)


def test_a_record_without_an_event_type_is_unmappable() -> None:
    assert map_record({"timestamp": _TIMESTAMP}) is None
    assert map_record({"event": "", "timestamp": _TIMESTAMP}) is None
    assert map_record({"event": 7, "timestamp": _TIMESTAMP}) is None


def test_a_record_without_a_usable_timestamp_is_unmappable() -> None:
    assert map_record({"event": _EVENT}) is None
    assert map_record({"event": _EVENT, "timestamp": ""}) is None
    assert map_record({"event": _EVENT, "timestamp": 7}) is None


def test_a_timestamp_the_domain_cannot_parse_is_unmappable() -> None:
    """The domain owns the format; a record it rejects is dropped, not guessed."""
    assert map_record({"event": _EVENT, "timestamp": "last Tuesday"}) is None


def test_a_complete_record_maps_to_an_event() -> None:
    mapped = map_record({"event": _EVENT, "timestamp": _TIMESTAMP})

    assert mapped is not None
    assert mapped.event_type == _EVENT


def test_a_missing_file_yields_no_lines_and_holds_the_offset(tmp_path) -> None:
    """A journal can vanish between the poll and the read."""
    result = read_new_bytes(tmp_path / "absent.log", EMPTY_OFFSET, b"")

    assert result.complete_lines == ()
    assert result.new_offset == EMPTY_OFFSET


def test_only_new_bytes_are_read_from_the_recorded_offset(tmp_path) -> None:
    journal = tmp_path / "Journal.log"
    journal.write_bytes(_FIRST_LINE)
    first = read_new_bytes(journal, EMPTY_OFFSET, b"")

    journal.write_bytes(_FIRST_LINE + _SECOND_LINE)
    second = read_new_bytes(journal, first.new_offset, first.new_partial)

    assert len(first.complete_lines) == 1
    assert len(second.complete_lines) == 1
    assert "Shutdown" in second.complete_lines[0]


def test_a_truncated_file_is_read_again_from_the_beginning(tmp_path) -> None:
    """A file smaller than the recorded offset was rotated, so start over."""
    journal = tmp_path / "Journal.log"
    journal.write_bytes(_FIRST_LINE)

    stale_offset = len(_FIRST_LINE) * 10
    result = read_new_bytes(journal, stale_offset, b"partial")

    assert len(result.complete_lines) == 1
    assert result.new_offset == len(_FIRST_LINE)


def test_a_stat_that_fails_is_treated_as_a_rotation(tmp_path, monkeypatch) -> None:
    """An unreadable size cannot be trusted, so the read starts over safely."""
    journal = tmp_path / "Journal.log"
    journal.write_bytes(_FIRST_LINE)

    def _refuse(self):
        raise OSError("stat refused")

    monkeypatch.setattr("pathlib.Path.stat", _refuse)

    result = read_new_bytes(journal, len(_FIRST_LINE), b"carried")

    assert result.new_offset == len(_FIRST_LINE)
    assert result.new_partial == b""
