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
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from o7debrief import __version__
from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.services.auto_debrief_trigger import (
    AutoDebriefTrigger,
)
from o7debrief.application.services.config_loading_service import (
    ConfigLoadingService,
)
from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.debrief_export_service import (
    BundleWriting,
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
from o7debrief.application.services.update_service import (
    UpdateService,
    platform_key_for,
)

# The composition root alone reaches into infrastructure.
from o7debrief.infrastructure import (
    FileJournalSource,
    FilesystemBundleSink,
    FilesystemDebriefArchive,
    FilesystemSink,
    GitHubReleaseSource,
    HtmlBundleExporter,
    HtmlDebriefExporter,
    JinjaTextTemplateRenderer,
    JsonPreferencesStore,
    JsonRankSnapshotStore,
    LinuxAutostart,
    MarkdownDebriefExporter,
    NameHumaniser,
    SystemClock,
    TomlConfigProvider,
    WindowsAutostart,
)
from o7debrief.infrastructure.journal import paths as journal_paths
from o7debrief.ui.tray.single_instance import SingleInstanceLock
from o7debrief.ui.tray.summon import SummonRequest, SummonWatcher
from o7debrief.ui.tray.tray_availability import TrayAvailabilityWatcher
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
# The value of ``os.name`` on Windows, plus the Linux equivalents of the
# known-folder registration the Windows branch reads.
_OS_WINDOWS = "nt"
_ENV_XDG_DOWNLOAD_DIR = "XDG_DOWNLOAD_DIR"
_ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
_XDG_CONFIG_DIR_NAME = ".config"
_USER_DIRS_FILE = "user-dirs.dirs"
_XDG_DOWNLOAD_ASSIGNMENT = "XDG_DOWNLOAD_DIR="
# Set by flatpak inside the sandbox. Its presence is how the composition root
# knows the autostart entry must re-launch the app through flatpak rather than
# through the interpreter path, which does not exist on the host.
_ENV_FLATPAK_ID = "FLATPAK_ID"
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

# The Linux counterpart of that shell identity: the reverse-DNS application id
# the desktop entry is installed under. A desktop knows a window belongs to an
# installed application by matching this against the entry's own name, so
# without it the home window opens as an unrelated entry with a generic icon
# rather than lighting up the launcher the user started it from. Setting it on
# Windows is harmless; Qt uses it only where the platform has the concept.
#
# It must stay identical to APP_ID in build_flatpak.sh, which is what names the
# installed .desktop file. A structural test pins the two together rather than
# trusting them to be kept in step by hand.
_DESKTOP_FILE_NAME = "uk.co.oernster.o7Debrief"
_APP_TOAST_TITLE = "Commander Mission Debrief"
_AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"
_AUMID_DISPLAY_NAME_VALUE = "DisplayName"
_AUMID_ICON_URI_VALUE = "IconUri"

# Bundled LICENCE file shown verbatim by the Help > Licence dialog.
_LICENCE_FILE_NAME = "LICENSE"
_LICENCE_FALLBACK = (
    "Licence text not found. See https://www.gnu.org/licenses/lgpl-3.0.html"
)

# GitHub endpoint for the update check. It returns the latest published
# release as JSON (the one network call the app makes), including the human
# releases page URL and the installer assets the prompt's Download button
# offers. Nothing is downloaded or run by the check itself.
_RELEASES_API_URL = "https://api.github.com/repos/oernster/o7Debrief/releases/latest"

# The taxonomy table and keys that populate the display NumberFormat.
_FORMAT_TABLE = "format"
_KEY_CREDITS_SUFFIX = "credits_suffix"
_KEY_COINS_SUFFIX = "coins_suffix"
_KEY_DISTANCE_SUFFIX = "distance_suffix"
_KEY_THOUSANDS = "thousands"
_KEY_DURATION_FORMAT = "duration_format"
_KEY_TIME_FORMAT = "time_format"
_KEY_DATETIME_FORMAT = "datetime_format"
_KEY_DATE_FORMAT = "date_format"
_KEY_MONTH_FORMAT = "month_format"
_KEY_TIMEZONE_LABEL = "timezone_label"

# The taxonomy table and keys that bound and split a whole-history debrief.
_HISTORY_TABLE = "history"
_KEY_ENTRIES_PER_PAGE = "entries_per_page"
_KEY_PAGE_BYTES_TARGET = "page_bytes_target"
_KEY_BYTES_PER_ENTRY = "bytes_per_entry_estimate"
_KEY_SINGLE_FILE = "single_file"
_KEY_SINGLE_FILE_MAX = "single_file_max_entries"
_KEY_TRUNCATION_NOTICE = "truncation_notice_format"
_KEY_ROLLUP_ENABLED = "rollup_enabled"
_KEY_ROLLUP_AFTER_DAYS = "rollup_after_days"
_KEY_ROLLUP_TEXT = "rollup_text_format"

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

# Process exit code used when no journal directory can be found. Nothing the app
# does is possible without one, so the run ends here. It is not a crash, so it
# earns no traceback; it is not success either, so it cannot be zero.
_EXIT_NO_JOURNAL = 1

# Shown when discovery finds no journal at all. The wording addresses the
# likeliest cause rather than the mechanism, because the mechanism is in the
# detail pane and the cause is usually simply that the game has not been played
# on this machine yet.
_NO_JOURNAL_TITLE = "o7 Debrief: no journal found"
_NO_JOURNAL_ADVICE = (
    "o7 Debrief could not find your Elite Dangerous journal, so there is "
    "nothing for it to read. The game writes the journal the first time you "
    "play on this machine.\n\n"
    "If you have played here, the journal is somewhere o7 Debrief did not "
    "look. The details say what it searched for."
)

# How often (in milliseconds) the Qt loop yields to the Python interpreter so a
# pending Ctrl+C (SIGINT) handler can run. Qt's C++ event loop otherwise never
# returns control to Python, so the signal would never be delivered.
_SIGNAL_POLL_MS = 200

# Console guidance printed when the app starts. o7Debrief has no window of its
# own, so a terminal launch needs to say where the app went and how to stop it.
# This is printed before the desktop has been asked whether it draws a tray, so
# it claims no tray icon: it says only what is true on every desktop.
_RUNNING_MESSAGE = (
    "o7 Debrief is running in the background. Launch o7 Debrief again at any "
    "time to bring up its home screen, which carries every action the app has. "
    "Press Ctrl+C here to quit."
)
# Printed once the desktop has answered, so each of these states a tray fact
# that has been observed rather than one assumed from the operating system.
_TRAY_MESSAGE = (
    "A system tray was found. Left-click the o7 Debrief icon to open the home "
    "screen; right-click for the full menu (generate a debrief, Settings, Help, "
    "Quit)."
)
_NO_TRAY_MESSAGE = (
    "This desktop draws no system tray, so o7 Debrief has opened its home "
    "screen instead. Closing that window leaves the app running and watching "
    "the journal; launch o7 Debrief again to bring the window back."
)

# Printed by a second launch, which does not start a second tray. Whether it
# says the window was opened depends on whether the request actually reached
# the running instance, so the two outcomes are never reported as one.
_SUMMONED_MESSAGE = (
    "o7 Debrief is already running. Its home screen has been brought up."
)
_ALREADY_RUNNING_MESSAGE = (
    "o7 Debrief is already running. Its home screen could not be summoned; use "
    "the tray icon to open it."
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


def _app_icon() -> QIcon:
    """Return the application icon, preferring the installed desktop icon.

    A Linux tray icon is published over D-Bus as a StatusNotifierItem, and an
    item may hand the panel either a NAME to look up in the icon theme or a
    bitmap. Qt sends a bitmap for a file-backed icon, and it sends one at the
    size it thinks a tray wants, which is 16 pixels; the panel then has a
    16 pixel image to fill a slot several times that, so the icon draws small
    and soft beside every other icon on the bar. Naming the icon instead lets
    the panel load whichever size of the installed hicolor set it actually
    wants, which is what makes it the same size as its neighbours.

    The name is the desktop-entry id, since that is what the icons are
    installed under. The lookup fails wherever the entry is not installed (on
    Windows, and when running from a source tree on Linux), so the bundled
    file remains the fallback.
    """
    return QIcon.fromTheme(_DESKTOP_FILE_NAME, QIcon(str(_icon_path())))


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

    The shell identity is a Windows concept and the registry module does not
    exist elsewhere, so off Windows this returns without doing anything. Guarding
    on the platform rather than catching the import keeps the intent explicit:
    there is nothing to register, not a registration that failed.
    """
    if os.name != _OS_WINDOWS:
        return

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
    directory when the value is absent or unreadable. On Linux the equivalent
    registration is the XDG user-directories file, which is what a localised
    desktop uses to call the folder something other than "Downloads".
    """
    if os.name != _OS_WINDOWS:
        return _xdg_downloads_dir()

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


def _xdg_downloads_dir() -> Path:
    """Return the Linux Downloads directory, honouring the XDG registration.

    ``XDG_DOWNLOAD_DIR`` is read first, then the ``user-dirs.dirs`` file the
    desktop actually maintains, which is where a localised session records that
    the folder is called Téléchargements or Downloads or anything else. The
    conventional English name is the last resort rather than the assumption.
    """
    from_env = os.environ.get(_ENV_XDG_DOWNLOAD_DIR)
    if from_env:
        return Path(os.path.expandvars(from_env))

    config_home = os.environ.get(_ENV_XDG_CONFIG_HOME)
    base = Path(config_home) if config_home else Path.home() / _XDG_CONFIG_DIR_NAME
    try:
        for line in (base / _USER_DIRS_FILE).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(_XDG_DOWNLOAD_ASSIGNMENT):
                continue
            value = stripped.split("=", 1)[1].strip().strip('"')
            expanded = os.path.expandvars(value.replace("$HOME", str(Path.home())))
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
        coins_suffix=table[_KEY_COINS_SUFFIX],
        distance_suffix=table[_KEY_DISTANCE_SUFFIX],
        thousands=table[_KEY_THOUSANDS],
        duration_format=table[_KEY_DURATION_FORMAT],
        time_format=table[_KEY_TIME_FORMAT],
        datetime_format=table[_KEY_DATETIME_FORMAT],
        date_format=table[_KEY_DATE_FORMAT],
        month_format=table[_KEY_MONTH_FORMAT],
        timezone_label=table[_KEY_TIMEZONE_LABEL],
    )


def _load_history_options(taxonomy_path: Path) -> HistoryOptions:
    """Build the history limits from the taxonomy ``[history]`` table.

    Same reasoning as the number format above: the composition root is the one
    layer that owns concrete I/O, so it is the one that reads the file.
    """
    with taxonomy_path.open("rb") as handle:
        data = tomllib.load(handle)
    table = data[_HISTORY_TABLE]
    return HistoryOptions(
        entries_per_page=table[_KEY_ENTRIES_PER_PAGE],
        page_bytes_target=table[_KEY_PAGE_BYTES_TARGET],
        bytes_per_entry_estimate=table[_KEY_BYTES_PER_ENTRY],
        single_file=table[_KEY_SINGLE_FILE],
        single_file_max_entries=table[_KEY_SINGLE_FILE_MAX],
        truncation_notice_format=table[_KEY_TRUNCATION_NOTICE],
        rollup_enabled=table[_KEY_ROLLUP_ENABLED],
        rollup_after_days=table[_KEY_ROLLUP_AFTER_DAYS],
        rollup_text_format=table[_KEY_ROLLUP_TEXT],
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


def _report_missing_journal(detail: str) -> int:
    """Say that no journal was found on every channel available, then give up.

    Discovery failing is an ordinary situation with a plain cause, usually that
    the game has not been played on this machine. It used to arrive as an
    unhandled traceback, which reads as a defect in o7 Debrief rather than as a
    statement about the machine. Most users never saw it at all either: the
    packaged Windows build is compiled with its console disabled and a desktop
    entry has no console either, so the app simply never appeared and gave no
    reason. That silence is the worse half of the bug.

    So it is said twice. stderr first, because it is the one channel that
    always exists and is what a terminal launch or a captured log will show,
    surviving even if Qt cannot start. The dialog second, for
    every launch that has no console to read.

    The locations that were tried go in the detail pane rather than the body.
    On Linux that is a dozen paths, which turns a readable sentence into a wall
    that gets skipped.
    """
    print(f"{_NO_JOURNAL_ADVICE}\n\n{detail}", file=sys.stderr, flush=True)

    # A message box needs a running application object, which this early
    # nothing else has built. Reusing the existing instance keeps this safe to call
    # at any point rather than only before Qt exists.
    application = QApplication.instance() or QApplication(sys.argv)
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(_NO_JOURNAL_TITLE)
    box.setText(_NO_JOURNAL_ADVICE)
    box.setDetailedText(detail)
    box.exec()
    application.quit()
    return _EXIT_NO_JOURNAL


def _autostart_command() -> str:
    """Return the command the session should run at sign-in to launch o7Debrief.

    Three cases. Inside a flatpak the entry is written for the HOST session to
    run; neither the interpreter nor this file exists out there, so the only
    command that works is a ``flatpak run`` of the app id. Otherwise, a packaged
    build (frozen or Nuitka-compiled) is its own launcher; from source it is
    the interpreter running this script.

    The flatpak case is checked first because inside the sandbox the source case
    also looks true and would write an entry naming a path the host cannot see.
    """
    flatpak_id = os.environ.get(_ENV_FLATPAK_ID)
    if flatpak_id:
        return f"flatpak run {flatpak_id}"
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


def _build_autostart() -> WindowsAutostart | LinuxAutostart:
    """Return the autostart adapter for the running platform.

    Both expose the same three methods, so everything downstream (the Settings
    dialog and its save handler) is written against the shape rather than
    against either implementation.
    """
    if os.name == _OS_WINDOWS:
        return WindowsAutostart()
    return LinuxAutostart()


def _on_tray_settled(controller: TrayController, available: bool) -> None:
    """React to the desktop's answer about whether it draws a system tray.

    With a tray, the icon is shown again: it may have been asked for before the
    host that draws it existed; asking twice costs nothing where it was
    there all along. Without one, the home window is opened, because the app is
    otherwise running with nothing on screen to click.
    """
    if available:
        controller.reattach_icon()
        print(_TRAY_MESSAGE, flush=True)
        return
    print(_NO_TRAY_MESSAGE, flush=True)
    controller.show_home()


def _open_settings(
    preferences_store: JsonPreferencesStore,
    autostart: WindowsAutostart | LinuxAutostart,
    default_output_dir: Path,
) -> Callable[[], None]:
    """Return a handler that opens the Settings dialog and applies any change.

    The dialog is shown the current export format, startup state and output
    directory, then reports the chosen values through a callback; applying them
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
            # Re-read before writing so fields the dialog does not edit (the
            # skipped update version) survive a settings save.
            preserved = preferences_store.load()
            preferences_store.save(
                replace(preserved, export_format=export_format, output_dir=output_dir)
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
    """Return the bundled LICENCE text, else a short fallback when it is absent.

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
    humaniser = NameHumaniser(config_provider.humanise_vocabulary())
    presenter = DebriefPresenter(
        spec, number_format, JinjaTextTemplateRenderer(humaniser)
    )

    exporters = (HtmlDebriefExporter(), MarkdownDebriefExporter())
    sink = FilesystemSink(str(export_dir))
    clock = SystemClock()
    # The history report is paged into a bundle rather than written as one
    # document that grows on every quit; Markdown has no bundle form and so
    # falls back to the capped single document.
    bundles = BundleWriting(
        exporters=(HtmlBundleExporter(),),
        sink=FilesystemBundleSink(str(export_dir)),
        options=_load_history_options(taxonomy_path),
    )
    export_service = DebriefExportService(exporters, sink, clock, bundles)

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
        spec=spec,
    )
    return one_shot, recorder


def main() -> int:
    """Build the whole app and run the Qt event loop; return the exit code."""
    lock = SingleInstanceLock()
    summon = SummonRequest()
    if not lock.acquire():
        # Another instance holds the lock, so this launch is a request to see
        # the app rather than a second copy of it. It leaves the marker the
        # running instance is watching for and exits: the window is the running
        # instance's to open, opening the same one a tray click would.
        print(
            _SUMMONED_MESSAGE if summon.send() else _ALREADY_RUNNING_MESSAGE,
            flush=True,
        )
        return _EXIT_ALREADY_RUNNING

    try:
        taxonomy_path = _taxonomy_path()
        try:
            journal_dir = _discover_journal_dir()
        except journal_paths.JournalDirectoryNotFoundError as error:
            # Not a crash: the machine simply has no journal on it. Discovery
            # already knows every location it looked in, so the message it
            # raises is the whole explanation and is passed through as it is.
            return _report_missing_journal(str(error))
        export_dir = _downloads_dir()
        state_dir = _app_dir(_ENV_LOCALAPPDATA, _STATE_DIR_NAME)
        preferences_store = JsonPreferencesStore(str(state_dir))
        autostart = _build_autostart()

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
        app.setDesktopFileName(_DESKTOP_FILE_NAME)
        app.setQuitOnLastWindowClosed(False)
        icon = _app_icon()
        app.setWindowIcon(icon)

        # Keep a reference to the heartmoment timer for the life of the app so it
        # is not garbage-collected; it is what lets Ctrl+C quit the app.
        interrupt_timer = _install_interrupt_handling(app)

        session = SessionViewModel(recorder, AutoDebriefTrigger())
        archive = FilesystemDebriefArchive(export_dir, preferences_store)
        update_service = UpdateService(
            GitHubReleaseSource(_RELEASES_API_URL),
            __version__,
            platform_key_for(sys.platform),
        )

        def load_skipped_version() -> str | None:
            return preferences_store.load().skipped_update_version or None

        def save_skipped_version(version: str) -> None:
            preferences_store.save(
                replace(preferences_store.load(), skipped_update_version=version)
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
            load_skipped_version=load_skipped_version,
            save_skipped_version=save_skipped_version,
        )
        controller.show()

        # Watch for a later launch asking to see the app. Parented to the
        # controller so it lives exactly as long as the tray it surfaces.
        summon_watcher = SummonWatcher(summon, controller.show_home, parent=controller)
        summon_watcher.start()

        print(_RUNNING_MESSAGE, flush=True)

        # Ask the running desktop whether it draws a tray rather than inferring
        # it from the platform, then give it time to answer: at sign-in the app
        # can be up before the panel that would host the icon. Until this
        # settles the app is reachable either way, because the summon watcher
        # above is already running.
        tray_availability = TrayAvailabilityWatcher(
            lambda available: _on_tray_settled(controller, available),
            parent=controller,
        )
        tray_availability.start()

        splash = SplashScreen(icon, __version__)
        splash.show_briefly()

        exit_code = app.exec()
        tray_availability.stop()
        summon_watcher.stop()
        interrupt_timer.stop()
        return exit_code
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
