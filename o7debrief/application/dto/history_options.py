"""HistoryOptions DTO: how a whole-history debrief is bounded and split.

A history report grows on every session, so it needs limits that a user can
change without editing code. All of them arrive here from the taxonomy
``[history]`` table.

Two of the limits are worth explaining because they trade against each other.
``entries_per_page`` is the enforced cap and is deterministic: the same log
always splits at the same place, which is what lets an older page be left
untouched on a regeneration. ``page_bytes_target`` is a size budget expressed
in bytes, which is what a reader actually cares about; it is converted into an
entry count through a measured per-entry estimate rather than by rendering and
measuring, because a cap that depended on the rendered size would move every
page boundary each time a page's contents changed. The stricter of the two
wins.

``rollup_after_days`` is measured back from the newest entry in the log, never
from the wall clock. A report must render the same way twice, and a threshold
anchored to "now" would silently re-cut the same journal differently tomorrow.

This module belongs to the application layer and imports the standard library
only. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HistoryOptions"]


@dataclass(frozen=True, slots=True)
class HistoryOptions:
    """The limits governing a whole-history debrief."""

    entries_per_page: int
    page_bytes_target: int
    bytes_per_entry_estimate: int
    single_file: bool
    single_file_max_entries: int
    truncation_notice_format: str
    rollup_enabled: bool
    rollup_after_days: int
    rollup_text_format: str

    def max_entries_per_page(self) -> int:
        """Return the effective per-page cap: the stricter of the two limits.

        At least one entry always fits, whatever the budget says, so a
        pathologically small byte target cannot produce a page holding nothing
        and a paging loop that never advances.
        """
        from_bytes = self.page_bytes_target // self.bytes_per_entry_estimate
        return max(_AT_LEAST_ONE, min(self.entries_per_page, from_bytes))


# A page must be able to hold a row, whatever the configured budget.
_AT_LEAST_ONE = 1
