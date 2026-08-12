"""Crash diagnostics for a console-disabled setup program.

The installer is compiled as a onefile with its console disabled, so a crash
otherwise leaves the user with a window that vanishes and no traceback to send
back. The hook appends one to a known file under the temporary directory and
then chains to the default handler, so behaviour is otherwise unchanged. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import faulthandler
import sys
import tempfile
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

from installer.constants import INSTALLER_LOG_NAME

_HEADER = "\n=== Unhandled exception ===\n"
# Format of one step line: an ISO timestamp, then the message.
_STEP_LINE = "{stamp} {message}\n"
_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


def installer_log_path() -> Path:
    """Return the crash-log path under the per-user temporary directory."""
    return Path(tempfile.gettempdir()) / INSTALLER_LOG_NAME


def write_crash(log_path: Path, exc_type, exc, tb: TracebackType | None) -> None:
    """Append one traceback to the crash log, ignoring a log that cannot open."""
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(_HEADER)
            traceback.print_exception(exc_type, exc, tb, file=handle)
    except OSError:
        return


def log_step(message: str, log_path: Path | None = None) -> None:
    """Append one timestamped step to the installer log, ignoring failure.

    A crash log alone was not enough. The setup program's worst failures are
    the quiet ones: an install that reports success and launches nothing, or a
    window that closes with the work half done. Neither raises, so neither
    leaves a traceback, and by the time the user says something went wrong the
    machine has usually been changed again and the evidence is gone. Recording
    each step as it happens is what makes the next such report answerable.

    Logging is best effort by design: a log that cannot be written must never
    become a reason the install itself fails.
    """
    path = log_path if log_path is not None else installer_log_path()
    stamp = datetime.now(timezone.utc).strftime(_STAMP_FORMAT)
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_STEP_LINE.format(stamp=stamp, message=message))
    except OSError:
        return


def install_crash_logging(log_path: Path | None = None) -> Path:
    """Log unhandled exceptions to a file before the default handler runs."""
    path = log_path if log_path is not None else installer_log_path()

    def _hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        write_crash(path, exc_type, exc, tb)
        sys.__excepthook__(exc_type, exc, tb)

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        """Log a worker-thread failure, which ``sys.excepthook`` never sees."""
        write_crash(path, args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    _enable_native_crash_dump(path)
    return path


def _enable_native_crash_dump(path: Path) -> None:
    """Write a native traceback if the process dies below the Python level.

    An access violation or an abort inside Qt raises no Python exception, so
    neither hook above ever runs and the process simply vanishes. That is the
    exact signature of the failure this exists for: a setup program that
    disappeared with no traceback, no log line and no Windows error report. The
    handle is deliberately left open for the life of the process, because the
    whole point is that it is still usable at the moment of the crash.
    """
    try:
        handle = path.open("a", encoding="utf-8")
    except OSError:
        return
    try:
        faulthandler.enable(file=handle, all_threads=True)
    except (OSError, ValueError, RuntimeError):
        handle.close()
