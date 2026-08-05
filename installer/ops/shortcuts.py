"""Creating and removing the per-user Desktop and Start Menu shortcuts.

Shortcuts are written through the Windows scripting host rather than through
COM bindings, so the compiled setup program pulls in nothing beyond PySide6 and
the standard library. Every step is best effort: a shortcut that cannot be
written must not fail an otherwise complete install. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from installer.ops.commands import (
    CommandRunner,
    default_runner,
    powershell_command,
)
from installer.ops.paths import desktop_link, start_menu_link
from installer.ops.payload import shortcut_icon_file

SHORTCUT_TIMEOUT_S = 15.0

_SHELL_OBJECT = "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{link}'); "
_TARGET_CLAUSE = "$s.TargetPath = '{target}'; "
_WORKING_CLAUSE = "$s.WorkingDirectory = '{working}'; "
_ICON_CLAUSE = "$s.IconLocation = '{icon}'; "
_SAVE_CLAUSE = "$s.Save()"


def shortcut_script(exe_path: Path, link: Path, icon: Path | None) -> str:
    """Return the scripting-host command that writes one shortcut."""
    script = (
        _SHELL_OBJECT.format(link=link)
        + _TARGET_CLAUSE.format(target=exe_path)
        + _WORKING_CLAUSE.format(working=exe_path.parent)
    )
    if icon is not None:
        script += _ICON_CLAUSE.format(icon=icon)
    return script + _SAVE_CLAUSE


def create_shortcut(
    exe_path: Path,
    link: Path,
    *,
    runner: CommandRunner | None = None,
) -> None:
    """Write a shortcut to the installed executable, with the app icon."""
    active = runner or default_runner()
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    icon = shortcut_icon_file(exe_path.parent)
    script = shortcut_script(exe_path, link, icon)
    active.run(powershell_command(script), timeout=SHORTCUT_TIMEOUT_S)


def remove_shortcut(link: Path | None) -> None:
    """Delete a shortcut file if it is present."""
    if link is None:
        return
    try:
        link.unlink(missing_ok=True)
    except OSError:
        return


def apply_shortcuts(
    exe_path: Path,
    *,
    desktop: bool,
    start_menu: bool,
    runner: CommandRunner | None = None,
) -> None:
    """Create or remove the shortcuts so they match the chosen options."""
    active = runner or default_runner()

    link = desktop_link()
    if desktop:
        create_shortcut(exe_path, link, runner=active)
    else:
        remove_shortcut(link)

    start_link = start_menu_link()
    if start_menu and start_link is not None:
        create_shortcut(exe_path, start_link, runner=active)
    else:
        remove_shortcut(start_link)


def remove_all_shortcuts() -> None:
    """Delete both shortcuts, used on uninstall."""
    remove_shortcut(desktop_link())
    remove_shortcut(start_menu_link())
