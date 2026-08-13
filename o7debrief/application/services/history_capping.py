"""Cap a history log for the one-document mode and say what was dropped.

Single-file mode exists so a whole history can still be handed to somebody as
one file. That only works if the file is bounded, so the log is cut to the
newest rows and the footer states plainly how many rows are not in it. A
truncated report that does not admit it is worse than a paged one: a reader
counts what is there and believes it is everything.

Only the log is cut. The headline, the activity cards and the ranks are
summaries of the whole history and stay whole, so the figures at the top of
the report never disagree with the journal because of a display limit.

This module belongs to the application layer and imports application symbols
only. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import replace

from o7debrief.application.dto.debrief_view import DebriefView, TimelineCategory
from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.services.day_grouping import with_day_separators

__all__ = ["capped"]

# Counting base for how many of a category's rows survive the cut.
_NONE_YET = 0


def _kept_per_category(entries) -> dict[str, int]:
    """Return how many surviving rows each category holds."""
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.category_key] = counts.get(entry.category_key, _NONE_YET) + 1
    return counts


def _trimmed_categories(
    categories: tuple[TimelineCategory, ...], counts: dict[str, int]
) -> tuple[TimelineCategory, ...]:
    """Return each category cut to the rows that survived the flat cut.

    Both lists hold the same rows in the same newest-first order, so taking a
    category's first ``n`` rows yields exactly the ones the flat cut kept,
    without having to match rows to each other one by one.

    ``count`` deliberately keeps the whole history's figure. A tab that
    renumbered itself to the truncated total would quietly restate the
    journal, which is the failure this whole mode is trying to avoid.
    """
    trimmed = []
    for category in categories:
        keep = counts.get(category.key, _NONE_YET)
        if keep == _NONE_YET:
            continue
        trimmed.append(
            replace(category, entries=with_day_separators(category.entries[:keep]))
        )
    return tuple(trimmed)


def capped(view: DebriefView, options: HistoryOptions) -> DebriefView:
    """Return the view with its log cut to the configured maximum.

    A log already within the limit is returned exactly as it came, so nothing
    is rebuilt and no notice appears on a report that omits nothing.
    """
    limit = options.single_file_max_entries
    omitted = len(view.timeline) - limit
    if omitted <= _NONE_YET:
        return view
    entries = with_day_separators(view.timeline[:limit])
    counts = _kept_per_category(entries)
    return replace(
        view,
        timeline=entries,
        timeline_categories=_trimmed_categories(view.timeline_categories, counts),
        footer=replace(
            view.footer,
            truncation_notice=options.truncation_notice_format.format(
                omitted=omitted, shown=limit
            ),
        ),
    )
