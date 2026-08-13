"""The single seam through which the installer shells out.

Every external command the installer runs (the task list, PowerShell for
shortcuts and the deferred delete) goes through a ``CommandRunner``. Production
code uses the real runner below; tests pass a hand-written fake, so no test ever
spawns a process it did not intend to. British spelling is used in comments. No
em dashes appear anywhere.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

# Windows creation flags, read defensively so the module imports on any
# platform: they are absent from subprocess elsewhere.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0)

_POWERSHELL = "powershell"
_POWERSHELL_FLAGS = ("-NoProfile", "-NonInteractive")
_POWERSHELL_HIDDEN_FLAGS = ("-WindowStyle", "Hidden")
_POWERSHELL_COMMAND_FLAG = "-Command"

# A command that fails to start is reported with this code rather than raising,
# so every caller sees one shape of result.
FAILED_RETURNCODE = -1


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The outcome of a command: its exit code and captured standard output."""

    returncode: int
    stdout: str

    @property
    def ok(self) -> bool:
        """Return True when the command ran and reported success."""
        return self.returncode == 0


class CommandRunner(Protocol):
    """Runs a command to completion or starts one and does not wait."""

    def run(self, args: Sequence[str], *, timeout: float) -> CommandResult:
        """Run ``args`` to completion and return its result."""
        ...

    def start_detached(self, args: Sequence[str], *, cwd: str | None = None) -> bool:
        """Start ``args`` without waiting; return whether it started."""
        ...


class SubprocessRunner:
    """The real runner: subprocess with no console window and no stdin."""

    def run(self, args: Sequence[str], *, timeout: float) -> CommandResult:
        """Run a command, reporting a failure to start as a failed result."""
        try:
            completed = subprocess.run(
                list(args),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            return CommandResult(FAILED_RETURNCODE, "")
        return CommandResult(completed.returncode, completed.stdout or "")

    def start_detached(self, args: Sequence[str], *, cwd: str | None = None) -> bool:
        """Start a command detached, so it outlives this process.

        Returns whether it started. It used to swallow the failure and return
        nothing, which made a launch that never happened indistinguishable from
        one that did: the setup program reported success, closed itself and left
        the user with no application and no explanation.
        """
        try:
            subprocess.Popen(
                list(args),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW | _DETACHED,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return True


def default_runner() -> CommandRunner:
    """Return the runner used when a caller does not supply one."""
    return SubprocessRunner()


def powershell_command(script: str, *, hidden: bool = False) -> list[str]:
    """Return the argument list that runs a PowerShell script non-interactively."""
    args = [_POWERSHELL, *_POWERSHELL_FLAGS]
    if hidden:
        args.extend(_POWERSHELL_HIDDEN_FLAGS)
    args.extend([_POWERSHELL_COMMAND_FLAG, script])
    return args
