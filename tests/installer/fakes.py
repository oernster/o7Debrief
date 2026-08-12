"""Hand-written test doubles for the installer's external seams.

No mocking library is used anywhere in this suite. The installer shells out
through a single CommandRunner protocol, so a recording fake of that protocol is
all that is needed to exercise every command path without spawning a process.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from collections.abc import Sequence

from installer.ops.commands import CommandResult


class FakeRunner:
    """Records every command it is given and replays scripted results."""

    def __init__(
        self,
        results: Sequence[CommandResult] | None = None,
        default: CommandResult | None = None,
        *,
        detached_starts: bool = True,
    ) -> None:
        self.calls: list[tuple[list[str], float]] = []
        self.detached: list[tuple[list[str], str | None]] = []
        # Whether a detached start is reported as having succeeded, so a launch
        # that the operating system refuses can be exercised.
        self.detached_starts = detached_starts
        self._results = list(results or ())
        self._default = default if default is not None else CommandResult(0, "")

    def run(self, args: Sequence[str], *, timeout: float) -> CommandResult:
        """Record the command and return the next scripted result."""
        self.calls.append((list(args), timeout))
        if self._results:
            return self._results.pop(0)
        return self._default

    def start_detached(self, args: Sequence[str], *, cwd: str | None = None) -> bool:
        """Record a detached start and report whether it was allowed to start."""
        self.detached.append((list(args), cwd))
        return self.detached_starts

    @property
    def commands(self) -> list[list[str]]:
        """Return just the argument lists of the commands that were run."""
        return [args for args, _ in self.calls]


class RecordingProgress:
    """Collects the progress updates an operation reports."""

    def __init__(self) -> None:
        self.updates: list[tuple[int, str]] = []

    def __call__(self, pct: int, message: str) -> None:
        """Record one update."""
        self.updates.append((pct, message))

    @property
    def percentages(self) -> list[int]:
        """Return the reported percentages in order."""
        return [pct for pct, _ in self.updates]


def running_result() -> CommandResult:
    """Return a task-list result that reports the application as running."""
    from installer.constants import EXE_NAME

    return CommandResult(0, f"{EXE_NAME}  1234 Console  1  50,000 K")


def idle_result() -> CommandResult:
    """Return a task-list result that reports nothing running."""
    return CommandResult(0, "INFO: No tasks are running.")
