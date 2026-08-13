"""LogPage DTO: one page of a paged history log, with its tabs.

A paged history splits the session log into pages the reader navigates
between. Each page carries its own rows, already marked with the day headings
that fall inside it, and one tab per category that exists anywhere in the
history, not merely on this page. A tab therefore always states the whole
history's count, so ``Combat (2 of 13)`` reads as two here out of thirteen
altogether, and a category with nothing on this page says so rather than
opening an empty panel.

``key`` doubles as the page's identity and its file stem, and is derived from
the calendar period the page covers rather than from its position in the set.
Position-numbered pages renumber every time a page is added at the newest end,
which would rewrite the whole bundle on the first session of a new month; a
period key never changes once that period is over.

This module belongs to the application layer and imports only the view DTO.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from o7debrief.application.dto.debrief_view import TimelineEntry

__all__ = ["LogPage", "PageCategory"]


@dataclass(frozen=True, slots=True)
class PageCategory:
    """One category tab on a page: its rows here, and its count everywhere."""

    key: str
    label: str
    icon: str
    page_count: int
    total_count: int
    entries: tuple[TimelineEntry, ...]

    def as_dict(self) -> dict:
        """Return the tab as a plain dict with its entries flattened."""
        return {
            "key": self.key,
            "label": self.label,
            "icon": self.icon,
            "page_count": self.page_count,
            "total_count": self.total_count,
            "entries": [entry.as_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class LogPage:
    """One page of the log: its rows, its tabs and its identity."""

    key: str
    title: str
    entries: tuple[TimelineEntry, ...]
    categories: tuple[PageCategory, ...]
    total_entries: int

    def as_dict(self) -> dict:
        """Return the page as a plain dict with its parts flattened."""
        return {
            "key": self.key,
            "title": self.title,
            "total_entries": self.total_entries,
            "entries": [entry.as_dict() for entry in self.entries],
            "categories": [category.as_dict() for category in self.categories],
        }
