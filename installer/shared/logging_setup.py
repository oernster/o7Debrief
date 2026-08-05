"""Crash diagnostics for a console-disabled setup program.

The installer is compiled as a onefile with its console disabled, so a crash
otherwise leaves the user with a window that vanishes and no traceback to send
back. The hook appends one to a known file under the temporary directory and
then chains to the default handler, so behaviour is otherwise unchanged. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path
from types import TracebackType

from installer.constants import INSTALLER_LOG_NAME

_HEADER = "\n=== Unhandled exception ===\n"


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

    sys.excepthook = _hook
    return path
