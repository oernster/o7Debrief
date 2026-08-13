"""Tests for the shared day-separator marking.

The function is used three times over: by the presenter for the full log, for
each category panel, and by the pager for each page and each page's tabs. What
matters is that it is a function of the row set handed to it and of nothing
else, so the same rows can be marked differently in two different panels
without either knowing about the other.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import TimelineEntry
from o7debrief.application.services.day_grouping import with_day_separators


def _row(day: str, separator: str = "") -> TimelineEntry:
    """Build a bare row on a given day, optionally pre-marked."""
    return TimelineEntry(
        time_display="12:00:00",
        mode="ship",
        mode_label="Ship",
        mode_tag="S",
        icon="rocket",
        text="Jumped.",
        system=None,
        day_display=day,
        day_key=day,
        month_key=day[:7],
        day_separator=separator,
    )


def _marks(entries) -> list[str]:
    return [entry.day_separator for entry in entries]


def test_no_rows_is_no_marking() -> None:
    """An empty panel produces nothing to draw, and no arithmetic on nothing."""
    assert with_day_separators(()) == ()


def test_rows_all_on_one_day_are_left_unmarked() -> None:
    """One day of rows repeats nothing above itself."""
    rows = (_row("2026-08-13"), _row("2026-08-13"))

    assert _marks(with_day_separators(rows)) == ["", ""]


def test_the_first_row_of_each_day_carries_the_heading() -> None:
    """Each day is announced once, above the rows that belong to it."""
    rows = (_row("2026-08-14"), _row("2026-08-13"), _row("2026-08-13"))

    assert _marks(with_day_separators(rows)) == ["2026-08-14", "2026-08-13", ""]


def test_a_row_sliced_into_a_single_day_set_loses_its_inherited_heading() -> None:
    """A page taken out of a longer log must not keep the log's marking.

    The same row appears in the full log, in its category panel and on a page.
    A heading is right in one of those and wrong in another, so it is always
    recomputed rather than carried across.
    """
    rows = (_row("2026-08-13", "2026-08-13"), _row("2026-08-13"))

    assert _marks(with_day_separators(rows)) == ["", ""]


def test_a_row_sliced_into_a_multi_day_set_gains_the_heading_it_needs() -> None:
    """A row that was mid-day in the log opens the day on its own page."""
    rows = (_row("2026-08-14"), _row("2026-08-13"), _row("2026-08-12"))

    assert _marks(with_day_separators(rows[1:])) == ["2026-08-13", "2026-08-12"]


def test_an_already_correct_marking_returns_the_same_rows() -> None:
    """Nothing is rebuilt when nothing needs to change."""
    rows = (_row("2026-08-14", "2026-08-14"), _row("2026-08-13", "2026-08-13"))

    assert with_day_separators(rows) == rows
