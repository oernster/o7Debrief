"""Scale tests: a journal of over ten thousand rows, written as a bundle.

These are the assertions the paging exists to make true, so they are measured
against a real rendered bundle rather than argued from the design. A history
run must produce a set of pages that each stay under the configured size, that
between them hold every row exactly once, and that a following short session
barely disturbs.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.services.debrief_export_service import (
    BundleWriting,
    DebriefExportService,
)
from o7debrief.infrastructure import (
    FilesystemBundleSink,
    FilesystemSink,
    HtmlBundleExporter,
    HtmlDebriefExporter,
    MarkdownDebriefExporter,
)
from tests.application.history_builders import spread, view_of

# Comfortably beyond the ten thousand rows the acceptance criteria name.
_LARGE = 10500
# What one more evening of play adds.
_ONE_SESSION = 20
_DIRECTORY = "debrief_history"


class _FixedClock:
    """A clock returning one fixed instant, so filenames stay predictable."""

    def now_utc(self) -> str:
        return "2026-08-13T10:00:00+00:00"


def _shipped_options() -> HistoryOptions:
    """Return the history limits exactly as the shipped taxonomy states them.

    The point of these tests is that the settings o7 Debrief actually ships
    hold up at scale, so they are read from the file rather than restated.
    """
    path = Path(__file__).resolve().parents[2] / "config" / "debrief_taxonomy.toml"
    table = tomllib.loads(path.read_text(encoding="utf-8"))["history"]
    return HistoryOptions(**table)


def _service(directory: Path, options: HistoryOptions) -> DebriefExportService:
    return DebriefExportService(
        (HtmlDebriefExporter(), MarkdownDebriefExporter()),
        FilesystemSink(str(directory)),
        _FixedClock(),
        BundleWriting(
            (HtmlBundleExporter(),), FilesystemBundleSink(str(directory)), options
        ),
    )


def _run(directory: Path, moments, options: HistoryOptions, fmt: str = "html"):
    view = view_of(moments)
    return _service(directory, options).export(
        view, RenderRequest((fmt,), str(directory), history=True)
    )


def test_a_large_history_opens_from_the_filesystem_as_a_bundle(tmp_path) -> None:
    """No server and no network: an index beside its pages and one sheet."""
    options = _shipped_options()
    result = _run(tmp_path, spread(_LARGE), options)

    entry = Path(result.paths[0])
    assert entry.name == "index.html"
    assert entry.is_file()
    assert (entry.parent / "style.css").is_file()
    assert (entry.parent / "pages").is_dir()


def test_every_page_stays_under_the_configured_size_budget(tmp_path) -> None:
    """The budget is a claim about the shipped settings, so it is measured."""
    options = _shipped_options()
    _run(tmp_path, spread(_LARGE), options)

    root = tmp_path / _DIRECTORY
    oversized = [
        path.name
        for path in root.rglob("*.html")
        if path.stat().st_size > options.page_bytes_target
    ]
    assert not oversized, f"pages over the budget: {oversized}"


def test_the_whole_bundle_is_a_fraction_of_one_document(tmp_path) -> None:
    """Paging must divide the report, not multiply it by repeating the sheet."""
    options = _shipped_options()
    _run(tmp_path, spread(_LARGE), options)

    root = tmp_path / _DIRECTORY
    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    sheet = (root / "style.css").stat().st_size
    pages = len(list(root.rglob("*.html")))
    # One shared sheet rather than one per page is the saving the bundle makes,
    # so what it saved must be larger than what a page costs to carry.
    assert sheet * (pages - 1) < total
    assert total < options.page_bytes_target * (pages + 1)


def test_every_row_appears_exactly_once_across_the_written_pages(tmp_path) -> None:
    """Navigation reaching every page is worth nothing if a page lost a row."""
    options = _shipped_options()
    _run(tmp_path, spread(_LARGE), options)

    root = tmp_path / _DIRECTORY
    rows = 0
    for path in root.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        panel = html.split('id="panel-all"', maxsplit=1)[1].split("</ul>", maxsplit=1)[
            0
        ]
        rows += len(re.findall(r'<span class="t">', panel))
    assert rows == _LARGE


def test_a_following_short_session_rewrites_the_index_and_little_else(
    tmp_path,
) -> None:
    """The acceptance criterion for regenerating on every quit, measured."""
    options = _shipped_options()
    _run(tmp_path, spread(_LARGE), options)
    root = tmp_path / _DIRECTORY
    stamps = {
        path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()
    }

    _run(tmp_path, spread(_LARGE + _ONE_SESSION), options)

    moved = [
        path.name for path, stamp in stamps.items() if path.stat().st_mtime_ns != stamp
    ]
    # The sheet carries the global counts, so it moves; the index carries the
    # newest page. Every older page is left exactly as it was.
    assert sorted(moved) == ["index.html", "style.css"]


def test_single_file_mode_produces_one_capped_document_that_says_so(
    tmp_path,
) -> None:
    """The flag for handing somebody one file, with an honest footer."""
    capped_options = _replace_single_file(_shipped_options())
    single = _run(tmp_path, spread(_LARGE), capped_options)

    document = Path(single.paths[0])
    assert document.suffix == ".html"
    html = document.read_text(encoding="utf-8")
    omitted = _LARGE - capped_options.single_file_max_entries
    assert f"{omitted} older entries" in html
    assert len(re.findall(r'<span class="t">', html)) < _LARGE


def test_markdown_history_is_capped_because_it_has_no_bundle_form(tmp_path) -> None:
    """Markdown cannot be a bundle, so it is bounded the other way instead."""
    options = _shipped_options()
    result = _run(tmp_path, spread(_LARGE), options, fmt="md")

    document = Path(result.paths[0])
    assert document.suffix == ".md"
    text = document.read_text(encoding="utf-8")
    assert f"{_LARGE - options.single_file_max_entries} older entries" in text


def _as_dict(options: HistoryOptions) -> dict:
    """Return the options as a plain dict, for building a variant."""
    return {
        field: getattr(options, field) for field in HistoryOptions.__dataclass_fields__
    }


def _replace_single_file(options: HistoryOptions) -> HistoryOptions:
    """Return the same options with one-document mode turned on."""
    return HistoryOptions(**{**_as_dict(options), "single_file": True})
