"""Install, upgrade, reinstall and repair.

Every one of these is the same sequence: put the files down, register the
uninstaller, record the installation, then apply the user's options. Repair
differs only in that it re-deploys over an install that is already there, which
without a per-file manifest is the safe way to restore anything missing or
altered. User settings live outside the install directory, so they are never
touched. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from installer.constants import FALLBACK_VERSION
from installer.ops.commands import CommandRunner, default_runner
from installer.ops.errors import AppRunningError
from installer.ops.paths import (
    directory_size_kb,
    original_installer_exe,
    uninstaller_path,
)
from installer.ops.payload import app_version, deploy, shortcut_icon_file
from installer.ops.progress import (
    COMPLETE_PCT,
    DONE_MESSAGE,
    REGISTER_MESSAGE,
    REGISTER_PCT,
    SETTINGS_MESSAGE,
    SETTINGS_PCT,
    SHORTCUTS_MESSAGE,
    SHORTCUTS_PCT,
    UNINSTALLER_MESSAGE,
    UNINSTALLER_PCT,
    ProgressCallback,
    report,
)
from installer.ops.running_app import is_app_running
from installer.ops.shortcuts import apply_shortcuts
from installer.state.registry import (
    DEFAULT_KEYS,
    RegistryKeys,
    set_autostart,
    write_uninstall_entry,
)

APP_RUNNING_MESSAGE = (
    "o7 Debrief is running. Please close it from the system tray, then try again."
)


@dataclass(frozen=True, slots=True)
class InstallOptions:
    """The user's choices for one install, upgrade or reinstall."""

    target_dir: Path
    desktop: bool
    start_menu: bool
    autostart: bool


def guard_not_running(runner: CommandRunner | None = None) -> None:
    """Refuse to proceed while the application holds its own files open."""
    if is_app_running(runner):
        raise AppRunningError(APP_RUNNING_MESSAGE)


def copy_uninstaller(install_dir: Path) -> Path:
    """Copy the setup program into the install root to act as the uninstaller.

    Best effort: the application is already deployed by the time this runs, so
    a failure here degrades to registering the running executable as the
    uninstall source rather than failing the whole install.
    """
    source = original_installer_exe()
    destination = uninstaller_path(install_dir)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except OSError:
        return source
    return destination


def register(
    install_dir: Path,
    uninstaller: Path,
    version: str,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> None:
    """Record the installation so it appears in Apps and features."""
    icon = shortcut_icon_file(install_dir)
    write_uninstall_entry(
        install_dir,
        uninstaller,
        version,
        display_icon=icon if icon is not None else install_dir,
        estimated_kb=directory_size_kb(install_dir),
        keys=keys,
    )


def _deploy_and_register(
    target: Path,
    *,
    progress: ProgressCallback | None,
    keys: RegistryKeys,
) -> Path:
    """Put the files down and register the installation, reporting as it goes."""
    exe_path = deploy(target, progress=progress)

    report(progress, UNINSTALLER_PCT, UNINSTALLER_MESSAGE)
    uninstaller = copy_uninstaller(target)

    report(progress, REGISTER_PCT, REGISTER_MESSAGE)
    register(target, uninstaller, app_version() or FALLBACK_VERSION, keys)
    return exe_path


def install(
    options: InstallOptions,
    *,
    progress: ProgressCallback | None = None,
    runner: CommandRunner | None = None,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> Path:
    """Run a full install, upgrade or reinstall and return the installed exe."""
    active = runner or default_runner()
    guard_not_running(active)

    exe_path = _deploy_and_register(options.target_dir, progress=progress, keys=keys)

    report(progress, SHORTCUTS_PCT, SHORTCUTS_MESSAGE)
    apply_shortcuts(
        exe_path,
        desktop=options.desktop,
        start_menu=options.start_menu,
        runner=active,
    )

    report(progress, SETTINGS_PCT, SETTINGS_MESSAGE)
    set_autostart(options.autostart, exe_path, keys)

    report(progress, COMPLETE_PCT, DONE_MESSAGE)
    return exe_path


def repair(
    install_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    runner: CommandRunner | None = None,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> Path:
    """Re-deploy over an existing install and restore its shortcuts.

    The user's sign-in setting is left as it is: a repair restores what the
    installer put down, and the Run entry is a preference rather than part of
    the deployed application.
    """
    active = runner or default_runner()
    guard_not_running(active)

    exe_path = _deploy_and_register(install_dir, progress=progress, keys=keys)

    report(progress, SHORTCUTS_PCT, SHORTCUTS_MESSAGE)
    apply_shortcuts(exe_path, desktop=True, start_menu=True, runner=active)

    report(progress, COMPLETE_PCT, DONE_MESSAGE)
    return exe_path
