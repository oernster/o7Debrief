"""RecentsPager: paging state over a DebriefArchive for the recents views.

The tray submenu always shows the most recent page; the home dialog pages
through the whole archive with previous and next. This holds the current page
offset and the page size and answers the archive in page-sized slices, so the ui
never realises more than one page of entries at a time. It owns no Qt and no
I/O; the archive behind it does the directory read.

This module belongs to the ui layer and imports the application layer (for the
port type, under TYPE_CHECKING) and the standard library only. British spelling
is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type-only import, no runtime dependency
    from o7debrief.application.ports.debrief_archive import DebriefArchive

__all__ = ["RecentsPager", "NullArchive"]

# The offset of the first (most recent) page.
_FIRST_OFFSET = 0
# The smallest page count reported, so the ui always has at least one page even
# when the archive is empty.
_MIN_PAGES = 1


class NullArchive:
    """A DebriefArchive with nothing in it, used when none is injected."""

    def count(self) -> int:
        """Return zero; there is nothing to list."""
        return 0

    def list_page(self, offset: int, limit: int) -> tuple[str, ...]:
        """Return an empty page regardless of the request."""
        return ()


class RecentsPager:
    """Tracks the current page offset over a DebriefArchive."""

    def __init__(self, archive: DebriefArchive, page_size: int) -> None:
        self._archive = archive
        self._page_size = page_size
        self._offset = _FIRST_OFFSET

    def reset(self) -> None:
        """Return to the first, most recent page."""
        self._offset = _FIRST_OFFSET

    def first_page(self) -> tuple[str, ...]:
        """Return the most recent page without moving the current position."""
        return self._archive.list_page(_FIRST_OFFSET, self._page_size)

    def page(self) -> tuple[str, ...]:
        """Return the page at the current position."""
        return self._archive.list_page(self._offset, self._page_size)

    def page_index(self) -> int:
        """Return the zero-based index of the current page."""
        return self._offset // self._page_size

    def page_count(self) -> int:
        """Return how many pages the archive spans, never fewer than one."""
        total = self._archive.count()
        if total == 0:
            return _MIN_PAGES
        return (total + self._page_size - 1) // self._page_size

    def has_more(self) -> bool:
        """Return whether the archive holds more than a single page."""
        return self._archive.count() > self._page_size

    def to_next(self) -> None:
        """Advance one page, stopping at the last."""
        if self.page_index() < self.page_count() - 1:
            self._offset += self._page_size

    def to_prev(self) -> None:
        """Step back one page, stopping at the first."""
        if self._offset >= self._page_size:
            self._offset -= self._page_size
