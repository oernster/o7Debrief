"""The setup window: a themed, state-aware lifecycle screen.

The window holds no installer logic of its own. It reads one state snapshot,
decides what to offer, then hands each operation to a worker thread. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QWidget

from installer.constants import APP_DISPLAY_NAME
from installer.ops.errors import InstallerError
from installer.ops.install_ops import InstallOptions, install, repair
from installer.ops.paths import install_target, installed_exe
from installer.ops.payload import app_version, licence_text
from installer.ops.progress import COMPLETE_PCT, MINIMUM_PCT
from installer.ops.running_app import close_running_app, is_app_running, launch
from installer.ops.uninstall_ops import uninstall
from installer.shared.logging_setup import log_step
from installer.state.model import InstallState, detect
from installer.state.registry import set_autostart
from installer.ui._main_window_build import (
    WindowWidgets,
    build_window,
    primary_label,
    subtitle_text,
)
from installer.ui.close_app_dialog import CloseAppDialog
from installer.ui.icons import app_icon
from installer.ui.licence_dialog import LicenceDialog
from installer.ui.themes import STYLESHEET, WINDOW_HEIGHT, WINDOW_WIDTH
from installer.ui.uninstall_dialog import UninstallDialog
from installer.ui.worker import OperationRunner

# Zero delay: the close is posted to the back of the event queue rather than
# postponed, so it happens on the very next turn, after the worker teardown
# already queued ahead of it.
_CLOSE_ON_NEXT_TURN_MS = 0

WINDOW_TITLE = f"Install {APP_DISPLAY_NAME}"
INSTALLED_MESSAGE = "Installed to {path}."
LAUNCH_FAILED_MESSAGE = (
    f"Installed, but {APP_DISPLAY_NAME} could not be started. "
    "Start it yourself from {path}."
)
REPAIRED_MESSAGE = "Repair complete."
UNINSTALLED_MESSAGE = f"{APP_DISPLAY_NAME} has been uninstalled."
CLOSE_FAILED_MESSAGE = "{detail}"

# Step messages written to the installer log. They exist so a report of "it
# quietly did nothing" can be answered from the machine rather than guessed at:
# the log names which action was chosen, what the versions were, whether the
# running application was closed and whether the launch afterwards worked.
LOG_PRIMARY = "primary action: state={state} installed={installed} bundled={bundled}"
LOG_NONE = "none"
LOG_APP_NOT_RUNNING = "application was not running"
LOG_CLOSE_DECLINED = "user declined to close the running application"
LOG_CLOSED = "running application closed"
LOG_CLOSE_FAILED = "could not close the running application: {detail}"
LOG_OPERATION_OK = "operation finished"
LOG_OPERATION_FAILED = "operation failed: {detail}"
LOG_LAUNCH_FAILED = "launch failed: {path}"
LOG_LAUNCHED = "launched {path}"


class InstallerWindow(QWidget):
    """The installer window: a themed, state-aware lifecycle screen."""

    def __init__(self) -> None:
        super().__init__()
        self._snapshot = detect(app_version(), install_target())
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(STYLESHEET)

        self._widgets: WindowWidgets = build_window(self, self._snapshot)
        self._runner = OperationRunner(self)
        self._wire()
        self._show_installed_actions()

    # ------------------------------------------------------------- wiring

    def _wire(self) -> None:
        """Connect every control to the action it performs."""
        widgets = self._widgets
        widgets.licence.clicked.connect(self._on_show_licence)
        widgets.primary.clicked.connect(self._on_primary)
        widgets.repair.clicked.connect(self._on_repair)
        widgets.uninstall.clicked.connect(self._on_uninstall)
        widgets.close.clicked.connect(self.close)
        widgets.autostart.toggled.connect(self._on_autostart_toggled)

    def _show_installed_actions(self) -> None:
        """Show Repair and Uninstall only when there is something to act on."""
        installed = self._snapshot.installed
        self._widgets.repair.setVisible(installed)
        self._widgets.uninstall.setVisible(installed)

    # ------------------------------------------------------------ actions

    def _on_show_licence(self) -> None:
        """Open the bundled licence in a themed, scrollable dialog."""
        LicenceDialog(licence_text(), self).exec()

    def _on_autostart_toggled(self, enabled: bool) -> None:
        """Apply the sign-in choice at once when the app is already installed.

        Before an install there is no executable to point the Run entry at, so
        the choice is simply carried into the install that follows.
        """
        if not self._snapshot.installed:
            return
        set_autostart(enabled, installed_exe(self._snapshot.install_dir))

    def _ensure_app_closed(self) -> bool:
        """Return True when it is safe to proceed, offering to close the app."""
        if not is_app_running():
            log_step(LOG_APP_NOT_RUNNING)
            return True
        if CloseAppDialog(self).exec() != QDialog.DialogCode.Accepted:
            log_step(LOG_CLOSE_DECLINED)
            return False
        try:
            close_running_app()
        except InstallerError as error:
            log_step(LOG_CLOSE_FAILED.format(detail=error))
            self._widgets.status.setText(CLOSE_FAILED_MESSAGE.format(detail=error))
            return False
        log_step(LOG_CLOSED)
        return True

    def _on_primary(self) -> None:
        """Install, upgrade or reinstall, then optionally launch the app."""
        log_step(
            LOG_PRIMARY.format(
                state=self._snapshot.state,
                installed=self._snapshot.installed_version or LOG_NONE,
                bundled=self._snapshot.bundled_version,
            )
        )
        if not self._ensure_app_closed():
            return
        widgets = self._widgets
        options = InstallOptions(
            target_dir=install_target(),
            desktop=widgets.desktop.isChecked(),
            start_menu=widgets.start_menu.isChecked(),
            autostart=widgets.autostart.isChecked(),
        )
        self._start(lambda report: install(options, progress=report), self._installed)

    def _on_repair(self) -> None:
        """Re-deploy the application files over the existing install."""
        if not self._ensure_app_closed():
            return
        location = self._snapshot.install_dir
        self._start(lambda report: repair(location, progress=report), self._repaired)

    def _on_uninstall(self) -> None:
        """Confirm, then remove the application, shortcuts and registration."""
        dialog = UninstallDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not self._ensure_app_closed():
            return
        remove_settings = dialog.remove_settings()
        self._start(
            lambda report: uninstall(remove_settings=remove_settings, progress=report),
            self._uninstalled,
        )

    # ------------------------------------------------------------ outcomes

    def _installed(self, result: object) -> None:
        """Report a completed install and launch the app when asked to."""
        exe_path = result if isinstance(result, Path) else None
        if exe_path is None:
            self._refresh()
            return
        self._widgets.status.setText(INSTALLED_MESSAGE.format(path=exe_path.parent))
        if self._widgets.launch_on_finish.isChecked():
            if not launch(exe_path):
                log_step(LOG_LAUNCH_FAILED.format(path=exe_path))
                # The install itself succeeded, so this is not an install
                # failure and must not read as one. It does mean the window
                # must stay open: closing on a launch that never happened left
                # the user with no application, no setup window and nothing
                # said, which is indistinguishable from a crash.
                self._widgets.status.setText(
                    LAUNCH_FAILED_MESSAGE.format(path=exe_path)
                )
                self._refresh()
                return
            log_step(LOG_LAUNCHED.format(path=exe_path))
            # Close on the next turn of the event loop rather than inside this
            # callback. The runner has already released its worker thread by
            # the time this runs, so closing here would be safe; posting it
            # keeps application shutdown out of a signal emission altogether,
            # which is the state that hung the setup program when the callback
            # was still arriving on the worker thread.
            QTimer.singleShot(_CLOSE_ON_NEXT_TURN_MS, self.close)
            return
        self._refresh()

    def _repaired(self, _result: object) -> None:
        """Report a completed repair."""
        self._widgets.status.setText(REPAIRED_MESSAGE)
        self._refresh()

    def _uninstalled(self, _result: object) -> None:
        """Report a completed uninstall and return the window to its first state."""
        self._widgets.status.setText(UNINSTALLED_MESSAGE)
        self._refresh(reread=False, state=InstallState.NOT_INSTALLED)

    # ------------------------------------------------------- worker plumbing

    def _start(self, operation, on_success) -> None:
        """Run one operation on a worker thread, showing progress while it runs."""
        self._set_busy(True)
        self._runner.start(
            operation,
            self._on_progress,
            lambda error, result: self._on_finished(error, result, on_success),
        )

    def _on_progress(self, pct: int, message: str) -> None:
        """Show the current phase and how far through it the operation is."""
        self._widgets.progress.setValue(pct)
        self._widgets.status.setText(message)

    def _on_finished(self, error: str, result: object, on_success) -> None:
        """Restore the window, then either report the failure or the success."""
        self._set_busy(False)
        if error:
            log_step(LOG_OPERATION_FAILED.format(detail=error))
            self._widgets.status.setText(error)
            return
        log_step(LOG_OPERATION_OK)
        on_success(result)

    def _set_busy(self, busy: bool) -> None:
        """Disable the actions and show the progress bar while work is running."""
        widgets = self._widgets
        widgets.progress.setVisible(busy)
        if busy:
            widgets.progress.setValue(MINIMUM_PCT)
        else:
            widgets.progress.setValue(COMPLETE_PCT)
        for button in (widgets.primary, widgets.repair, widgets.uninstall):
            button.setEnabled(not busy)

    def _refresh(self, *, reread: bool = True, state: str = "") -> None:
        """Re-read the installed state and relabel the window to match it."""
        if reread:
            self._snapshot = detect(app_version(), install_target())
        else:
            self._snapshot = replace(self._snapshot, state=state)
        widgets = self._widgets
        widgets.primary.setText(primary_label(self._snapshot))
        widgets.subtitle.setText(subtitle_text(self._snapshot))
        self._show_installed_actions()
