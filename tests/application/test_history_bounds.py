"""Tests for the three things that bound a history report.

Paging divides the report; these bound it. The daily rollup folds the older
tail into one row per day per category, the single-file cap cuts the log and
says how much it cut, and the page limit is the stricter of a row count and a
size budget.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.services.history_capping import capped
from o7debrief.application.services.history_rollup import rolled_up, rollup_count
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from tests.application.history_builders import (
    history_options,
    moment_at,
    spread,
    view_of,
)

# Labels the rollup wording is built from, mirroring the taxonomy titles.
_LABELS = {"travel": "Travel", "combat": "Combat"}


# ------------------------------------------------------------------- rollup


def test_rollup_is_off_by_default_and_returns_the_log_untouched() -> None:
    """It discards detail, so nothing happens unless it is asked for."""
    view = view_of(spread(200))

    assert rolled_up(view.timeline, history_options(), _LABELS) is view.timeline


def test_rollup_on_an_empty_log_is_still_empty() -> None:
    """No rows in means no rows out, and no arithmetic on a missing newest row."""
    options = history_options(rollup_enabled=True)

    assert rolled_up((), options, _LABELS) == ()


def test_rollup_leaves_the_recent_window_in_full_detail() -> None:
    """Everything inside the threshold is untouched, row for row."""
    view = view_of(spread(60, "2026-08-01T00:00:00Z", minutes=60))
    options = history_options(rollup_enabled=True, rollup_after_days=90)

    assert rolled_up(view.timeline, options, _LABELS) == view.timeline


def test_rollup_folds_an_old_day_into_one_row_per_category() -> None:
    """An old day costs one row per category rather than every event."""
    moments = (
        moment_at("2026-01-05T09:00:00Z", ActivityDomain.TRAVEL),
        moment_at("2026-01-05T10:00:00Z", ActivityDomain.TRAVEL),
        moment_at("2026-01-05T11:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
        moment_at("2026-08-10T09:00:00Z", ActivityDomain.TRAVEL),
    )
    view = view_of(moments)
    options = history_options(rollup_enabled=True, rollup_after_days=30)

    folded = rolled_up(view.timeline, options, _LABELS)

    assert len(folded) == 3
    assert folded[0].text == view.timeline[0].text
    # Categories keep the order they first appear in on that day, and the rows
    # read newest first, so the 11:00 combat row is met before the travel ones.
    summaries = [entry.text for entry in folded[1:]]
    assert summaries == ["1 Combat entries", "2 Travel entries"]
    # A summary stands for a whole day, so it invents no time and no mode.
    assert all(entry.time_display == "" for entry in folded[1:])
    assert all(entry.day_display == "Mon 05 Jan 2026" for entry in folded[1:])


def test_rollup_falls_back_to_the_category_key_when_no_label_is_known() -> None:
    """An unlabelled category still reads as something rather than as blank."""
    view = view_of(
        (
            moment_at("2026-01-05T09:00:00Z", ActivityDomain.TRAVEL),
            moment_at("2026-08-10T09:00:00Z", ActivityDomain.TRAVEL),
        )
    )
    options = history_options(rollup_enabled=True, rollup_after_days=30)

    folded = rolled_up(view.timeline, options, {})

    assert folded[-1].text == "1 travel entries"


def test_rollup_counts_what_it_would_fold_for_an_honest_notice() -> None:
    """The report can say how much detail the rollup cost."""
    view = view_of(
        (
            moment_at("2026-01-05T09:00:00Z"),
            moment_at("2026-01-06T09:00:00Z"),
            moment_at("2026-08-10T09:00:00Z"),
        )
    )
    options = history_options(rollup_enabled=True, rollup_after_days=30)

    assert rollup_count(view.timeline, options) == 2
    assert rollup_count(view.timeline, history_options()) == 0
    assert rollup_count((), options) == 0


# ------------------------------------------------------------- single file


def test_a_log_within_the_cap_is_returned_exactly_as_it_came() -> None:
    """No notice appears on a report that omitted nothing."""
    view = view_of(spread(50))

    assert capped(view, history_options(single_file_max_entries=100)) is view


def test_capping_keeps_the_newest_rows_and_says_what_it_dropped() -> None:
    """A truncated report that does not admit it is worse than a paged one."""
    view = view_of(spread(200))

    cut = capped(view, history_options(single_file_max_entries=50))

    assert len(cut.timeline) == 50
    assert cut.timeline == view.timeline[:50]
    assert "150 older entries" in cut.footer.truncation_notice
    assert "most recent 50" in cut.footer.truncation_notice


def test_capping_trims_each_tab_to_the_rows_that_survived() -> None:
    """A tab must not show rows the truncated log no longer holds."""
    view = view_of(spread(200))

    cut = capped(view, history_options(single_file_max_entries=20))

    shown = {(entry.day_key, entry.time_display, entry.text) for entry in cut.timeline}
    for category in cut.timeline_categories:
        for entry in category.entries:
            assert (entry.day_key, entry.time_display, entry.text) in shown
    assert sum(len(c.entries) for c in cut.timeline_categories) == 20


def test_capping_keeps_each_tab_count_at_the_whole_history_figure() -> None:
    """A tab renumbering itself down would quietly restate the journal."""
    view = view_of(spread(200))

    cut = capped(view, history_options(single_file_max_entries=20))

    before = {category.key: category.count for category in view.timeline_categories}
    for category in cut.timeline_categories:
        assert category.count == before[category.key]
        assert len(category.entries) < category.count


def test_capping_drops_a_tab_with_nothing_left_in_it() -> None:
    """A tab whose rows were all cut is not rendered as an empty panel."""
    view = view_of(
        (
            moment_at("2026-08-10T09:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
            moment_at("2026-08-10T10:00:00Z", ActivityDomain.TRAVEL),
        )
    )

    cut = capped(view, history_options(single_file_max_entries=1))

    assert [category.key for category in cut.timeline_categories] == ["travel"]


# ------------------------------------------------------------- page limits


def test_the_page_limit_is_the_stricter_of_the_row_count_and_the_budget() -> None:
    """Whichever bound bites first is the one that applies."""
    by_rows = history_options(entries_per_page=100, page_bytes_target=512000)
    by_bytes = history_options(entries_per_page=100000, page_bytes_target=40000)

    assert by_rows.max_entries_per_page() == 100
    assert by_bytes.max_entries_per_page() == 100


def test_a_page_always_holds_at_least_one_row() -> None:
    """A budget too small for a single row must not produce an empty page.

    A page holding nothing would never consume a row, and the paging loop
    would not advance.
    """
    options = history_options(page_bytes_target=1, bytes_per_entry_estimate=400)

    assert options.max_entries_per_page() == 1
