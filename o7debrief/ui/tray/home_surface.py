"""HomeSurface: the Recent debriefs submenu and the home dialog.

Extracted from the tray controller so that controller holds the menu shell
and its actions while this class owns the two views onto the debrief
archive: the Recent debriefs submenu (always showing the newest page) and
the modeless home dialog (which can page through the full history). Both
read through one shared ``RecentsPager``, so the pager's state is the only
paging truth.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QIcon

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from collections.abc import Callable

    from PySide6.QtWidgets import QMenu

    from o7debrief.ui.tray.recents_pager import RecentsPager
    from o7debrief.ui.windows.home import HomeDialog

__all__ = ["HomeSurface"]

# Caption shown in the Recent debriefs submenu when the directory is empty.
_NO_RECENT_TEXT = "No debriefs yet"
# Final submenu entry shown when more debriefs exist than fit on one page; it
# opens the home dialog, where the full history can be paged through.
_MORE_TEXT = "More debriefs..."


class HomeSurface:
    """Drives the Recent debriefs submenu and the modeless home dialog."""

    def __init__(
        self,
        pager: RecentsPager,
        recent_menu: QMenu,
        opener: Callable[[str], bool],
        home_factory: Callable[..., HomeDialog],
        icon: QIcon | None,
        status_provider: Callable[[], str],
        on_debrief_last: Callable[[], None],
        on_debrief_history: Callable[[], None],
        on_settings: Callable[[], None],
        on_about: Callable[[], None],
    ) -> None:
        self._pager = pager
        self._recent_menu = recent_menu
        self._opener = opener
        self._home_factory = home_factory
        self._icon = icon
        self._status_provider = status_provider
        self._on_debrief_last = on_debrief_last
        self._on_debrief_history = on_debrief_history
        self._on_settings = on_settings
        self._on_about = on_about
        self._home: HomeDialog | None = None

    # ------------------------------------------------------------- recents menu

    def rebuild_recent_menu(self) -> None:
        """Repopulate the Recent debriefs submenu from the most recent page.

        The submenu always shows the newest page; when more debriefs exist
        than fit on a page a final entry opens the home dialog, where the
        full history can be paged through.
        """
        self._recent_menu.clear()
        page = self._pager.first_page()
        if not page:
            empty = QAction(_NO_RECENT_TEXT, self._recent_menu)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return
        for path in page:
            self._add_recent_entry(path)
        if self._pager.has_more():
            self._add_more_entry()

    def _add_recent_entry(self, path: str) -> None:
        """Add a single Recent debriefs entry that reopens its file."""
        action = QAction(path, self._recent_menu)
        action.triggered.connect(lambda _checked=False, p=path: self._opener(p))
        self._recent_menu.addAction(action)

    def _add_more_entry(self) -> None:
        """Add a final entry that opens the home dialog to page the history."""
        action = QAction(_MORE_TEXT, self._recent_menu)
        action.triggered.connect(lambda _checked=False: self.open_home())
        self._recent_menu.addAction(action)

    # -------------------------------------------------------------- home dialog

    def open_home(self) -> None:
        """Show the home dialog wired to the injected actions, or raise it.

        The dialog is modeless (``show`` rather than ``exec``) so the tray
        context menu stays reachable while it is open; that is what lets a
        debrief triggered from the menu refresh the dialog. A second
        left-click brings the existing dialog to the front (restoring it if
        minimised) instead of opening another, and the reference is dropped
        on close so a stale, closed dialog is never refreshed.
        """
        if self._home is not None:
            self._home.bring_to_front()
            return
        self._pager.reset()
        dialog = self._home_factory(
            self._status_provider(),
            self._pager.page(),
            page_index=self._pager.page_index(),
            page_count=self._pager.page_count(),
            on_debrief_last=self._on_debrief_last,
            on_debrief_history=self._on_debrief_history,
            on_settings=self._on_settings,
            on_about=self._on_about,
            on_open_recent=self._opener,
            on_prev_page=self._on_recent_prev,
            on_next_page=self._on_recent_next,
            icon=self._icon,
        )
        self._home = dialog
        dialog.finished.connect(self._on_home_closed)
        dialog.show()

    def refresh_after_result(self) -> None:
        """Refresh both views after a new debrief landed on disk.

        The new file is already there, so the archive sees it; the submenu
        and any open home dialog are rebuilt from the newest page. An open
        home dialog is reset to that first page and its status refreshed, so
        a debrief generated from the tray menu while it is showing updates
        the dialog instead of leaving it on its opening snapshot.
        """
        self._pager.reset()
        self.rebuild_recent_menu()
        if self._home is not None:
            self._home.set_status(self._status_provider())
            self._update_home_recent()

    def _on_home_closed(self, _result: int = 0) -> None:
        """Drop the reference to the home dialog once it has closed."""
        self._home = None

    def _on_recent_prev(self) -> None:
        """Show the previous page of recents in the open home dialog."""
        self._pager.to_prev()
        self._update_home_recent()

    def _on_recent_next(self) -> None:
        """Show the next page of recents in the open home dialog."""
        self._pager.to_next()
        self._update_home_recent()

    def _update_home_recent(self) -> None:
        """Push the pager's current page to the open home dialog, if any."""
        if self._home is not None:
            self._home.show_recent_page(
                self._pager.page(),
                self._pager.page_index(),
                self._pager.page_count(),
            )
