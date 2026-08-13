"""HtmlBundleExporter: render a whole-history debrief as a small static bundle.

This adapter implements the application ``DebriefBundleExporter`` port for the
``html`` format. It emits one ``style.css``, an ``index.html`` carrying the
report proper plus the newest page of the log and one file per older page
under ``pages/``. Every page links the shared sheet, so the palette is stored
once rather than once per page and navigation is ordinary links, so the
bundle opens from the filesystem with no server and no scripts.

Pages arrive already split, keyed and ordered newest first: how a log divides
is the application's decision and this adapter only chooses markup.

A page file is named after its key, which is the calendar period it covers,
not its position. A position-numbered set renumbers whenever a page is added
at the newest end, which would rewrite every file in the bundle on the first
session of a new month.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from jinja2 import Environment

from o7debrief.application.dto.bundle import BundleFile, DebriefBundle
from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.dto.log_page import LogPage
from o7debrief.infrastructure.render.html_bundle_templates import (
    INDEX_TEMPLATE,
    PAGE_TEMPLATE,
)
from o7debrief.infrastructure.render.html_styles import STYLESHEET
from o7debrief.infrastructure.render.icons import emoji_for

__all__ = ["BUNDLE_DIRECTORY_NAME", "HtmlBundleExporter"]

# File-type suffix (no dot) this exporter produces.
_EXTENSION = "html"
_ENCODING = "utf-8"
_EMOJI_FILTER = "emoji"
_TAB_KEYS = "tab_keys"
# Context names under which the stylesheet receives the whole history's
# counts. They live in the sheet rather than in each page's markup so that a
# growing total does not rewrite every page; see html_styles for the reasoning.
_TAB_TOTALS = "tab_totals"
_ALL_TOTAL = "all_total"
_PAGE_TOTAL = "page_total"

# The one directory a history bundle is written to, rewritten in place on each
# run. A timestamped directory per run would mean every page is written every
# time, which is exactly what incremental regeneration exists to avoid.
BUNDLE_DIRECTORY_NAME = "debrief_history"

# The fixed file names inside a bundle.
_INDEX_FILE = "index.html"
_STYLE_FILE = "style.css"
_PAGES_DIR = "pages"

# Where the index sits in the page order and the reader-facing number of the
# first page. The newest page is the index, so it is page one.
_NEWEST = 0
_FIRST_POSITION = 1


def _page_path(page: LogPage) -> str:
    """Return a page's path inside the bundle, relative to its root."""
    return f"{_PAGES_DIR}/{page.key}.{_EXTENSION}"


def _href(from_index: bool, target: int, pages: tuple[LogPage, ...]) -> str:
    """Return the link to page ``target``, relative to the page linking it.

    The index sits at the bundle root and every other page a directory below,
    so the same destination is written differently depending on where the
    reader currently is.
    """
    if target == _NEWEST:
        return _INDEX_FILE if from_index else f"../{_INDEX_FILE}"
    path = _page_path(pages[target])
    return path if from_index else path.split("/", maxsplit=1)[1]


def _style_context(context: dict, pages: tuple[LogPage, ...]) -> dict:
    """Return what the stylesheet needs: the tab keys and the global counts."""
    categories = pages[_NEWEST].categories if pages else ()
    return {
        _TAB_KEYS: [category["key"] for category in context["timeline_categories"]],
        _TAB_TOTALS: [
            {"key": category.key, "total": category.total_count}
            for category in categories
        ],
        _ALL_TOTAL: pages[_NEWEST].total_entries if pages else _NEWEST,
        _PAGE_TOTAL: len(pages),
    }


def _nav(position: int, pages: tuple[LogPage, ...]) -> dict:
    """Return the navigation for the page at ``position`` in the set."""
    from_index = position == _NEWEST
    newer = position - _FIRST_POSITION
    older = position + _FIRST_POSITION
    return {
        "newer": "" if from_index else _href(from_index, newer, pages),
        "older": ("" if older >= len(pages) else _href(from_index, older, pages)),
        "index": "" if from_index else _href(from_index, _NEWEST, pages),
        "position": position + _FIRST_POSITION,
    }


class HtmlBundleExporter:
    """Renders a history debrief as a static bundle (port: DebriefBundleExporter)."""

    extension = _EXTENSION

    def __init__(self) -> None:
        environment = Environment(autoescape=True)
        environment.filters[_EMOJI_FILTER] = emoji_for
        self._index = environment.from_string(INDEX_TEMPLATE)
        self._page = environment.from_string(PAGE_TEMPLATE)
        self._style = environment.from_string(STYLESHEET)

    def render_bundle(
        self, view: DebriefView, pages: tuple[LogPage, ...]
    ) -> DebriefBundle:
        """Render the view and its pages into every file the bundle holds."""
        context = view.to_context()
        files = [
            BundleFile(
                relative_path=_STYLE_FILE,
                content=self._style.render(**_style_context(context, pages)).encode(
                    _ENCODING
                ),
            )
        ]
        for position, page in enumerate(pages):
            template = self._index if position == _NEWEST else self._page
            body = {**context, "page": page.as_dict(), "nav": _nav(position, pages)}
            files.append(
                BundleFile(
                    relative_path=(
                        _INDEX_FILE if position == _NEWEST else _page_path(page)
                    ),
                    content=template.render(**body).encode(_ENCODING),
                )
            )
        if not pages:
            # A history with no rows still needs a readable index rather than a
            # directory holding a stylesheet and nothing to open.
            files.append(
                BundleFile(
                    relative_path=_INDEX_FILE,
                    content=self._index.render(
                        **{**context, "page": _EMPTY_PAGE, "nav": _EMPTY_NAV}
                    ).encode(_ENCODING),
                )
            )
        return DebriefBundle(
            directory_name=BUNDLE_DIRECTORY_NAME,
            entry_point=_INDEX_FILE,
            files=tuple(files),
        )


# What the index shows when the journal yielded no log rows at all.
_EMPTY_PAGE = {
    "key": "",
    "title": "No log entries",
    "total_entries": 0,
    "entries": [],
    "categories": [],
}
_EMPTY_NAV = {
    "newer": "",
    "older": "",
    "index": "",
    "position": _FIRST_POSITION,
}
