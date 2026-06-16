"""Tests for FilesystemSink: atomic writes, naming and directory creation."""

from __future__ import annotations

from pathlib import Path

from o7debrief.infrastructure.sink.filesystem_sink import FilesystemSink


def test_write_creates_file_with_name_and_content(tmp_path: Path) -> None:
    sink = FilesystemSink(tmp_path / "out")
    written = sink.write("debrief_2026", b"<html></html>", "html")

    path = Path(written)
    assert path.name == "debrief_2026.html"
    assert path.read_bytes() == b"<html></html>"


def test_write_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    sink = FilesystemSink(tmp_path)
    sink.write("debrief", b"body", "md")

    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_write_creates_missing_output_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "debriefs"
    sink = FilesystemSink(target)

    written = sink.write("debrief", b"x", "md")

    assert Path(written).exists()
    assert Path(written).parent == target


def test_write_overwrites_an_existing_file(tmp_path: Path) -> None:
    sink = FilesystemSink(tmp_path)
    sink.write("debrief", b"first", "md")

    written = sink.write("debrief", b"second", "md")

    assert Path(written).read_bytes() == b"second"


def test_write_honours_an_explicit_output_dir(tmp_path: Path) -> None:
    sink = FilesystemSink(tmp_path / "default")
    chosen = tmp_path / "chosen"

    written = sink.write("debrief", b"x", "md", str(chosen))

    assert Path(written).parent == chosen
    # The default directory is left untouched when an output dir is given.
    assert (tmp_path / "default").exists() is False
