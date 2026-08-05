"""Removing the application, its shortcuts and its registrations.

The registered uninstaller is a copy of the setup program living inside the
directory it has to remove, so it cannot delete its own running executable. The
last step therefore hands the deletion to a detached helper that waits for the
lock to release rather than racing a fixed delay. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from installer.ops.commands import (
    CommandRunner,
    default_runner,
    powershell_command,
)
from installer.ops.install_ops import guard_not_running
from installer.ops.paths import install_target, running_from_inside, state_dir
from installer.ops.progress import (
    COMPLETE_PCT,
    DONE_MESSAGE,
    REMOVE_FILES_MESSAGE,
    REMOVE_FILES_PCT,
    REMOVE_REGISTRY_MESSAGE,
    REMOVE_REGISTRY_PCT,
    REMOVE_SETTINGS_MESSAGE,
    REMOVE_SETTINGS_PCT,
    REMOVE_SHORTCUTS_MESSAGE,
    REMOVE_SHORTCUTS_PCT,
    ProgressCallback,
    report,
)
from installer.ops.shortcuts import remove_all_shortcuts
from installer.state.registry import (
    DEFAULT_KEYS,
    RegistryKeys,
    delete_toast_identity,
    delete_uninstall_entry,
    installed_location,
    set_autostart,
)

# The detached helper polls rather than sleeping once, so the directory goes as
# soon as the lock on the running uninstaller is released.
DEFERRED_DELETE_ATTEMPTS = 30
DEFERRED_DELETE_INTERVAL_MS = 500

_QUOTE = "'"
_ESCAPED_QUOTE = "''"


def deferred_delete_script(install_dir: Path) -> str:
    """Return the script that removes the directory once the lock is released."""
    escaped = str(install_dir).replace(_QUOTE, _ESCAPED_QUOTE)
    return (
        f"$d = '{escaped}'; "
        f"for ($i = 0; $i -lt {DEFERRED_DELETE_ATTEMPTS}; $i++) {{ "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        "Remove-Item -LiteralPath $d -Recurse -Force "
        "-ErrorAction SilentlyContinue; "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        f"Start-Sleep -Milliseconds {DEFERRED_DELETE_INTERVAL_MS} "
        "}"
    )


def schedule_delete_after_exit(
    install_dir: Path,
    runner: CommandRunner | None = None,
) -> None:
    """Delete the install directory from a detached helper once this exits."""
    active = runner or default_runner()
    script = deferred_delete_script(install_dir)
    active.start_detached(powershell_command(script, hidden=True))


def remove_install_dir(
    install_dir: Path,
    runner: CommandRunner | None = None,
) -> None:
    """Remove the install directory, deferring when it holds the running exe."""
    if not install_dir.exists():
        return
    if running_from_inside(install_dir):
        schedule_delete_after_exit(install_dir, runner)
        return
    shutil.rmtree(install_dir, ignore_errors=True)


def uninstall(
    *,
    remove_settings: bool,
    progress: ProgressCallback | None = None,
    runner: CommandRunner | None = None,
    keys: RegistryKeys = DEFAULT_KEYS,
    settings_dir: Path | None = None,
) -> None:
    """Remove shortcuts, registrations, optionally settings, then the files."""
    active = runner or default_runner()
    guard_not_running(active)
    install_dir = installed_location(keys) or install_target()
    settings = settings_dir if settings_dir is not None else state_dir()

    report(progress, REMOVE_SHORTCUTS_PCT, REMOVE_SHORTCUTS_MESSAGE)
    remove_all_shortcuts()
    set_autostart(False, Path(), keys)

    report(progress, REMOVE_REGISTRY_PCT, REMOVE_REGISTRY_MESSAGE)
    delete_uninstall_entry(keys)
    delete_toast_identity(keys)

    if remove_settings:
        report(progress, REMOVE_SETTINGS_PCT, REMOVE_SETTINGS_MESSAGE)
        shutil.rmtree(settings, ignore_errors=True)

    report(progress, REMOVE_FILES_PCT, REMOVE_FILES_MESSAGE)
    remove_install_dir(install_dir, active)

    report(progress, COMPLETE_PCT, DONE_MESSAGE)
