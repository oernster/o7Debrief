#!/usr/bin/env python3
"""o7Debrief installer UI.

A self-contained PySide6 installer compiled into a single executable by
buildinstaller.py. It carries the built application bundle and the LICENCE as an
embedded payload (staged under ``payload/`` by the build tooling) and provides
the full lifecycle the author's other installers offer:

- Install, upgrade, reinstall and repair the per-user application.
- Register the app in Windows "Apps & features" (the HKCU Uninstall key), so it
  appears as an installed program with a working Uninstall action.
- Uninstall (also runnable headlessly via ``--uninstall``, which is how the
  registered UninstallString re-invokes a copy of this installer).
- Optional desktop and Start Menu shortcuts, and optional launch at sign-in.

It never needs administrator rights: it deploys to
``%LOCALAPPDATA%\\Programs\\o7Debrief`` and registers under HKCU. It is
deliberately standalone (it imports nothing from the ``o7debrief`` package) and
dependency-light: process detection uses ``tasklist``, version comparison is a
plain tuple compare and shortcuts are written through the Windows scripting
host, so the onefile build pulls in nothing beyond PySide6 and the stdlib.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "o7Debrief"
# Display name shown in all installer UI text and the Apps list. The identifier
# above stays spaceless for the payload directory, install path and exe.
APP_DISPLAY_NAME = "o7 Debrief"
APP_TAGLINE = "Commander Mission Debrief"
APP_PUBLISHER = "Oliver Ernster"
APP_URL = "https://oernster.github.io/o7Debrief/"

# Payload layout produced by buildinstaller.py: payload/o7Debrief/ holds the
# bundle's non-binary files (read by the installer UI), payload/o7Debrief.zip
# holds the full app bundle for deployment and payload/LICENSE holds the
# licence text.
_PAYLOAD_DIR_NAME = "payload"
_LICENSE_FILE_NAME = "LICENSE"
_VERSION_FILE_NAME = "VERSION"
_EXE_NAME = "o7Debrief.exe"
# The bundle ships as a single zip because Nuitka's onefile build drops loose
# executables and DLLs from an included data directory; the installer extracts
# this archive on deploy.
_PAYLOAD_ARCHIVE_NAME = "o7Debrief.zip"
_ICON_SUBPATH = ("assets", "o7Debrief.png")
# The multi-size .ico, used for shortcuts and the Apps-list DisplayIcon so the
# small sizes that Windows search and the taskbar render are present.
_SHORTCUT_ICON_SUBPATH = ("assets", "o7debrief.ico")

# Per-user locations (no administrator rights required).
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_APPDATA = "APPDATA"
_PROGRAMS_DIR_NAME = "Programs"
_START_MENU_SUBPATH = ("Microsoft", "Windows", "Start Menu", "Programs")
_DESKTOP_DIR_NAME = "Desktop"
_SHORTCUT_EXT = ".lnk"
# Per-user state directory the application writes (preferences, rank snapshots).
_STATE_DIR_NAME = "o7Debrief"

# The registered uninstaller is a copy of this installer placed under the
# install root, so "Apps & features" can re-run it with --uninstall.
_UNINSTALLER_SUBDIR = "_uninstall"
_UNINSTALLER_NAME = "o7DebriefSetup.exe"
_UNINSTALL_FLAG = "--uninstall"
# Under a Nuitka onefile build sys.executable is the unpacked temporary
# bootstrap, so the original launcher (the source for the registered
# uninstaller) is discovered via these instead.
_NUITKA_ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"
_EXE_SUFFIX = ".exe"

# HKCU Uninstall registration: this is what makes the app appear in
# "Apps & features" with a working Uninstall button.
_UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\o7Debrief"

# Per-user Run key for launching the app at Windows sign-in (no admin needed).
_RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "o7Debrief"

# The app registers its notification name and icon under this Application User
# Model ID at startup so Windows can brand its toasts; the uninstall flow
# removes that registration. Must match main.py's _APP_USER_MODEL_ID.
_APP_AUMID = "OliverErnster.o7Debrief"
_AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"

# Best-effort shell-out timeouts.
_POWERSHELL = "powershell"
_SHORTCUT_TIMEOUT_S = 15
_TASKLIST_TIMEOUT_S = 10

# Deferred delete (when the uninstaller lives inside the dir it must remove).
_DEFERRED_DELETE_ATTEMPTS = 30
_DEFERRED_DELETE_INTERVAL_MS = 500

# Crash diagnostics: a console-disabled onefile shows no traceback when it
# dies, so unhandled exceptions are appended to this file under the temp
# directory for the user to send back.
_INSTALLER_LOG_NAME = "o7debrief-installer.log"

# Window geometry, as named layout constants.
_WINDOW_TITLE = f"Install {APP_DISPLAY_NAME}"
_WINDOW_WIDTH = 620
_WINDOW_HEIGHT = 540
_LICENCE_DIALOG_HEIGHT = 540
_LICENCE_FONT_PX = 12
_ICON_PX = 56
_DIVIDER_PX = 1
_BORDER_PX = 1
_TEXT_PADDING_PX = 8
_SIDES = 2
_WIDTH_SAFETY_PX = 8
_MARGIN_SIDE = 36
_MARGIN_TOP = 28
_MARGIN_BOTTOM = 24
_DIALOG_MARGIN = 20
_SECTION_SPACING = 14
_HEADER_SPACING = 14
_BUTTON_GAP = 10

_LICENSE_FALLBACK = "The licence text was not bundled with this installer."

# Dark-dossier palette, mirroring the o7Debrief splash and report HUD so the
# installer feels of a piece with the application it deploys.
_BACKGROUND = "#0d0d10"
_SURFACE = "#16161d"
_EDGE = "#2a2a33"
_ACCENT = "#f07b05"
_ACCENT_SOFT = "#f8a24a"
_TEXT = "#d7d7da"
_MUTED = "#8a8a93"
_DANGER = "#7a1f25"
_DANGER_HOVER = "#94262e"

_STYLESHEET = f"""
QWidget {{ background: {_BACKGROUND}; color: {_TEXT}; font-family: 'Segoe UI'; }}
QLabel#HeaderTitle {{ font-size: 30px; font-weight: 700; color: {_ACCENT}; }}
QLabel#HeaderVersion {{ font-size: 13px; color: {_MUTED}; }}
QLabel#SubTitle {{ font-size: 18px; font-weight: 700; color: {_ACCENT}; }}
QLabel#Tagline {{ font-size: 13px; color: {_MUTED}; }}
QLabel#InstallPath {{ font-size: 12px; color: {_MUTED}; }}
QLabel#StatusLine {{ font-size: 13px; color: {_TEXT}; }}
QFrame#Divider {{ background: {_EDGE}; border: none; }}
QCheckBox {{ spacing: 10px; font-size: 13px; color: {_TEXT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QPushButton#LicenceButton {{
    background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_EDGE};
    padding: 8px 16px; border-radius: 16px; font-weight: 600;
}}
QPushButton#LicenceButton:hover {{ background: {_EDGE}; }}
QPushButton#PrimaryAction {{
    background: {_ACCENT}; color: {_BACKGROUND}; border: none;
    padding: 12px 28px; border-radius: 22px; font-size: 14px;
    font-weight: 700; min-width: 150px;
}}
QPushButton#PrimaryAction:hover {{ background: {_ACCENT_SOFT}; }}
QPushButton#PrimaryAction:disabled {{ background: {_EDGE}; color: {_MUTED}; }}
QPushButton#SecondaryAction {{
    background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_EDGE};
    padding: 12px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
}}
QPushButton#SecondaryAction:hover {{ background: {_EDGE}; }}
QPushButton#DangerAction {{
    background: {_DANGER}; color: {_TEXT}; border: none;
    padding: 12px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
}}
QPushButton#DangerAction:hover {{ background: {_DANGER_HOVER}; }}
QTextEdit {{
    background: {_SURFACE}; border: {_BORDER_PX}px solid {_EDGE};
    border-radius: 10px; color: {_TEXT}; padding: {_TEXT_PADDING_PX}px;
}}
QTextEdit#LicenceView {{
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: {_LICENCE_FONT_PX}px;
}}
QDialog {{ background: {_BACKGROUND}; }}
"""


# --------------------------------------------------------------------- payload


def _bundle_root() -> Path:
    """Return the directory holding the unpacked payload and licence."""
    return Path(__file__).resolve().parent


def _payload_app_dir() -> Path:
    """Return the bundled application directory inside the payload."""
    return _bundle_root() / _PAYLOAD_DIR_NAME / APP_NAME


def _payload_archive() -> Path:
    """Return the zipped application bundle inside the payload."""
    return _bundle_root() / _PAYLOAD_DIR_NAME / _PAYLOAD_ARCHIVE_NAME


def _license_text() -> str:
    """Return the bundled licence text, or a fallback when it is absent."""
    candidates = (
        _bundle_root() / _LICENSE_FILE_NAME,
        _bundle_root() / _PAYLOAD_DIR_NAME / _LICENSE_FILE_NAME,
    )
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return _LICENSE_FALLBACK


def _app_version() -> str:
    """Return the bundled application version, or an empty string if absent."""
    candidates = (
        _payload_app_dir() / _VERSION_FILE_NAME,
        _bundle_root() / _PAYLOAD_DIR_NAME / _VERSION_FILE_NAME,
        _bundle_root() / _VERSION_FILE_NAME,
    )
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return ""


def _app_icon() -> QIcon:
    """Return the bundled application icon, or an empty icon when absent."""
    path = _payload_app_dir().joinpath(*_ICON_SUBPATH)
    if path.is_file():
        return QIcon(str(path))
    return QIcon()


def _install_target() -> Path:
    """Return the per-user install directory for the application."""
    base = os.environ.get(_ENV_LOCALAPPDATA)
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / _PROGRAMS_DIR_NAME / APP_NAME


def _state_dir() -> Path:
    """Return the per-user state directory the app writes (settings, ranks)."""
    base = os.environ.get(_ENV_LOCALAPPDATA)
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / _STATE_DIR_NAME


# ------------------------------------------------------------------- versioning


def _version_tuple(version: str) -> tuple[int, ...]:
    """Return a comparable tuple of the numeric parts of a version string."""
    parts: list[int] = []
    for raw in version.strip().split("."):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def _compare_versions(left: str, right: str) -> int:
    """Return -1, 0 or 1 for left < right, left == right or left > right."""
    a = _version_tuple(left)
    b = _version_tuple(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


# --------------------------------------------------------------------- registry


def _read_registry_str(key: str, name: str) -> str | None:
    """Return an HKCU string value, or None when the key or value is absent."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            return str(winreg.QueryValueEx(handle, name)[0])
    except OSError:
        return None


def _write_uninstall_entry(install_dir: Path, uninstaller: Path, version: str) -> None:
    """Register the app under HKCU so it appears in Apps and features."""
    import winreg

    icon = install_dir.joinpath(*_SHORTCUT_ICON_SUBPATH)
    display_icon = str(icon if icon.exists() else install_dir / _EXE_NAME)
    estimated_kb = _dir_size_kb(install_dir)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _UNINSTALL_KEY) as handle:
        winreg.SetValueEx(handle, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(handle, "DisplayVersion", 0, winreg.REG_SZ, version)
        winreg.SetValueEx(handle, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(
            handle,
            "UninstallString",
            0,
            winreg.REG_SZ,
            f'"{uninstaller}" {_UNINSTALL_FLAG}',
        )
        winreg.SetValueEx(handle, "DisplayIcon", 0, winreg.REG_SZ, display_icon)
        winreg.SetValueEx(handle, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(handle, "URLInfoAbout", 0, winreg.REG_SZ, APP_URL)
        winreg.SetValueEx(handle, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(handle, "NoRepair", 0, winreg.REG_DWORD, 1)
        if estimated_kb is not None:
            winreg.SetValueEx(
                handle, "EstimatedSize", 0, winreg.REG_DWORD, estimated_kb
            )


def _delete_uninstall_entry() -> None:
    """Remove the HKCU Uninstall registration (best effort)."""
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _UNINSTALL_KEY)
    except OSError:
        return


def _delete_toast_identity() -> None:
    """Remove the app's notification (AppUserModelId) registration.

    The app writes its toast name and icon under HKCU on launch; removing the
    key on uninstall leaves no orphaned registration behind. Best effort.
    """
    import winreg

    try:
        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER, rf"{_AUMID_CLASSES_SUBKEY}\{_APP_AUMID}"
        )
    except OSError:
        return


def _installed_version() -> str | None:
    """Return the registered installed version, or None when not installed."""
    return _read_registry_str(_UNINSTALL_KEY, "DisplayVersion")


def _installed_location() -> Path | None:
    """Return the registered install location, or None when not installed."""
    raw = _read_registry_str(_UNINSTALL_KEY, "InstallLocation")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else None


def _dir_size_kb(path: Path) -> int | None:
    """Return the total size of a directory in KiB, or None on error."""
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return None
    return total // 1024


# ------------------------------------------------------------------ autostart


def _set_autostart(enabled: bool, exe_path: Path) -> None:
    """Add or remove the per-user Run entry that starts the app at sign-in."""
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_SUBKEY) as key:
            if enabled:
                winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(key, _RUN_VALUE)
                except OSError:
                    pass
    except OSError:
        return


def _remove_autostart() -> None:
    """Remove the per-user Run entry (best effort), used on uninstall."""
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_SUBKEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, _RUN_VALUE)
            except OSError:
                pass
    except OSError:
        return


# ------------------------------------------------------------------- processes


def _is_app_running() -> bool:
    """Return True when o7Debrief.exe appears in the task list (best effort)."""
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            ["tasklist", "/fi", f"imagename eq {_EXE_NAME}", "/nh"],
            capture_output=True,
            text=True,
            timeout=_TASKLIST_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            creationflags=no_window,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return _EXE_NAME.lower() in result.stdout.lower()


# ------------------------------------------------------------------- shortcuts


def _start_menu_link() -> Path | None:
    """Return the per-user Start Menu shortcut path, or None when unavailable."""
    appdata = os.environ.get(_ENV_APPDATA)
    if not appdata:
        return None
    programs = Path(appdata).joinpath(*_START_MENU_SUBPATH)
    return programs / f"{APP_DISPLAY_NAME}{_SHORTCUT_EXT}"


def _desktop_link() -> Path:
    """Return the per-user Desktop shortcut path."""
    return Path.home() / _DESKTOP_DIR_NAME / f"{APP_DISPLAY_NAME}{_SHORTCUT_EXT}"


def _run_powershell(command: str) -> None:
    """Run a PowerShell command, ignoring failures (best effort)."""
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(
            [_POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", command],
            check=False,
            timeout=_SHORTCUT_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=no_window,
        )
    except (OSError, subprocess.SubprocessError):
        return


def _create_shortcut(exe_path: Path, link: Path) -> None:
    """Write a shortcut to the installed exe with the app icon (best effort)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    icon = exe_path.parent.joinpath(*_SHORTCUT_ICON_SUBPATH)
    icon_clause = f"$s.IconLocation = '{icon}'; " if icon.exists() else ""
    command = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('"
        f"{link}'); $s.TargetPath = '{exe_path}'; "
        f"$s.WorkingDirectory = '{exe_path.parent}'; "
        f"{icon_clause}$s.Save()"
    )
    _run_powershell(command)


def _remove_shortcut(link: Path | None) -> None:
    """Delete a shortcut file if present (best effort)."""
    if link is None:
        return
    try:
        link.unlink(missing_ok=True)
    except OSError:
        return


def _apply_shortcuts(exe_path: Path, *, desktop: bool, start_menu: bool) -> None:
    """Create or remove the desktop and Start Menu shortcuts to match options."""
    desktop_link = _desktop_link()
    if desktop:
        _create_shortcut(exe_path, desktop_link)
    else:
        _remove_shortcut(desktop_link)

    start_link = _start_menu_link()
    if start_menu and start_link is not None:
        _create_shortcut(exe_path, start_link)
    else:
        _remove_shortcut(start_link)


# ----------------------------------------------------------------- deploy/ops


def _deploy_files(target: Path) -> Path:
    """Extract the bundled application archive to ``target``; return the exe.

    The bundle ships as a single zip because Nuitka's onefile build drops loose
    executables and DLLs from an included data directory. Any previous install
    at the target is removed first so the result is a clean deployment.
    """
    archive = _payload_archive()
    if not archive.is_file():
        raise FileNotFoundError(f"Bundled application not found at {archive}.")
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(target)
    return target / _EXE_NAME


def _original_installer_exe() -> Path:
    """Return the original onefile installer the user launched.

    Under a Nuitka onefile build ``sys.executable`` is the unpacked temporary
    bootstrap rather than the launcher; it must not be registered as the
    uninstaller. The real launcher is exposed through the NUITKA_ONEFILE_BINARY
    environment variable and as ``sys.argv[0]``. Prefer those and fall back to
    ``sys.executable`` only when neither resolves to an executable outside the
    temporary directory.
    """
    temp_root = Path(tempfile.gettempdir()).resolve()
    candidates = (
        os.environ.get(_NUITKA_ONEFILE_ENV, ""),
        sys.argv[0] if sys.argv else "",
    )
    for raw in candidates:
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except OSError:
            continue
        if path.suffix.lower() != _EXE_SUFFIX or not path.is_file():
            continue
        if path == temp_root or temp_root in path.parents:
            continue
        return path
    return Path(sys.executable)


def _copy_uninstaller(install_dir: Path) -> Path:
    """Copy this installer into the install root to act as the uninstaller.

    Best effort: the application is already deployed by the time this runs, so
    a failure here degrades to using the running executable as the uninstall
    source rather than failing the whole install.
    """
    source = _original_installer_exe()
    destination = install_dir / _UNINSTALLER_SUBDIR / _UNINSTALLER_NAME
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except Exception:
        return source
    return destination


def install(target: Path, *, desktop: bool, start_menu: bool, autostart: bool) -> Path:
    """Run the full install/upgrade/reinstall: files, registry and shortcuts."""
    exe_path = _deploy_files(target)
    uninstaller = _copy_uninstaller(target)
    _write_uninstall_entry(target, uninstaller, _app_version() or "0.0.0")
    _apply_shortcuts(exe_path, desktop=desktop, start_menu=start_menu)
    _set_autostart(autostart, exe_path)
    return exe_path


def repair(install_dir: Path) -> Path:
    """Re-deploy the application files over an existing install, then re-register.

    Without a per-file manifest the safe, simple repair is a full re-copy of the
    bundled files: it restores anything missing or altered. User settings live
    outside the install directory, so they are untouched.
    """
    exe_path = _deploy_files(install_dir)
    uninstaller = _copy_uninstaller(install_dir)
    _write_uninstall_entry(install_dir, uninstaller, _app_version() or "0.0.0")
    _apply_shortcuts(exe_path, desktop=True, start_menu=True)
    return exe_path


def uninstall(*, remove_settings: bool) -> None:
    """Remove shortcuts, registry, autostart, user state and the install dir."""
    install_dir = _installed_location() or _install_target()
    _remove_shortcut(_desktop_link())
    _remove_shortcut(_start_menu_link())
    _remove_autostart()
    _delete_uninstall_entry()
    _delete_toast_identity()
    if remove_settings:
        shutil.rmtree(_state_dir(), ignore_errors=True)
    if install_dir.exists():
        if _running_from_inside(install_dir):
            _schedule_delete_after_exit(install_dir)
        else:
            shutil.rmtree(install_dir, ignore_errors=True)


def _running_from_inside(install_dir: Path) -> bool:
    """Return True when this process's exe lives inside ``install_dir``."""
    try:
        running = Path(sys.executable).resolve()
        root = install_dir.resolve()
    except OSError:
        return True
    return running == root or root in running.parents


def _schedule_delete_after_exit(install_dir: Path) -> None:
    """Delete ``install_dir`` from a detached helper once this process exits.

    The registered uninstaller lives inside the install directory, so it cannot
    remove its own running exe. A hidden PowerShell process polls and deletes
    once the lock is released, rather than racing a fixed delay.
    """
    escaped = str(install_dir).replace("'", "''")
    script = (
        f"$d = '{escaped}'; "
        f"for ($i = 0; $i -lt {_DEFERRED_DELETE_ATTEMPTS}; $i++) {{ "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        "Remove-Item -LiteralPath $d -Recurse -Force "
        "-ErrorAction SilentlyContinue; "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        f"Start-Sleep -Milliseconds {_DEFERRED_DELETE_INTERVAL_MS} "
        "}"
    )
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    detached = getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [
                _POWERSHELL,
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                script,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=no_window | detached,
        )
    except (OSError, subprocess.SubprocessError):
        return


def _launch(exe_path: Path) -> None:
    """Start the installed application without waiting for it (best effort)."""
    try:
        subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
    except OSError:
        return


# ------------------------------------------------------------------- app state


class AppState:
    """The installed-vs-bundled relationship, driving the primary action."""

    NOT_INSTALLED = "not_installed"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"
    DOWNGRADE = "downgrade"


def _detect_state() -> str:
    """Classify the current install against the bundled version."""
    installed = _installed_version()
    location = _installed_location()
    if installed is None or location is None or not location.exists():
        return AppState.NOT_INSTALLED
    comparison = _compare_versions(_app_version() or "0.0.0", installed)
    if comparison > 0:
        return AppState.UPGRADE
    if comparison < 0:
        return AppState.DOWNGRADE
    return AppState.REINSTALL


def _primary_label(state: str) -> str:
    """Return the primary button caption for an install state."""
    version = _app_version()
    if state == AppState.NOT_INSTALLED:
        return "Install"
    if state == AppState.UPGRADE:
        return f"Upgrade to {version}" if version else "Upgrade"
    if state == AppState.DOWNGRADE:
        return "Reinstall (older)"
    return "Reinstall"


# ----------------------------------------------------------------------- views


def _licence_view_width(view: QTextEdit, text: str) -> int:
    """Return the pixel width that shows the widest licence line in full."""
    view.ensurePolished()
    metrics = view.fontMetrics()
    lines = text.splitlines() or [text]
    widest = max(metrics.horizontalAdvance(line) for line in lines)
    doc_margin = round(view.document().documentMargin())
    scrollbar = view.verticalScrollBar().sizeHint().width()
    chrome = _SIDES * (doc_margin + _TEXT_PADDING_PX + _BORDER_PX)
    return widest + scrollbar + chrome + _WIDTH_SAFETY_PX


class LicenceDialog(QDialog):
    """A themed, scrollable view of the bundled licence text."""

    def __init__(self, licence_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} Licence")
        self.setWindowIcon(_app_icon())
        self.setStyleSheet(_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _DIALOG_MARGIN, _DIALOG_MARGIN, _DIALOG_MARGIN, _DIALOG_MARGIN
        )
        layout.setSpacing(_BUTTON_GAP)

        view = QTextEdit()
        view.setObjectName("LicenceView")
        view.setReadOnly(True)
        view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        view.setPlainText(licence_text)
        layout.addWidget(view)

        view_width = _licence_view_width(view, licence_text)
        view.setMinimumWidth(view_width)
        self.resize(view_width + _SIDES * _DIALOG_MARGIN, _LICENCE_DIALOG_HEIGHT)

        close = QPushButton("Close")
        close.setObjectName("SecondaryAction")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)


class InstallerWindow(QWidget):
    """The installer window: a themed, state-aware lifecycle screen."""

    def __init__(self) -> None:
        super().__init__()
        self._state = _detect_state()
        self.setWindowTitle(_WINDOW_TITLE)
        self.setWindowIcon(_app_icon())
        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setStyleSheet(_STYLESHEET)
        self._desktop = QCheckBox("Create a desktop shortcut")
        self._start_menu = QCheckBox("Create a Start Menu shortcut")
        self._launch_on_finish = QCheckBox("Launch o7 Debrief when finished")
        self._autostart = QCheckBox("Start o7 Debrief when I sign in to Windows")
        self._status = QLabel("")
        self._status.setObjectName("StatusLine")
        self._status.setWordWrap(True)
        self._primary = QPushButton(_primary_label(self._state))
        self._primary.setObjectName("PrimaryAction")
        self._repair = QPushButton("Repair")
        self._repair.setObjectName("SecondaryAction")
        self._uninstall = QPushButton("Uninstall")
        self._uninstall.setObjectName("DangerAction")
        self._build_ui()

    # ----------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        """Assemble the themed installer layout in a single top-to-bottom column."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _MARGIN_SIDE, _MARGIN_TOP, _MARGIN_SIDE, _MARGIN_BOTTOM
        )
        layout.setSpacing(_SECTION_SPACING)

        layout.addLayout(self._build_header())

        subtitle = QLabel(self._subtitle_text())
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle)

        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("Tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(tagline)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(_DIVIDER_PX)
        layout.addWidget(divider)

        path_label = QLabel(f"Install location: {_install_target()}")
        path_label.setObjectName("InstallPath")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        self._desktop.setChecked(True)
        layout.addWidget(self._desktop)
        self._start_menu.setChecked(True)
        layout.addWidget(self._start_menu)
        self._launch_on_finish.setChecked(True)
        layout.addWidget(self._launch_on_finish)
        layout.addWidget(self._autostart)
        layout.addWidget(self._status)

        layout.addStretch()
        layout.addLayout(self._build_buttons())

    def _build_header(self) -> QHBoxLayout:
        """Build the header row: icon, title and version, with a Licence button."""
        header = QHBoxLayout()
        header.setSpacing(_HEADER_SPACING)

        icon = _app_icon()
        if not icon.isNull():
            badge = QLabel()
            badge.setPixmap(icon.pixmap(QSize(_ICON_PX, _ICON_PX)))
            header.addWidget(badge)

        title = QLabel(f"{APP_DISPLAY_NAME} Setup")
        title.setObjectName("HeaderTitle")
        header.addWidget(title)

        version = _app_version()
        if version:
            version_label = QLabel(f"v{version}")
            version_label.setObjectName("HeaderVersion")
            version_label.setAlignment(
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
            )
            header.addWidget(version_label)

        header.addStretch()

        licence_button = QPushButton("Licence")
        licence_button.setObjectName("LicenceButton")
        licence_button.clicked.connect(self._on_show_licence)
        header.addWidget(licence_button)
        return header

    def _build_buttons(self) -> QHBoxLayout:
        """Build the action row: primary, Repair, Uninstall and Close."""
        self._primary.clicked.connect(self._on_primary)
        self._repair.clicked.connect(self._on_repair)
        self._uninstall.clicked.connect(self._on_uninstall)
        close_button = QPushButton("Close")
        close_button.setObjectName("SecondaryAction")
        close_button.clicked.connect(self.close)

        installed = self._state != AppState.NOT_INSTALLED
        self._repair.setVisible(installed)
        self._uninstall.setVisible(installed)

        buttons = QHBoxLayout()
        buttons.setSpacing(_BUTTON_GAP)
        buttons.addWidget(self._uninstall)
        buttons.addStretch()
        buttons.addWidget(self._repair)
        buttons.addWidget(self._primary)
        buttons.addWidget(close_button)
        return buttons

    def _subtitle_text(self) -> str:
        """Return a subtitle reflecting whether this is a fresh install."""
        if self._state == AppState.NOT_INSTALLED:
            return f"Welcome to the {APP_DISPLAY_NAME} installer"
        return f"{APP_DISPLAY_NAME} is already installed"

    # ---------------------------------------------------------------- actions

    def _on_show_licence(self) -> None:
        """Open the bundled licence in a themed, scrollable dialog."""
        LicenceDialog(_license_text(), self).exec()

    def _guard_not_running(self) -> bool:
        """Return True when it is safe to proceed; warn if the app is running."""
        if _is_app_running():
            self._status.setText(
                "o7 Debrief is running. Please close it from the system tray, "
                "then try again."
            )
            return False
        return True

    def _on_primary(self) -> None:
        """Install, upgrade or reinstall, then optionally launch the app."""
        if not self._guard_not_running():
            return
        self._set_busy("Installing...")
        try:
            exe_path = install(
                _install_target(),
                desktop=self._desktop.isChecked(),
                start_menu=self._start_menu.isChecked(),
                autostart=self._autostart.isChecked(),
            )
        except Exception as error:
            self._finish_error(f"Installation failed: {error}")
            return
        self._status.setText(f"Installed to {exe_path.parent}.")
        if self._launch_on_finish.isChecked():
            _launch(exe_path)
            self.close()
            return
        self._refresh_after_change()

    def _on_repair(self) -> None:
        """Re-deploy the application files over the existing install."""
        if not self._guard_not_running():
            return
        location = _installed_location() or _install_target()
        self._set_busy("Repairing...")
        try:
            repair(location)
        except Exception as error:
            self._finish_error(f"Repair failed: {error}")
            return
        self._status.setText("Repair complete.")
        self._refresh_after_change()

    def _on_uninstall(self) -> None:
        """Confirm, then remove the application, shortcuts and registration."""
        if not self._guard_not_running():
            return
        dialog = UninstallDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._set_busy("Uninstalling...")
        try:
            uninstall(remove_settings=dialog.remove_settings())
        except Exception as error:
            self._finish_error(f"Uninstall failed: {error}")
            return
        self._status.setText("o7 Debrief has been uninstalled.")
        self._state = AppState.NOT_INSTALLED
        self._primary.setText(_primary_label(self._state))
        self._repair.setVisible(False)
        self._uninstall.setVisible(False)
        self._primary.setEnabled(True)

    def _set_busy(self, message: str) -> None:
        """Show a status message and disable the action buttons during work."""
        self._status.setText(message)
        self._primary.setEnabled(False)
        self._repair.setEnabled(False)
        self._uninstall.setEnabled(False)
        QApplication.processEvents()

    def _finish_error(self, message: str) -> None:
        """Show an error and restore the buttons to their accepted state."""
        self._status.setText(message)
        self._primary.setEnabled(True)
        self._repair.setEnabled(True)
        self._uninstall.setEnabled(True)

    def _refresh_after_change(self) -> None:
        """Re-detect state after an install or repair and relabel the buttons."""
        self._state = _detect_state()
        self._primary.setText(_primary_label(self._state))
        installed = self._state != AppState.NOT_INSTALLED
        self._repair.setVisible(installed)
        self._uninstall.setVisible(installed)
        self._uninstall.setEnabled(True)
        self._primary.setEnabled(True)
        self._repair.setEnabled(True)


class UninstallDialog(QDialog):
    """A small themed confirmation for uninstall, with a remove-settings option."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Uninstall {APP_DISPLAY_NAME}")
        self.setWindowIcon(_app_icon())
        self.setStyleSheet(_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _DIALOG_MARGIN, _DIALOG_MARGIN, _DIALOG_MARGIN, _DIALOG_MARGIN
        )
        layout.setSpacing(_BUTTON_GAP)

        message = QLabel(
            f"Remove {APP_DISPLAY_NAME} and its shortcuts from this PC? Your "
            "Elite Dangerous journal is never touched."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        self._remove_settings = QCheckBox("Also remove my o7 Debrief settings")
        layout.addWidget(self._remove_settings)

        confirm = QPushButton("Uninstall")
        confirm.setObjectName("DangerAction")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryAction")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)

    def remove_settings(self) -> bool:
        """Return whether the user asked to also remove their settings."""
        return self._remove_settings.isChecked()


# ------------------------------------------------------------------------ main


def _set_app_user_model_id() -> None:
    """Give the installer a stable taskbar identity (best effort)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "OliverErnster.o7Debrief.Installer"
        )
    except (OSError, AttributeError):
        return


def _run_uninstall_cli(args: argparse.Namespace) -> int:
    """Run the uninstall flow when invoked as the registered uninstaller."""
    app = QApplication(sys.argv)
    app.setApplicationName(f"{APP_DISPLAY_NAME} Setup")
    app.setWindowIcon(_app_icon())
    if args.quiet:
        uninstall(remove_settings=args.remove_settings)
        return 0
    dialog = UninstallDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        uninstall(remove_settings=dialog.remove_settings())
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the installer command line (used for the registered uninstaller)."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(_UNINSTALL_FLAG, dest="uninstall", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--remove-settings", action="store_true")
    return parser.parse_args(argv)


def _installer_log_path() -> Path:
    """Return the crash-log path under the per-user temporary directory."""
    return Path(tempfile.gettempdir()) / _INSTALLER_LOG_NAME


def _install_crash_logging() -> None:
    """Log unhandled exceptions to a file before the default handler runs.

    The installer is a console-disabled onefile; a crash otherwise leaves no
    visible traceback. This excepthook appends one to a known log file and
    then chains to the default handler so behaviour is unchanged.
    """
    log_path = _installer_log_path()

    def _hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("\n=== Unhandled exception ===\n")
                traceback.print_exception(exc_type, exc, tb, file=handle)
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook


def main() -> int:
    """Run the installer GUI, or the uninstall flow when so invoked."""
    _install_crash_logging()
    _set_app_user_model_id()
    args = _parse_args(sys.argv[1:])
    if args.uninstall:
        return _run_uninstall_cli(args)

    app = QApplication(sys.argv)
    app.setApplicationName(_WINDOW_TITLE)
    app.setWindowIcon(_app_icon())
    window = InstallerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
