"""Split a whole-history log into deterministic, stable pages.

The rules that matter, in the order they matter:

  - **Deterministic.** The same log always splits at the same places, from the
    log alone. Nothing here reads a clock, a filesystem or a rendered size.
  - **Stable at the older end.** Pages are keyed by the calendar month they
    cover, and a month is split from its oldest row forward. Adding rows to
    the newest month therefore changes only that month's newest part; every
    older page is byte-identical to what it was, which is what lets the sink
    leave it untouched. Position-numbered pages would renumber on the first
    session of a new month and rewrite the entire bundle.
  - **Counts are global.** A tab states the whole history's count for its
    category and how many of those are on this page, so a reader never has to
    guess whether thirteen means thirteen here or thirteen altogether.

Rows arrive newest first and stay newest first, so page one is the newest.

This module belongs to the application layer and imports application symbols
only. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import DebriefView, TimelineEntry
from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.dto.log_page import LogPage, PageCategory
from o7debrief.application.services.day_grouping import with_day_separators
from o7debrief.application.services.history_rollup import rolled_up

__all__ = ["paginate"]

# Separator between a month key and the part number of a month too large for
# one page, giving keys like "2026-08" and "2026-08-2".
_PART_SEPARATOR = "-"
# The part number the first (oldest) part of a month carries implicitly, so
# that an unsplit month keeps the bare month key it has always had.
_FIRST_PART = 1
# Suffix appended to a page title when a month occupies more than one page.
_PART_TITLE = " ({part})"
# An empty log still produces no pages at all rather than one blank page.
_NOTHING = 0


def _months(entries: tuple[TimelineEntry, ...]) -> list[tuple[str, list]]:
    """Return the rows grouped into consecutive runs of one calendar month.

    The rows are already ordered, so a month's rows are contiguous and a plain
    single pass finds every group without sorting or bucketing.
    """
    groups: list[tuple[str, list]] = []
    for entry in entries:
        if not groups or groups[-1][0] != entry.month_key:
            groups.append((entry.month_key, []))
        groups[-1][1].append(entry)
    return groups


def _parts(rows: list, per_page: int) -> list[list]:
    """Split one month's rows into pages, counting from its oldest row.

    Counting from the oldest is what makes the split stable. The rows are
    newest first, so the oldest sit at the end; chunking from there leaves
    every completed chunk fixed and grows only the newest one, which is the
    single page a fresh session can disturb.
    """
    chunks: list[list] = []
    remaining = list(rows)
    while remaining:
        chunks.append(remaining[-per_page:])
        remaining = remaining[:-per_page]
    # Chunks were collected oldest first; the report reads newest first.
    chunks.reverse()
    return chunks


def _page_key(month: str, part: int) -> str:
    """Return the page key: the oldest part keeps the bare month name.

    Parts are filled from the oldest, so part one holds the same rows whether
    the month later needs two pages or ten. Letting it keep the bare month key
    means the file a month starts life as is the file it stays, and a month
    that outgrows one page adds files rather than renaming the one it had.
    """
    if part == _FIRST_PART:
        return month
    return f"{month}{_PART_SEPARATOR}{part}"


def _page_title(month_title: str, part: int, of_parts: int) -> str:
    """Return the page heading, naming the part only when there is one."""
    if of_parts == _FIRST_PART:
        return month_title
    return month_title + _PART_TITLE.format(part=part)


def _totals(entries: tuple[TimelineEntry, ...]) -> dict[str, int]:
    """Return how many rows each category holds across the whole log."""
    totals: dict[str, int] = {}
    for entry in entries:
        totals[entry.category_key] = totals.get(entry.category_key, _NOTHING) + 1
    return totals


def _categories(page_rows: tuple[TimelineEntry, ...], view, totals) -> tuple:
    """Build a tab for every category in the history, in the report's order.

    Every category the history holds gets a tab on every page, including one
    with nothing on this page: a tab that states zero of thirteen tells the
    reader where the other thirteen are, where a silently missing tab does not.
    """
    here: dict[str, list[TimelineEntry]] = {}
    for entry in page_rows:
        here.setdefault(entry.category_key, []).append(entry)
    tabs = []
    for category in view.timeline_categories:
        rows = tuple(here.get(category.key, ()))
        tabs.append(
            PageCategory(
                key=category.key,
                label=category.label,
                icon=category.icon,
                page_count=len(rows),
                total_count=totals.get(category.key, _NOTHING),
                entries=with_day_separators(rows),
            )
        )
    return tuple(tabs)


def paginate(
    view: DebriefView, options: HistoryOptions, month_titles: dict[str, str]
) -> tuple[LogPage, ...]:
    """Split the view's log into pages, newest first.

    ``month_titles`` maps each month key to its display heading, formatted by
    the presenter, so nothing here formats a date of its own.
    """
    labels = {category.key: category.label for category in view.timeline_categories}
    entries = rolled_up(view.timeline, options, labels)
    if not entries:
        return ()
    totals = _totals(entries)
    per_page = options.max_entries_per_page()
    pages: list[LogPage] = []
    for month, rows in _months(entries):
        chunks = _parts(rows, per_page)
        of_parts = len(chunks)
        for index, chunk in enumerate(chunks):
            # Parts are numbered from the oldest, so the number a page carries
            # never changes once the part below it is full.
            part = of_parts - index
            page_rows = with_day_separators(tuple(chunk))
            pages.append(
                LogPage(
                    key=_page_key(month, part),
                    title=_page_title(month_titles.get(month, month), part, of_parts),
                    entries=page_rows,
                    categories=_categories(page_rows, view, totals),
                    total_entries=len(entries),
                )
            )
    return tuple(pages)
