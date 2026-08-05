"""The setup program's composition root.

This is the only module that wires the pieces together: it installs crash
logging, claims a taskbar identity, reads the command line and then either runs
the window or the headless uninstall the registered UninstallString invokes.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from installer.cli import Options, parse_args
from installer.constants import APP_DISPLAY_NAME
from installer.ops.errors import InstallerError
from installer.ops.uninstall_ops import uninstall
from installer.shared.logging_setup import install_crash_logging
from installer.ui.icons import app_icon, set_app_user_model_id
from installer.ui.main_window import WINDOW_TITLE, InstallerWindow
from installer.ui.uninstall_dialog import UninstallDialog

SETUP_APPLICATION_NAME = f"{APP_DISPLAY_NAME} Setup"

SUCCESS = 0
FAILURE = 1


def _uninstall_quietly(options: Options) -> int:
    """Run the uninstall with no window, as a scripted removal would."""
    try:
        uninstall(remove_settings=options.remove_settings)
    except InstallerError:
        return FAILURE
    return SUCCESS


def run_uninstall(options: Options) -> int:
    """Run the uninstall flow invoked by the registered UninstallString."""
    app = QApplication(sys.argv)
    app.setApplicationName(SETUP_APPLICATION_NAME)
    app.setWindowIcon(app_icon())
    if options.quiet:
        return _uninstall_quietly(options)
    dialog = UninstallDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return SUCCESS
    return _uninstall_quietly(
        Options(uninstall=True, quiet=True, remove_settings=dialog.remove_settings())
    )


def run_window() -> int:
    """Show the setup window and run the Qt event loop until it closes."""
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    app.setWindowIcon(app_icon())
    window = InstallerWindow()
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    """Run the setup program, or the uninstall flow when so invoked."""
    install_crash_logging()
    set_app_user_model_id()
    options = parse_args(list(argv) if argv is not None else sys.argv[1:])
    if options.uninstall:
        return run_uninstall(options)
    return run_window()


if __name__ == "__main__":
    raise SystemExit(main())
