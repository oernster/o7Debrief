"""Tests for RecentsPager: page slicing, position and clamping over an archive.

The pager owns no Qt; these are plain unit tests over a fake archive. They check
the page slice at each position, the page count and the clamping of previous and
next at the ends, plus the empty and null-archive cases.
"""

from __future__ import annotations

from o7debrief.ui.tray.recents_pager import NullArchive, RecentsPager

from tests.ui.fakes import FakeArchive

_PAGE_SIZE = 10


def _paths(count: int) -> tuple[str, ...]:
    """Return a tuple of sortable sample debrief paths."""
    return tuple(f"C:/out/debrief_{index:02d}.html" for index in range(count))


def test_empty_archive_has_one_page() -> None:
    pager = RecentsPager(FakeArchive(), _PAGE_SIZE)

    assert pager.page() == ()
    assert pager.page_index() == 0
    assert pager.page_count() == 1
    assert pager.has_more() is False


def test_single_page_fits_in_one() -> None:
    paths = _paths(7)
    pager = RecentsPager(FakeArchive(paths), _PAGE_SIZE)

    assert pager.page() == paths
    assert pager.page_count() == 1
    assert pager.has_more() is False


def test_next_and_prev_walk_the_pages() -> None:
    paths = _paths(25)
    pager = RecentsPager(FakeArchive(paths), _PAGE_SIZE)

    assert pager.page_count() == 3
    assert pager.has_more() is True
    assert pager.page() == paths[0:10]

    pager.to_next()
    assert pager.page() == paths[10:20]
    assert pager.page_index() == 1

    pager.to_next()
    assert pager.page() == paths[20:25]
    assert pager.page_index() == 2

    pager.to_next()  # clamped at the last page
    assert pager.page_index() == 2

    pager.to_prev()
    pager.to_prev()
    pager.to_prev()  # clamped at the first page
    assert pager.page_index() == 0


def test_first_page_ignores_the_current_position() -> None:
    paths = _paths(25)
    pager = RecentsPager(FakeArchive(paths), _PAGE_SIZE)

    pager.to_next()

    assert pager.first_page() == paths[0:10]
    assert pager.page_index() == 1  # unchanged by first_page


def test_reset_returns_to_the_first_page() -> None:
    pager = RecentsPager(FakeArchive(_paths(25)), _PAGE_SIZE)

    pager.to_next()
    pager.reset()

    assert pager.page_index() == 0


def test_null_archive_lists_nothing() -> None:
    archive = NullArchive()

    assert archive.count() == 0
    assert archive.list_page(0, _PAGE_SIZE) == ()
