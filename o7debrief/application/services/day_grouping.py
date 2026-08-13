"""Mark where day separators fall in a set of timeline rows.

A separator belongs to the panel or page it is drawn in, never to the moment.
The same moment appears in the full log, in its own category panel and on one
page of a paged history, and those three sets cover different spans of days: a
category holding one afternoon's rows must stay undated even when the full log
runs for months. So the marking is a function of a row set, applied once per
rendered set, and a set covering a single day is marked not at all.

Rows arrive ordered newest first and are never reordered here, so the newest
day heads the result and each separator sits directly above the rows it covers.

This module belongs to the application layer and imports only the view DTO.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import replace

from o7debrief.application.dto.debrief_view import TimelineEntry

__all__ = ["with_day_separators"]

# How many distinct calendar days a set of rows must cover before separators
# are worth drawing. At or below this every row is the same day and repeating
# it above them would be noise.
_SINGLE_DAY = 1


def with_day_separators(
    entries: tuple[TimelineEntry, ...],
) -> tuple[TimelineEntry, ...]:
    """Return the rows with the first row of each day carrying its heading.

    Every row's existing separator is recomputed rather than trusted, because
    a row sliced out of one set into another (a page taken from the full log)
    inherits a heading that may no longer be the first of its day here.
    """
    if len({entry.day_display for entry in entries}) <= _SINGLE_DAY:
        return tuple(
            entry if not entry.day_separator else replace(entry, day_separator="")
            for entry in entries
        )
    marked: list[TimelineEntry] = []
    previous = ""
    for entry in entries:
        heading = "" if entry.day_display == previous else entry.day_display
        marked.append(
            entry
            if entry.day_separator == heading
            else replace(entry, day_separator=heading)
        )
        previous = entry.day_display
    return tuple(marked)
