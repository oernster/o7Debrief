"""SingleInstanceLock: a per-OS-user single-instance guard for o7Debrief.

Only one o7Debrief tray should run per logged-in user. The guard holds an
exclusive OS-level lock on a per-user lock file under
``%LOCALAPPDATA%/o7Debrief`` (and an equivalent per-user location on POSIX,
so the module imports and tests cleanly off Windows). Operating-system file
locks are released automatically when the owning process exits, so a crash
or reboot never leaves a stale lock behind.

This module belongs to the ui layer and imports the standard library only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO

__all__ = ["SingleInstanceLock"]

# Application identity used for the lock directory and the lock file name.
_APP_DIR_NAME = "o7Debrief"
_LOCK_FILE_NAME = "o7debrief.lock"

# Windows path segments used only when LOCALAPPDATA is somehow absent.
_WINDOWS_APPDATA_LOCAL = ("AppData", "Local")
# POSIX cache segment used when no XDG location is provided.
_POSIX_CACHE_DIR = ".cache"

# Environment variables that name the per-user base directory.
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG_RUNTIME = "XDG_RUNTIME_DIR"
_ENV_XDG_CACHE = "XDG_CACHE_HOME"

# File open mode that both creates the file and allows seeking without
# truncating an existing one.
_LOCK_OPEN_MODE = "a+"
# Number of bytes locked at the start of the file. The region is arbitrary as
# long as every instance locks the same one; the first byte is the convention.
_LOCK_REGION_BYTES = 1
# Offset within the file at which the lock region and the pid marker begin.
_FILE_START = 0


class SingleInstanceLock:
    """Holds a per-user exclusive lock so only one instance runs at a time."""

    def __init__(self) -> None:
        self._handle: IO[str] | None = None
        self._path: Path | None = None

    def acquire(self) -> bool:
        """Try to take the lock; return True on success, False if held.

        Acquiring is idempotent within one instance: a second call while the
        lock is already held by this object returns True without re-locking.
        """
        if self._handle is not None:
            return True
        path = self._resolve_lock_path()
        self._path = path
        handle = path.open(_LOCK_OPEN_MODE)
        if self._try_lock(handle):
            self._handle = handle
            self._write_pid(handle)
            return True
        self._close_quietly(handle)
        return False

    def release(self) -> None:
        """Release the lock if held; safe to call when nothing is held."""
        handle = self._handle
        if handle is None:
            return
        self._unlock(handle)
        self._close_quietly(handle)
        self._handle = None
        self._path = None

    def _resolve_lock_path(self) -> Path:
        """Return the per-user lock file path, creating its directory."""
        root = _user_lock_dir()
        root.mkdir(parents=True, exist_ok=True)
        return root / _LOCK_FILE_NAME

    def _write_pid(self, handle: IO[str]) -> None:
        """Write this process's pid into the lock file for debugging.

        Failure to record the pid is never fatal; the lock itself is what
        provides exclusivity, not the marker.
        """
        try:
            handle.seek(_FILE_START)
            handle.truncate()
            handle.write(str(os.getpid()))
            handle.flush()
        except OSError:
            return

    @staticmethod
    def _try_lock(handle: IO[str]) -> bool:
        """Attempt a non-blocking exclusive lock on the file's first byte."""
        if os.name == "nt":
            return _windows_lock(handle)
        return _posix_lock(handle)

    @staticmethod
    def _unlock(handle: IO[str]) -> None:
        """Release the OS-level lock on a best-effort basis."""
        if os.name == "nt":
            _windows_unlock(handle)
        else:
            _posix_unlock(handle)

    @staticmethod
    def _close_quietly(handle: IO[str]) -> None:
        """Close a file handle, ignoring any secondary close error."""
        try:
            handle.close()
        except OSError:
            return


def _user_lock_dir() -> Path:
    """Return the per-user directory that should hold the lock file."""
    if os.name == "nt":
        base = os.environ.get(_ENV_LOCALAPPDATA)
        if base:
            return Path(base) / _APP_DIR_NAME
        return Path.home().joinpath(*_WINDOWS_APPDATA_LOCAL) / _APP_DIR_NAME
    runtime_dir = os.environ.get(_ENV_XDG_RUNTIME)
    if runtime_dir:
        return Path(runtime_dir) / _APP_DIR_NAME
    cache_home = os.environ.get(_ENV_XDG_CACHE)
    if cache_home:
        return Path(cache_home) / _APP_DIR_NAME
    return Path.home() / _POSIX_CACHE_DIR / _APP_DIR_NAME


def _windows_lock(handle: IO[str]) -> bool:
    """Take a non-blocking exclusive lock on Windows via msvcrt.

    ``msvcrt.locking`` locks ``nbytes`` starting at the current file position,
    so we seek to a fixed byte first. Without this, two instances opened in
    append mode would each lock from end-of-file (a different region once a pid
    has been written) and so fail to exclude one another.
    """
    import msvcrt  # type: ignore[import-not-found]

    try:
        handle.seek(_FILE_START)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, _LOCK_REGION_BYTES)
        return True
    except OSError:
        return False


def _windows_unlock(handle: IO[str]) -> None:
    """Release the Windows lock, ignoring errors."""
    import msvcrt  # type: ignore[import-not-found]

    try:
        handle.seek(_FILE_START)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, _LOCK_REGION_BYTES)
    except OSError:
        return


def _posix_lock(handle: IO[str]) -> bool:
    """Take a non-blocking exclusive lock on POSIX via fcntl.flock."""
    import fcntl  # type: ignore[import-not-found]

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _posix_unlock(handle: IO[str]) -> None:
    """Release the POSIX lock, ignoring errors."""
    import fcntl  # type: ignore[import-not-found]

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        return
