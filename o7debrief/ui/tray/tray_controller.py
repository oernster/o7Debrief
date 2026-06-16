"""TrayController: the system-tray icon, menu and user actions for o7Debrief.

The controller owns a ``QSystemTrayIcon`` and its ``QMenu``. A right-click
shows the menu; a left-click opens the home dialog (built through an injected
factory so tests need no real window). The menu carries a disabled status line
that mirrors the live recording status, the two debrief actions, a submenu of
debriefs generated this run, a settings entry and quit.
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
from o7debrief.ui.windows.home import HomeDialog
from o7debrief.ui.windows.preview import open_debrief

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from o7debrief.application.dto.export_result import ExportResult
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

# Caption shown in the Recent debriefs submenu before anything is generated.
_NO_RECENT_TEXT = "No debriefs yet"

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
        self._recent: list[str] = []

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
        """Repopulate the Recent debriefs submenu from this run's outputs."""
        self._recent_menu.clear()
        if not self._recent:
            empty = QAction(_NO_RECENT_TEXT, self._recent_menu)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return
        for path in self._recent:
            self._add_recent_entry(path)

    def _add_recent_entry(self, path: str) -> None:
        """Add a single Recent debriefs entry that reopens its file."""
        action = QAction(path, self._recent_menu)
        action.triggered.connect(lambda _checked=False, p=path: self._opener(p))
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
        """Remember produced paths, refresh the submenu and open the report."""
        if not result.paths:
            self._notify(_EMPTY_TITLE, _EMPTY_BODY)
            return
        for path in result.paths:
            if path not in self._recent:
                self._recent.append(path)
        self._rebuild_recent_menu()
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
        """Build and show the home dialog wired to this controller's actions."""
        dialog = self._home_factory(
            self._session.status_text,
            tuple(self._recent),
            on_debrief_last=self._on_debrief_last,
            on_debrief_history=self._on_debrief_history,
            on_settings=self._on_settings_triggered,
            on_about=self._on_about_triggered,
            on_open_recent=self._opener,
            icon=self._icon,
        )
        dialog.exec()

    # ------------------------------------------------------------------ status

    def _on_status_changed(self, headline: str) -> None:
        """Update the status line when the view model reports a change."""
        self._refresh_status_caption(headline)

    def _refresh_status_caption(self, headline: str) -> None:
        """Set the disabled status action's caption to the given headline."""
        self._status_action.setText(headline)
