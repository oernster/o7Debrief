"""The per-user locations the installer reads and writes.

Everything lives under the current user's profile, so no step of the install
needs administrator rights. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from installer.constants import (
    APP_DISPLAY_NAME,
    APP_NAME,
    DESKTOP_DIR_NAME,
    ENV_APPDATA,
    ENV_LOCALAPPDATA,
    EXE_NAME,
    EXE_SUFFIX,
    NUITKA_ONEFILE_ENV,
    PROGRAMS_DIR_NAME,
    SHORTCUT_EXT,
    START_MENU_SUBPATH,
    STATE_DIR_NAME,
    UNINSTALLER_NAME,
    UNINSTALLER_SUBDIR,
)

_LOCAL_APPDATA_FALLBACK = ("AppData", "Local")


def _local_appdata() -> Path:
    """Return %LOCALAPPDATA%, falling back to its conventional location."""
    base = os.environ.get(ENV_LOCALAPPDATA)
    if base:
        return Path(base)
    return Path.home().joinpath(*_LOCAL_APPDATA_FALLBACK)


def install_target() -> Path:
    """Return the per-user install directory for the application."""
    return _local_appdata() / PROGRAMS_DIR_NAME / APP_NAME


def state_dir() -> Path:
    """Return the per-user state directory the app writes (settings, ranks)."""
    return _local_appdata() / STATE_DIR_NAME


def installed_exe(install_dir: Path) -> Path:
    """Return the application executable inside an install directory."""
    return install_dir / EXE_NAME


def uninstaller_path(install_dir: Path) -> Path:
    """Return where the registered uninstaller copy lives under an install."""
    return install_dir / UNINSTALLER_SUBDIR / UNINSTALLER_NAME


def desktop_link() -> Path:
    """Return the per-user Desktop shortcut path."""
    return Path.home() / DESKTOP_DIR_NAME / f"{APP_DISPLAY_NAME}{SHORTCUT_EXT}"


def start_menu_link() -> Path | None:
    """Return the Start Menu shortcut path, or None when APPDATA is unset."""
    appdata = os.environ.get(ENV_APPDATA)
    if not appdata:
        return None
    programs = Path(appdata).joinpath(*START_MENU_SUBPATH)
    return programs / f"{APP_DISPLAY_NAME}{SHORTCUT_EXT}"


def launcher_candidates() -> tuple[str, ...]:
    """Return the places the original launcher's path may be found, in order."""
    return (
        os.environ.get(NUITKA_ONEFILE_ENV, ""),
        sys.argv[0] if sys.argv else "",
    )


def original_installer_exe(
    candidates: tuple[str, ...] | None = None,
    temp_root: Path | None = None,
) -> Path:
    """Return the setup executable the user actually launched.

    Under a Nuitka onefile build ``sys.executable`` is the unpacked temporary
    bootstrap rather than the launcher, and registering that as the uninstaller
    would record a path that disappears when the process exits. The real
    launcher is exposed through NUITKA_ONEFILE_BINARY and as ``sys.argv[0]``,
    so those are preferred and ``sys.executable`` is the last resort.
    """
    root = (
        temp_root.resolve()
        if temp_root is not None
        else Path(tempfile.gettempdir()).resolve()
    )
    sources = candidates if candidates is not None else launcher_candidates()
    for raw in sources:
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except OSError:  # pragma: no cover
            # Defensive: resolve() does not raise for any malformed value this
            # environment can produce, so no test can reach this. A candidate
            # that cannot be resolved is skipped rather than allowed to fail
            # the install.
            continue
        if path.suffix.lower() != EXE_SUFFIX or not path.is_file():
            continue
        if path == root or root in path.parents:
            continue
        return path
    return Path(sys.executable)


def running_from_inside(install_dir: Path) -> bool:
    """Return True when this process's executable lives inside ``install_dir``.

    A path that cannot be resolved answers True, which is the safe direction:
    the caller then defers the deletion instead of attempting it in place.

    The literal path is tested as well as the resolved one. ``resolve()``
    follows symlinks, so an interpreter that is a symlink out of the directory
    (a Linux venv's ``bin/python``, which points at the system Python) resolves
    to somewhere else entirely and the directory it is actually running from
    then looks unrelated. The caller's next act is an unconditional rmtree, so
    a false answer here deletes a live directory; either path matching is
    enough to defer.
    """
    candidates = []
    try:
        candidates.append((Path(sys.executable), install_dir))
        candidates.append((Path(sys.executable).resolve(), install_dir.resolve()))
    except OSError:  # pragma: no cover
        # Defensive: resolve() does not raise for any path this environment can
        # produce, so no test can reach this. It is kept because answering True
        # defers the deletion, which is the safe direction.
        return True
    return any(
        running == root or root in running.parents for running, root in candidates
    )


def directory_size_kb(path: Path) -> int | None:
    """Return the total size of a directory in KiB, or None when unreadable.

    A path that is not a directory walks to nothing and reports zero, which is
    the honest answer for an install that is not there.
    """
    kib = 1024
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:  # pragma: no cover
        # Defensive: the walk swallows a missing or non-directory path, so this
        # fires only if a file vanishes between being listed and being sized.
        return None
    return total // kib
