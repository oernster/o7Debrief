"""TrayController: the system-tray icon, menu and user actions for o7Debrief.

The controller owns a ``QSystemTrayIcon`` and its ``QMenu``. A right-click
shows the menu; a left-click opens the home dialog (built through an injected
factory so tests need no real window). The menu carries a disabled status line
that mirrors the live recording status, the two debrief actions, a submenu of
recent debriefs from the output directory, a settings entry and quit.
Both debrief actions drive the same injected one-shot use case (the app's one
reducer underlies both capture paths) and then open the produced report in the
browser through the preview helper. A low-frequency ``QTimer`` refreshes the
status line; there is no watchdog and no background thread here.

Every collaborator is injected through the constructor: the one-shot debrief
service, the session view model, an opener (defaulting to the preview helper),
and plain callables for settings and quit so this controller owns no
application lifecycle and no policy of its own. The controller is a dispatcher,
not a place where behaviour accumulates.

This module belongs to the ui layer and imports the application layer and the
standard library only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from o7debrief.application.errors import ApplicationError
from o7debrief.ui.tray.recents_pager import NullArchive, RecentsPager
from o7debrief.ui.windows.home import HomeDialog
from o7debrief.ui.windows.preview import open_debrief

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from o7debrief.application.dto.export_result import ExportResult
    from o7debrief.application.ports.debrief_archive import DebriefArchive
    from o7debrief.application.services.one_shot_debrief_service import (
        OneShotDebriefService,
    )
    from o7debrief.ui.view_models.session_view_model import SessionViewModel

__all__ = ["TrayController"]

# Visible application name used for the tray tooltip and notifications.
_APP_NAME = "o7 Debrief"

# Menu entry captions. Held as named constants so wording lives in one place
# and the smoke tests can find actions by their text.
_LAST_SESSION_TEXT = "Debrief my last session"
_HISTORY_TEXT = "Debrief my history to date"
_RECENT_TEXT = "Recent debriefs"
_SETTINGS_TEXT = "Settings"
_QUIT_TEXT = "Quit"
_HELP_TEXT = "Help"
_ABOUT_TEXT = "About o7 Debrief"
_LICENCE_TEXT = "Licence"

# Caption shown in the Recent debriefs submenu when the directory is empty.
_NO_RECENT_TEXT = "No debriefs yet"
# Final submenu entry shown when more debriefs exist than fit on one page; it
# opens the home dialog, where the full history can be paged through.
_MORE_TEXT = "More debriefs..."

# Notification titles and bodies for the two outcomes of a generate action.
_GENERATED_TITLE = "Debrief ready"
_GENERATED_BODY = "Your Commander Mission Debrief has been generated."
_EMPTY_TITLE = "Nothing to debrief"
_EMPTY_BODY = "No report was produced."
_FAILED_TITLE = "Debrief failed"

# How often, in milliseconds, the status line is refreshed. A low frequency is
# enough for a tray status line and keeps the app close to idle.
_STATUS_REFRESH_MS = 5000

# Index of the first produced path, used when opening the primary report.
_PRIMARY_PATH = 0

# How many recent debriefs are shown per page in the submenu and home dialog.
_RECENT_PAGE_SIZE = 10

# Dark-dossier styling for the tray menu, matching the splash and dialogs so the
# whole app reads as one piece rather than a native grey menu.
_MENU_STYLESHEET = """
QMenu {
    background-color: #16161d;
    border: 1px solid #2a2a33;
    padding: 6px;
    color: #d7d7da;
}
QMenu::item {
    padding: 8px 32px 8px 18px;
    margin: 1px 4px;
    border-radius: 6px;
}
QMenu::item:selected { background-color: #2a2a33; color: #f8a24a; }
QMenu::item:disabled { color: #6f6f78; }
QMenu::separator { height: 1px; background: #2a2a33; margin: 6px 8px; }
"""


def _noop() -> None:
    """Do nothing; the default handler for injected action callbacks."""
    return None


class TrayController(QObject):
    """Builds and drives the o7Debrief system-tray icon and its menu."""

    def __init__(
        self,
        one_shot: OneShotDebriefService,
        session: SessionViewModel,
        icon: QIcon | None = None,
        opener: Callable[[str], bool] = open_debrief,
        home_factory: Callable[..., HomeDialog] = HomeDialog,
        archive: DebriefArchive | None = None,
        on_settings: Callable[[], None] = _noop,
        on_about: Callable[[], None] = _noop,
        on_licence: Callable[[], None] = _noop,
        on_quit: Callable[[], None] = _noop,
        refresh_interval_ms: int = _STATUS_REFRESH_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._one_shot = one_shot
        self._session = session
        self._icon = icon
        self._opener = opener
        self._home_factory = home_factory
        self._on_settings = on_settings
        self._on_about = on_about
        self._on_licence = on_licence
        self._on_quit = on_quit
        self._home: HomeDialog | None = None
        self._pager = RecentsPager(
            archive if archive is not None else NullArchive(), _RECENT_PAGE_SIZE
        )

        self._tray = QSystemTrayIcon(self)
        if icon is not None:
            self._tray.setIcon(icon)
        self._tray.setToolTip(_APP_NAME)

        self._menu = QMenu()
        self._status_action = self._build_status_action()
        self._recent_menu = QMenu(_RECENT_TEXT)
        self._build_menu()
        for menu in (self._menu, self._recent_menu, self._help_menu):
            menu.setStyleSheet(_MENU_STYLESHEET)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)

        self._session.status_changed.connect(self._on_status_changed)
        self._timer = QTimer(self)
        self._timer.setInterval(refresh_interval_ms)
        self._timer.timeout.connect(self._session.refresh)

    # ------------------------------------------------------------------ lifecycle

    def show(self) -> None:
        """Show the tray icon, seed the status line and start refreshing."""
        self._refresh_status_caption(self._session.status_text)
        self._tray.show()
        self._timer.start()

    def stop(self) -> None:
        """Stop the refresh timer and hide the tray icon."""
        self._timer.stop()
        self._tray.hide()

    # ------------------------------------------------------------------ menu build

    def _build_status_action(self) -> QAction:
        """Create the disabled status-line action shown at the menu top."""
        action = QAction(self._session.status_text, self._menu)
        action.setEnabled(False)
        return action

    def _build_menu(self) -> None:
        """Assemble the tray menu in its fixed top-to-bottom order."""
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()
        self._add_action(_LAST_SESSION_TEXT, self._on_debrief_last)
        self._add_action(_HISTORY_TEXT, self._on_debrief_history)
        self._rebuild_recent_menu()
        self._menu.addMenu(self._recent_menu)
        self._menu.addSeparator()
        self._add_action(_SETTINGS_TEXT, self._on_settings_triggered)
        self._help_menu = self._build_help_menu()
        self._menu.addMenu(self._help_menu)
        self._add_action(_QUIT_TEXT, self._on_quit_triggered)

    def _add_action(self, text: str, handler: Callable[[], None]) -> QAction:
        """Add a top-level menu action wired to a handler; return it."""
        action = QAction(text, self._menu)
        action.triggered.connect(handler)
        self._menu.addAction(action)
        return action

    def _rebuild_recent_menu(self) -> None:
        """Repopulate the Recent debriefs submenu from the most recent page.

        The submenu always shows the newest page; when more debriefs exist than
        fit on a page a final entry opens the home dialog, where the full history
        can be paged through.
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
        action.triggered.connect(lambda _checked=False: self._open_home())
        self._recent_menu.addAction(action)

    def _build_help_menu(self) -> QMenu:
        """Build the Help submenu with the About and Licence entries."""
        menu = QMenu(_HELP_TEXT)
        about = QAction(_ABOUT_TEXT, menu)
        about.triggered.connect(self._on_about_triggered)
        menu.addAction(about)
        licence = QAction(_LICENCE_TEXT, menu)
        licence.triggered.connect(self._on_licence_triggered)
        menu.addAction(licence)
        return menu

    # ------------------------------------------------------------------ actions

    def _on_debrief_last(self) -> None:
        """Generate a debrief for the last session and open it."""
        self._run(self._one_shot.debrief_last_session)

    def _on_debrief_history(self) -> None:
        """Generate a debrief covering all history to date and open it."""
        self._run(self._one_shot.debrief_all_history)

    def _run(self, run_use_case: Callable[[], ExportResult]) -> None:
        """Run a debrief use case, record outputs and open the report.

        Any ApplicationError is shown as a notification rather than raised, so
        a failed read never tears the tray down.
        """
        try:
            result = run_use_case()
        except ApplicationError as error:
            self._notify(_FAILED_TITLE, str(error))
            return
        self._handle_result(result)

    def _handle_result(self, result: ExportResult) -> None:
        """Refresh the recents views and open the freshly produced report.

        The new file is already on disk, so the archive sees it; the submenu and
        any open home dialog are rebuilt from the newest page. An open home
        dialog is reset to that first page and its status refreshed, so a debrief
        generated from the tray menu while it is showing updates the dialog
        instead of leaving it on its opening snapshot.
        """
        if not result.paths:
            self._notify(_EMPTY_TITLE, _EMPTY_BODY)
            return
        self._pager.reset()
        self._rebuild_recent_menu()
        if self._home is not None:
            self._home.set_status(self._session.status_text)
            self._update_home_recent()
        self._opener(result.paths[_PRIMARY_PATH])
        self._notify(_GENERATED_TITLE, _GENERATED_BODY)

    def _notify(self, title: str, body: str) -> None:
        """Show a balloon notification, carrying the app icon when available.

        Passing the application QIcon makes the notification show the o7 Debrief
        icon rather than the generic system "information" glyph.
        """
        if self._icon is not None and not self._icon.isNull():
            self._tray.showMessage(title, body, self._icon)
        else:
            self._tray.showMessage(title, body)

    def _on_settings_triggered(self) -> None:
        """Invoke the injected settings handler."""
        self._on_settings()

    def _on_about_triggered(self) -> None:
        """Invoke the injected About handler."""
        self._on_about()

    def _on_licence_triggered(self) -> None:
        """Invoke the injected Licence handler."""
        self._on_licence()

    def _on_quit_triggered(self) -> None:
        """Stop the tray then invoke the injected quit handler."""
        self.stop()
        self._on_quit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Open the home dialog on a left-click; ignore other reasons."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_home()

    def _open_home(self) -> None:
        """Show the home dialog wired to this controller's actions, or raise it.

        The dialog is modeless (``show`` rather than ``exec``) so the tray
        context menu stays reachable while it is open; that is what lets a
        debrief triggered from the menu refresh the dialog. A second left-click
        brings the existing dialog to the front (restoring it if minimised)
        instead of opening another, and the reference is dropped on close so a
        stale, closed dialog is never refreshed.
        """
        if self._home is not None:
            self._home.bring_to_front()
            return
        self._pager.reset()
        dialog = self._home_factory(
            self._session.status_text,
            self._pager.page(),
            page_index=self._pager.page_index(),
            page_count=self._pager.page_count(),
            on_debrief_last=self._on_debrief_last,
            on_debrief_history=self._on_debrief_history,
            on_settings=self._on_settings_triggered,
            on_about=self._on_about_triggered,
            on_open_recent=self._opener,
            on_prev_page=self._on_recent_prev,
            on_next_page=self._on_recent_next,
            icon=self._icon,
        )
        self._home = dialog
        dialog.finished.connect(self._on_home_closed)
        dialog.show()

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

    # ------------------------------------------------------------------ status

    def _on_status_changed(self, headline: str) -> None:
        """Update the status line when the view model reports a change."""
        self._refresh_status_caption(headline)

    def _refresh_status_caption(self, headline: str) -> None:
        """Set the disabled status action's caption to the given headline."""
        self._status_action.setText(headline)
