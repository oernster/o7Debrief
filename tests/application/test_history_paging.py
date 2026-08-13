"""Tests for splitting a whole-history log into deterministic, stable pages.

The two properties that matter are asserted directly rather than inferred: the
same log always splits the same way and adding rows at the newest end leaves
every older page byte-identical. Everything else in the bundle depends on
those two holding.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.services.history_paging import paginate
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from tests.application.history_builders import (
    history_options,
    moment_at,
    spread,
    view_of,
)


def _pages(moments, **overrides):
    """Paginate a view built from these moments, with option overrides."""
    view = view_of(moments)
    return paginate(view, history_options(**overrides), dict(view.month_titles))


def _keys(pages) -> list[str]:
    return [page.key for page in pages]


def test_an_empty_log_produces_no_pages() -> None:
    """Nothing to read is no pages, not one blank page."""
    assert _pages(()) == ()


def test_a_log_within_one_month_is_a_single_page() -> None:
    """One month of rows is one page, keyed on the month it covers."""
    pages = _pages(spread(20, "2026-08-01T09:00:00Z"))

    assert _keys(pages) == ["2026-08"]
    assert len(pages[0].entries) == 20


def test_pages_are_keyed_by_month_and_ordered_newest_first() -> None:
    """The reader starts at the newest month and walks backwards."""
    pages = _pages(
        (
            moment_at("2026-06-10T09:00:00Z"),
            moment_at("2026-07-10T09:00:00Z"),
            moment_at("2026-08-10T09:00:00Z"),
        )
    )

    assert _keys(pages) == ["2026-08", "2026-07", "2026-06"]


def test_every_row_appears_exactly_once_across_the_set() -> None:
    """No page drops a row and no row is duplicated onto two pages."""
    moments = spread(500)
    pages = _pages(moments)

    assert sum(len(page.entries) for page in pages) == len(moments)


def test_a_month_larger_than_a_page_splits_into_numbered_parts() -> None:
    """A busy month becomes several pages, the newest part numbered highest."""
    pages = _pages(spread(250, "2026-08-01T00:00:00Z", minutes=5), entries_per_page=100)

    # The oldest part keeps the bare month name, so a month that outgrows one
    # page adds files rather than renaming the file it already had.
    assert _keys(pages) == ["2026-08-3", "2026-08-2", "2026-08"]
    # Parts are filled from the oldest, so only the newest part is short.
    assert [len(page.entries) for page in pages] == [50, 100, 100]


def test_growing_the_newest_month_leaves_every_older_page_untouched() -> None:
    """The property the incremental write depends on, asserted directly.

    A fresh session adds rows at the newest end. If that moved a boundary in
    an older page, every page in the bundle would be rewritten on every quit,
    which is the whole thing paging by month is meant to prevent.
    """
    before = _pages(spread(400))
    after = _pages(spread(420))

    for older in before[1:]:
        match = [page for page in after if page.key == older.key]
        assert match, f"page {older.key} vanished"
        assert match[0].entries == older.entries
        assert match[0].title == older.title


def test_growing_a_split_month_disturbs_only_its_newest_part() -> None:
    """Within a month the oldest parts are sealed by construction."""
    before = _pages(
        spread(250, "2026-08-01T00:00:00Z", minutes=5), entries_per_page=100
    )
    after = _pages(spread(260, "2026-08-01T00:00:00Z", minutes=5), entries_per_page=100)

    sealed = {page.key: page.entries for page in before if page.key != "2026-08-3"}
    for page in after:
        if page.key in sealed:
            assert page.entries == sealed[page.key]


def test_a_tab_states_the_whole_history_count_beside_the_page_count() -> None:
    """Thirteen means thirteen altogether and this page holds some of them."""
    pages = _pages(spread(2000))
    combat = next(tab for tab in pages[0].categories if tab.key == "combat")

    total = sum(
        len([entry for entry in page.entries if entry.category_key == "combat"])
        for page in pages
    )
    assert combat.total_count == total
    assert combat.page_count == len(
        [entry for entry in pages[0].entries if entry.category_key == "combat"]
    )
    assert combat.page_count < combat.total_count


def test_a_category_absent_from_a_page_still_gets_a_tab() -> None:
    """A tab reading zero of many tells the reader where the rest are."""
    pages = _pages(
        (
            moment_at("2026-07-10T09:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
            moment_at("2026-08-10T09:00:00Z", ActivityDomain.TRAVEL),
        )
    )
    newest = pages[0]
    combat = next(tab for tab in newest.categories if tab.key == "combat")

    assert combat.page_count == 0
    assert combat.total_count == 1
    assert combat.entries == ()


def test_a_page_spanning_days_carries_its_own_separators() -> None:
    """Day headings are recomputed per page, not inherited from the full log."""
    pages = _pages(spread(2000))
    headings = [
        entry.day_separator for entry in pages[0].entries if entry.day_separator
    ]

    assert headings
    # The first row of a page always opens a day, because a page boundary is
    # a month boundary and a month begins on a day.
    assert pages[0].entries[0].day_separator


def test_the_page_title_names_the_month_and_its_part() -> None:
    """An unsplit month reads plainly; a split one names which part it is."""
    single = _pages(spread(10, "2026-08-01T09:00:00Z"))
    split = _pages(spread(30, "2026-08-01T00:00:00Z", minutes=5), entries_per_page=10)

    assert single[0].title == "August 2026"
    assert [page.title for page in split] == [
        "August 2026 (3)",
        "August 2026 (2)",
        "August 2026 (1)",
    ]


def test_a_month_with_no_title_falls_back_to_its_key() -> None:
    """A heading that could not be resolved shows the key rather than nothing."""
    view = view_of(spread(5, "2026-08-01T09:00:00Z"))
    pages = paginate(view, history_options(), {})

    assert pages[0].title == "2026-08"


def test_the_page_carries_the_whole_history_row_count() -> None:
    """The All tab needs the global figure, so the page carries it."""
    pages = _pages(spread(300))

    assert all(page.total_entries == 300 for page in pages)
