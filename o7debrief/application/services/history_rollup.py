"""Collapse the older tail of a history log into one row per day per category.

Paging divides a growing report; it does not bound it. A journal that gains a
thousand rows a month gains a page a month for ever. Rolling the older tail up
is the only option here that bounds the total: however long the history runs,
an old month costs one row per day per category rather than every event.

It is deliberately opt-in and off by default, because it discards detail. What
it discards is stated on the page rather than quietly dropped.

The age threshold is measured back from the newest row in the log, never from
the wall clock, so the same journal always rolls up to the same rows. A
threshold anchored to "now" would re-cut an unchanged history differently
tomorrow and rewrite pages that had not changed.

This module belongs to the application layer and imports the standard library
and application symbols only. British spelling is used in comments. No em
dashes appear anywhere.
"""

from __future__ import annotations

from datetime import date, timedelta

from o7debrief.application.dto.debrief_view import TimelineEntry
from o7debrief.application.dto.history_options import HistoryOptions

__all__ = ["rolled_up", "rollup_count"]

# A summary row stands for a whole day, so it carries no time of day and no
# control mode: both would be an invention rather than a reading.
_NO_TIME = ""
_NO_MODE = ""
# Counting base for the rows folded into one summary.
_NONE_YET = 0


def _cutoff(newest_day: str, days: int) -> str:
    """Return the oldest ISO day that stays in full detail."""
    return (date.fromisoformat(newest_day) - timedelta(days=days)).isoformat()


def _summary(rows: list[TimelineEntry], text_format: str, label: str) -> TimelineEntry:
    """Return one row standing for a day's worth of one category's rows."""
    first = rows[0]
    return TimelineEntry(
        time_display=_NO_TIME,
        mode=_NO_MODE,
        mode_label=_NO_MODE,
        mode_tag=_NO_MODE,
        icon=first.icon,
        text=text_format.format(count=len(rows), label=label),
        system=None,
        day_display=first.day_display,
        day_key=first.day_key,
        month_key=first.month_key,
        category_key=first.category_key,
    )


def rolled_up(
    entries: tuple[TimelineEntry, ...],
    options: HistoryOptions,
    category_labels: dict[str, str],
) -> tuple[TimelineEntry, ...]:
    """Return the log with rows older than the threshold folded into summaries.

    Rows arrive newest first and leave newest first. Recent rows pass through
    untouched; older ones are grouped by day and then by category, keeping the
    order in which each category first appears on that day, so the summary
    reads in the same sequence the detail did.
    """
    if not options.rollup_enabled or not entries:
        return entries
    cutoff = _cutoff(entries[0].day_key, options.rollup_after_days)
    kept = [entry for entry in entries if entry.day_key >= cutoff]
    older = [entry for entry in entries if entry.day_key < cutoff]
    if not older:
        return entries
    groups: dict[tuple[str, str], list[TimelineEntry]] = {}
    order: list[tuple[str, str]] = []
    for entry in older:
        key = (entry.day_key, entry.category_key)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    summaries = [
        _summary(
            groups[key],
            options.rollup_text_format,
            category_labels.get(key[1], key[1]),
        )
        for key in order
    ]
    return tuple(kept) + tuple(summaries)


def rollup_count(entries: tuple[TimelineEntry, ...], options: HistoryOptions) -> int:
    """Return how many rows a rollup would fold away, for an honest notice."""
    if not options.rollup_enabled or not entries:
        return _NONE_YET
    cutoff = _cutoff(entries[0].day_key, options.rollup_after_days)
    return len([entry for entry in entries if entry.day_key < cutoff])
