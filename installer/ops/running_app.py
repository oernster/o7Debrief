"""Detecting, closing and launching the installed application.

An install replaces every file in the bundle, so it must not run while the
application holds its own executable open. The setup program therefore detects a
running instance and offers to end it, rather than only telling the user to do
it themselves.

Ending it is a forced termination rather than a polite close request. o7Debrief
intercepts a window close to minimise to the system tray, so asking its window
to close leaves the process alive and the file still locked. British spelling is
used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from installer.constants import EXE_NAME
from installer.ops.commands import CommandRunner, default_runner
from installer.ops.errors import AppStillRunningError

_TASKLIST = "tasklist"
_TASKLIST_FILTER = "/fi"
_TASKLIST_NO_HEADER = "/nh"
_TASKKILL = "taskkill"
_TASKKILL_IMAGE = "/im"
_TASKKILL_FORCE = "/f"
_TASKKILL_TREE = "/t"

TASKLIST_TIMEOUT_S = 10.0
TASKKILL_TIMEOUT_S = 15.0

# How long to wait for the process to disappear after it has been ended, so a
# stuck process cannot hang the setup program indefinitely.
CLOSE_POLL_ATTEMPTS = 50
CLOSE_POLL_INTERVAL_S = 0.1

# Injected so the wait can be exercised without spending real time.
Sleeper = Callable[[float], None]


def is_app_running(runner: CommandRunner | None = None) -> bool:
    """Return True when the application appears in the task list.

    Best effort: a task list that cannot be read reports not running, so a
    transient failure never blocks a legitimate install.
    """
    active = runner or default_runner()
    result = active.run(
        [_TASKLIST, _TASKLIST_FILTER, f"imagename eq {EXE_NAME}", _TASKLIST_NO_HEADER],
        timeout=TASKLIST_TIMEOUT_S,
    )
    return EXE_NAME.lower() in result.stdout.lower()


def close_running_app(
    runner: CommandRunner | None = None,
    *,
    sleep: Sleeper | None = None,
) -> None:
    """End every running instance and wait for its file lock to release.

    Raises AppStillRunningError when the application is still present after the
    wait, so the caller does not proceed onto a locked file.
    """
    active = runner or default_runner()
    wait = sleep or time.sleep
    active.run(
        [_TASKKILL, _TASKKILL_FORCE, _TASKKILL_TREE, _TASKKILL_IMAGE, EXE_NAME],
        timeout=TASKKILL_TIMEOUT_S,
    )
    for _ in range(CLOSE_POLL_ATTEMPTS):
        if not is_app_running(active):
            return
        wait(CLOSE_POLL_INTERVAL_S)
    if is_app_running(active):
        raise AppStillRunningError(
            "o7 Debrief could not be closed. Please close it from the system "
            "tray, then try again."
        )


def launch(exe_path: Path, runner: CommandRunner | None = None) -> None:
    """Start the installed application detached, so it outlives the installer."""
    active = runner or default_runner()
    active.start_detached([str(exe_path)], cwd=str(exe_path.parent))
