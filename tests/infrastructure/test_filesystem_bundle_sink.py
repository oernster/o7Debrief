"""Tests for FilesystemBundleSink: write what moved, leave the rest alone.

The history report is regenerated on every quit, so the saving asserted here
is the whole point of the bundle: an unchanged page is not opened for writing
and its modification time does not move.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.application.dto.bundle import BundleFile, DebriefBundle
from o7debrief.infrastructure.sink.filesystem_bundle_sink import FilesystemBundleSink

_DIRECTORY = "debrief_history"


def _bundle(*pairs: tuple[str, str]) -> DebriefBundle:
    """Build a bundle from (relative path, text) pairs."""
    return DebriefBundle(
        directory_name=_DIRECTORY,
        entry_point="index.html",
        files=tuple(
            BundleFile(relative_path=path, content=text.encode("utf-8"))
            for path, text in pairs
        ),
    )


def _full(text: str = "one") -> DebriefBundle:
    return _bundle(
        ("style.css", "body{}"),
        ("index.html", text),
        ("pages/2026-07.html", "july"),
        ("pages/2026-06.html", "june"),
    )


def test_a_first_write_creates_every_file_and_returns_the_entry(tmp_path) -> None:
    """A bundle written into nothing produces the whole set, ready to open."""
    result = FilesystemBundleSink(tmp_path).write_bundle(_full())

    root = tmp_path / _DIRECTORY
    assert Path(result.entry_path) == root / "index.html"
    assert (root / "pages" / "2026-07.html").read_text(encoding="utf-8") == "july"
    assert len(result.written) == 4
    assert result.skipped == ()


def test_an_unchanged_file_is_skipped_and_not_touched(tmp_path) -> None:
    """The saving this whole design exists for, measured rather than assumed."""
    sink = FilesystemBundleSink(tmp_path)
    sink.write_bundle(_full())
    stamps = {
        path: path.stat().st_mtime_ns
        for path in (tmp_path / _DIRECTORY).rglob("*")
        if path.is_file()
    }

    result = sink.write_bundle(_full(text="two"))

    assert [Path(item).name for item in result.written] == ["index.html"]
    assert len(result.skipped) == 3
    for path, stamp in stamps.items():
        if path.name != "index.html":
            assert path.stat().st_mtime_ns == stamp, f"{path.name} was rewritten"


def test_writing_to_an_explicit_directory_overrides_the_default(tmp_path) -> None:
    """The user's chosen output location wins over the configured one."""
    elsewhere = tmp_path / "elsewhere"
    result = FilesystemBundleSink(tmp_path / "default").write_bundle(
        _full(), str(elsewhere)
    )

    assert Path(result.entry_path) == elsewhere / _DIRECTORY / "index.html"


def test_a_page_the_bundle_no_longer_holds_is_removed(tmp_path) -> None:
    """A change of paging must not leave orphans navigation cannot reach."""
    sink = FilesystemBundleSink(tmp_path)
    sink.write_bundle(_full())

    result = sink.write_bundle(
        _bundle(
            ("style.css", "body{}"),
            ("index.html", "one"),
            ("pages/2026-07.html", "july"),
        )
    )

    assert [Path(item).name for item in result.removed] == ["2026-06.html"]
    assert not (tmp_path / _DIRECTORY / "pages" / "2026-06.html").exists()


def test_pruning_leaves_files_of_another_type_alone(tmp_path) -> None:
    """Only the bundle's own generated pages are ever removed."""
    sink = FilesystemBundleSink(tmp_path)
    sink.write_bundle(_full())
    stray = tmp_path / _DIRECTORY / "pages" / "notes.txt"
    stray.write_text("mine", encoding="utf-8")
    subdir = tmp_path / _DIRECTORY / "pages" / "sub"
    subdir.mkdir()

    sink.write_bundle(_full())

    assert stray.read_text(encoding="utf-8") == "mine"
    assert subdir.is_dir()


def test_a_bundle_with_no_pages_directory_prunes_nothing(tmp_path) -> None:
    """A single-page history has no pages directory to walk."""
    result = FilesystemBundleSink(tmp_path).write_bundle(
        _bundle(("style.css", "body{}"), ("index.html", "one"))
    )

    assert result.removed == ()


def test_no_temporary_file_survives_a_write(tmp_path) -> None:
    """Writing goes through a temporary file, and never leaves one behind."""
    FilesystemBundleSink(tmp_path).write_bundle(_full())

    assert not list((tmp_path / _DIRECTORY).rglob("*.tmp"))
