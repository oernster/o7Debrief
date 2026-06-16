"""Composition root for o7Debrief.

This is the single place where the layers are wired together. It is the only
module permitted to import ``o7debrief.infrastructure``: it constructs the
concrete adapters (journal source, config provider, exporters, sink, rank
store and clock), injects them into the application services, injects those
services into the ui, then starts the PySide6 event loop.

The flow is deliberately linear and explicit. There are no module-level
singletons; every object is built inside ``main`` and passed by constructor.
Filesystem locations come from the per-user environment variables and named
constants, never from literals scattered through the code. The number-format
tokens are read from the taxonomy ``[format]`` table so no display literal is
hardcoded here either.

main.py lives at the repository root, outside the ``o7debrief`` package, which
is what lets the structural composition-root test treat it as the one allowed
infrastructure-wiring boundary.
"""

from __future__ import annotations

import os
import signal
import sys
import tomllib
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from o7debrief import __version__
from o7debrief.application.dto.preferences import Preferences
from o7debrief.application.services.auto_debrief_trigger import (
    AutoDebriefTrigger,
)
from o7debrief.application.services.config_loading_service import (
    ConfigLoadingService,
)
from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.debrief_export_service import (
    DebriefExportService,
)
from o7debrief.application.services.debrief_presenter import (
    DebriefPresenter,
    NumberFormat,
)
from o7debrief.application.services.one_shot_debrief_service import (
    OneShotDebriefService,
)
from o7debrief.application.services.rank_analyzer import RankAnalyzer
from o7debrief.application.services.session_recorder import SessionRecorder
from o7debrief.application.services.update_service import UpdateService

# The composition root alone reaches into infrastructure.
from o7debrief.infrastructure import (
    FileJournalSource,
    FilesystemDebriefArchive,
    FilesystemSink,
    GitHubReleaseSource,
    HtmlDebriefExporter,
    JsonPreferencesStore,
    JsonRankSnapshotStore,
    MarkdownDebriefExporter,
    SystemClock,
    TomlConfigProvider,
    WindowsAutostart,
)
from o7debrief.infrastructure.journal import paths as journal_paths

from o7debrief.ui.tray.single_instance import SingleInstanceLock
from o7debrief.ui.tray.tray_controller import TrayController
from o7debrief.ui.view_models.session_view_model import SessionViewModel
from o7debrief.ui.windows.about import AboutDialog
from o7debrief.ui.windows.licence import LicenceDialog
from o7debrief.ui.windows.settings import SettingsDialog
from o7debrief.ui.windows.splash import SplashScreen

# Per-user environment variables that name the base directories on Windows.
_ENV_APPDATA = "APPDATA"
_ENV_LOCALAPPDATA = "LOCALAPPDATA"

# Application folder name used under both base directories.
_APP_DIR_NAME = "o7Debrief"
# Subdirectory under %LOCALAPPDATA% for persisted state (rank snapshots).
_STATE_DIR_NAME = "state"

# The user's Downloads folder is the default output location for debrief files.
# It is resolved from the Windows known-folder registration so a relocated
# Downloads folder is honoured, with a fallback to the conventional location.
_DOWNLOADS_DIR_NAME = "Downloads"
_SHELL_FOLDERS_SUBKEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
)
_DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"

# Location of the event taxonomy relative to this composition root.
_CONFIG_DIR_NAME = "config"
_TAXONOMY_FILE_NAME = "debrief_taxonomy.toml"

# Application icon bundled under assets/, shown in the tray and notifications.
_ASSETS_DIR_NAME = "assets"
_ICON_FILE_NAME = "o7debrief.ico"
# PNG form of the icon, used for the Windows toast notification header: the
# notification platform renders a PNG app logo more reliably than a .ico.
_ICON_PNG_FILE_NAME = "o7Debrief.png"

# Windows shell identity used to brand notifications. Windows draws a toast's
# header icon and name from the registration that matches the process's
# Application User Model ID, so the app declares an explicit id and registers
# its display name and icon under it; without this the header shows a blank
# placeholder. The id is stable across versions and is mirrored by the
# installer, which removes this registration on uninstall.
_APP_USER_MODEL_ID = "OliverErnster.o7Debrief"
_APP_TOAST_TITLE = "Commander Mission Debrief"
_AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"
_AUMID_DISPLAY_NAME_VALUE = "DisplayName"
_AUMID_ICON_URI_VALUE = "IconUri"

# Bundled LICENCE file shown verbatim by the Help > Licence dialog.
_LICENCE_FILE_NAME = "LICENSE"
_LICENCE_FALLBACK = (
    "Licence text not found. See https://www.gnu.org/licenses/lgpl-3.0.html"
)

# GitHub endpoints for the opt-in update check. The API endpoint returns the
# latest release as JSON (the one network call the app makes); the page URL is
# opened in the browser when a newer release exists. Nothing is downloaded or
# run by the check itself.
_RELEASES_API_URL = "https://api.github.com/repos/oernster/o7Debrief/releases/latest"
_RELEASES_PAGE_URL = "https://github.com/oernster/o7Debrief/releases/latest"

# The taxonomy table and keys that populate the display NumberFormat.
_FORMAT_TABLE = "format"
_KEY_CREDITS_SUFFIX = "credits_suffix"
_KEY_DISTANCE_SUFFIX = "distance_suffix"
_KEY_THOUSANDS = "thousands"
_KEY_DURATION_FORMAT = "duration_format"
_KEY_TIME_FORMAT = "time_format"
_KEY_DATETIME_FORMAT = "datetime_format"

# Candidate function names for journal-directory discovery, tried in order so
# the composition root binds to whichever name the infrastructure layer used.
_DISCOVERY_NAMES = (
    "discover_journal_dir",
    "get_journal_directory",
    "find_journal_directory",
    "journal_directory",
)

# Process exit code used when another instance already holds the lock.
_EXIT_ALREADY_RUNNING = 0

# How often (in milliseconds) the Qt loop yields to the Python interpreter so a
# pending Ctrl+C (SIGINT) handler can run. Qt's C++ event loop otherwise never
# returns control to Python, so the signal would never be delivered.
_SIGNAL_POLL_MS = 200

# Console guidance printed when the tray starts. o7Debrief has no window of its
# own, so a terminal launch needs to say where the app went and how to stop it.
_RUNNING_MESSAGE = (
    "o7 Debrief is running in the system tray. Left-click its icon to open the "
    "home screen; right-click for the full menu (generate a debrief, Settings, "
    "Help, Quit). Press Ctrl+C here to quit."
)
_NO_TRAY_MESSAGE = (
    "Warning: no system tray was detected, so the o7 Debrief icon may not be "
    "visible. The app is still running. Press Ctrl+C here to quit."
)


def _user_base(env_name: str) -> Path:
    """Return a per-user base directory from an environment variable.

    Falls back to the conventional Windows location under the home directory
    when the variable is not set, so the app still has somewhere to write.
    """
    base = os.environ.get(env_name)
    if base:
        return Path(base)
    return (
        Path.home() / "AppData" / ("Roaming" if env_name == _ENV_APPDATA else "Local")
    )


def _app_dir(env_name: str, *parts: str) -> Path:
    """Return (creating) an app-owned directory under a per-user base."""
    directory = _user_base(env_name).joinpath(_APP_DIR_NAME, *parts)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _taxonomy_path() -> Path:
    """Return the path to the taxonomy file beside this composition root."""
    return Path(__file__).resolve().parent / _CONFIG_DIR_NAME / _TAXONOMY_FILE_NAME


def _icon_path() -> Path:
    """Return the path to the application icon bundled under assets/."""
    return Path(__file__).resolve().parent / _ASSETS_DIR_NAME / _ICON_FILE_NAME


def _icon_png_path() -> Path:
    """Return the path to the PNG icon used for the toast notification header."""
    return Path(__file__).resolve().parent / _ASSETS_DIR_NAME / _ICON_PNG_FILE_NAME


def _set_app_user_model_id(app_user_model_id: str) -> None:
    """Declare an explicit Windows shell identity for the running process.

    Windows attributes a toast notification to this id and resolves the header
    icon and name from the matching registration. Setting it before any window
    exists is best effort: on a non-Windows host or an older shell the call is
    simply skipped.
    """
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_user_model_id)
    except (OSError, AttributeError):
        return


def _register_toast_identity(
    app_user_model_id: str, display_name: str, icon_path: Path
) -> None:
    """Register the notification header name and icon under the shell id.

    The notification platform reads ``DisplayName`` and ``IconUri`` from the
    per-user ``AppUserModelId`` class for the running process's id; writing them
    here lets the toast header show the app name and icon instead of a blank
    placeholder. Writing on each launch keeps the icon path correct whether the
    app runs from source or from an installed location. Best effort: a failed
    write simply leaves the header unbranded.
    """
    import winreg

    subkey = rf"{_AUMID_CLASSES_SUBKEY}\{app_user_model_id}"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as handle:
            winreg.SetValueEx(
                handle, _AUMID_DISPLAY_NAME_VALUE, 0, winreg.REG_SZ, display_name
            )
            winreg.SetValueEx(
                handle, _AUMID_ICON_URI_VALUE, 0, winreg.REG_SZ, str(icon_path)
            )
    except OSError:
        return


def _downloads_dir() -> Path:
    """Return the user's Downloads directory, the default output location.

    Reads the Windows known-folder registration so a relocated Downloads folder
    is honoured, falling back to the conventional location under the home
    directory when the value is absent or unreadable.
    """
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS_SUBKEY) as key:
            raw = str(winreg.QueryValueEx(key, _DOWNLOADS_GUID)[0])
        expanded = os.path.expandvars(raw)
        if expanded:
            return Path(expanded)
    except OSError:
        pass
    return Path.home() / _DOWNLOADS_DIR_NAME


def _load_number_format(taxonomy_path: Path) -> NumberFormat:
    """Build the display NumberFormat from the taxonomy ``[format]`` table.

    Reading the tokens from configuration keeps every display literal out of
    the code; the composition root is the right place to parse the file, since
    it is the only layer that owns concrete I/O wiring.
    """
    with taxonomy_path.open("rb") as handle:
        data = tomllib.load(handle)
    table = data[_FORMAT_TABLE]
    return NumberFormat(
        credits_suffix=table[_KEY_CREDITS_SUFFIX],
        distance_suffix=table[_KEY_DISTANCE_SUFFIX],
        thousands=table[_KEY_THOUSANDS],
        duration_format=table[_KEY_DURATION_FORMAT],
        time_format=table[_KEY_TIME_FORMAT],
        datetime_format=table[_KEY_DATETIME_FORMAT],
    )


def _discover_journal_dir() -> Path:
    """Locate the Elite Dangerous journal directory via infrastructure.

    The infrastructure ``journal.paths`` module owns discovery; this resolves
    whichever conventional entry-point name it exposes and calls it.
    """
    for name in _DISCOVERY_NAMES:
        candidate = getattr(journal_paths, name, None)
        if callable(candidate):
            return Path(candidate())
    raise RuntimeError(
        "No journal-directory discovery function found in "
        "o7debrief.infrastructure.journal.paths."
    )


def _autostart_command() -> str:
    """Return the command Windows should run at sign-in to launch o7Debrief.

    When packaged (a frozen or Nuitka-compiled build) the executable is itself
    the launcher; from source it is the interpreter running this script.
    """
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


def _open_settings(
    preferences_store: JsonPreferencesStore,
    autostart: WindowsAutostart,
    default_output_dir: Path,
) -> Callable[[], None]:
    """Return a handler that opens the Settings dialog and applies any change.

    The dialog is shown the current export format, startup state and output
    directory, and reports the chosen values through a callback; applying them
    here keeps the dialog free of file and registry I/O while the store and the
    registry stay the sources of truth. An unset output directory is shown as
    the default Downloads location.
    """

    def handler() -> None:
        preferences = preferences_store.load()
        current_format = preferences.export_format
        current_output = preferences.output_dir or str(default_output_dir)
        autostart_on = autostart.is_enabled()

        def save(export_format: str, start_on_boot: bool, output_dir: str) -> None:
            preferences_store.save(
                Preferences(export_format=export_format, output_dir=output_dir)
            )
            if start_on_boot:
                autostart.enable(_autostart_command())
            else:
                autostart.disable()

        SettingsDialog(current_format, autostart_on, current_output, save).exec()

    return handler


def _open_about(icon: QIcon) -> Callable[[], None]:
    """Return a handler that shows the About dialog with the application icon."""

    def handler() -> None:
        AboutDialog(icon).exec()

    return handler


def _load_licence_text() -> str:
    """Return the bundled LICENCE text, or a short fallback when it is absent.

    Reading the LICENCE file here (the composition root) keeps the ui free of
    I/O and makes the file the single source of truth for the licence shown in
    the app.
    """
    licence_file = Path(__file__).resolve().parent / _LICENCE_FILE_NAME
    try:
        return licence_file.read_text(encoding="utf-8")
    except OSError:
        return _LICENCE_FALLBACK


def _open_licence(licence_text: str) -> Callable[[], None]:
    """Return a handler that shows the Licence dialog with the given text."""

    def handler() -> None:
        LicenceDialog(licence_text).exec()

    return handler


def _install_interrupt_handling(app: QApplication) -> QTimer:
    """Make Ctrl+C (and Ctrl+Break) quit the Qt event loop cleanly.

    Qt's C++ event loop does not return to the Python interpreter while it runs,
    so a Python signal handler never gets a chance to fire on its own. A periodic
    no-op timer hands control back to the interpreter often enough for the
    handler to run, turning Ctrl+C into a clean quit. The timer is returned so
    the caller can keep it alive for the life of the app.
    """
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, lambda *_: app.quit())
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(_SIGNAL_POLL_MS)
    return timer


def _build_one_shot(
    journal_dir: Path,
    export_dir: Path,
    state_dir: Path,
    taxonomy_path: Path,
    preferences_store: JsonPreferencesStore,
) -> tuple[OneShotDebriefService, SessionRecorder]:
    """Wire the application services over the concrete infrastructure adapters.

    Returns both the one-shot use case and the session recorder, since the ui
    needs the recorder (via its view model) as well as the use case.
    """
    config_provider = TomlConfigProvider(str(taxonomy_path))
    spec = ConfigLoadingService(config_provider).load_spec()
    number_format = _load_number_format(taxonomy_path)

    journal_source = FileJournalSource(str(journal_dir))
    recorder = SessionRecorder(journal_source)
    builder = DebriefBuilder(spec)
    presenter = DebriefPresenter(spec, number_format)

    exporters = (HtmlDebriefExporter(), MarkdownDebriefExporter())
    sink = FilesystemSink(str(export_dir))
    clock = SystemClock()
    export_service = DebriefExportService(exporters, sink, clock)

    rank_store = JsonRankSnapshotStore(str(state_dir))
    rank_analyzer = RankAnalyzer()
    one_shot = OneShotDebriefService(
        journal_source=journal_source,
        debrief_builder=builder,
        presenter=presenter,
        export_service=export_service,
        preferences_store=preferences_store,
        rank_store=rank_store,
        rank_analyzer=rank_analyzer,
        clock=clock,
    )
    return one_shot, recorder


def main() -> int:
    """Build the whole app and run the Qt event loop; return the exit code."""
    lock = SingleInstanceLock()
    if not lock.acquire():
        return _EXIT_ALREADY_RUNNING

    try:
        taxonomy_path = _taxonomy_path()
        journal_dir = _discover_journal_dir()
        export_dir = _downloads_dir()
        state_dir = _app_dir(_ENV_LOCALAPPDATA, _STATE_DIR_NAME)
        preferences_store = JsonPreferencesStore(str(state_dir))
        autostart = WindowsAutostart()

        one_shot, recorder = _build_one_shot(
            journal_dir, export_dir, state_dir, taxonomy_path, preferences_store
        )

        # Declare the shell identity and notification branding before any Qt
        # window exists, so the first toast's header resolves to the app icon
        # and name rather than a blank placeholder.
        _set_app_user_model_id(_APP_USER_MODEL_ID)
        _register_toast_identity(_APP_USER_MODEL_ID, _APP_TOAST_TITLE, _icon_png_path())

        app = QApplication(sys.argv)
        app.setApplicationName(_APP_DIR_NAME)
        app.setQuitOnLastWindowClosed(False)
        icon = QIcon(str(_icon_path()))
        app.setWindowIcon(icon)

        # Keep a reference to the heartmoment timer for the life of the app so it
        # is not garbage-collected; it is what lets Ctrl+C quit the app.
        interrupt_timer = _install_interrupt_handling(app)

        session = SessionViewModel(recorder, AutoDebriefTrigger())
        archive = FilesystemDebriefArchive(export_dir, preferences_store)
        update_service = UpdateService(
            GitHubReleaseSource(_RELEASES_API_URL), __version__
        )
        controller = TrayController(
            one_shot=one_shot,
            session=session,
            icon=icon,
            archive=archive,
            on_settings=_open_settings(preferences_store, autostart, export_dir),
            on_about=_open_about(icon),
            on_licence=_open_licence(_load_licence_text()),
            on_quit=app.quit,
            update_service=update_service,
            releases_url=_RELEASES_PAGE_URL,
        )
        controller.show()

        if not QSystemTrayIcon.isSystemTrayAvailable():
            print(_NO_TRAY_MESSAGE, file=sys.stderr)
        print(_RUNNING_MESSAGE, flush=True)

        splash = SplashScreen(icon, __version__)
        splash.show_briefly()

        exit_code = app.exec()
        interrupt_timer.stop()
        return exit_code
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
