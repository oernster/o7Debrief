"""Progress reporting and the single seam through which the installer shells out.

The runner tests use real commands that do nothing (``cmd /c``), which exercises
the production subprocess path without any mocking library. British spelling is
used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from installer.ops.commands import (
    FAILED_RETURNCODE,
    CommandResult,
    SubprocessRunner,
    default_runner,
    powershell_command,
)
from installer.ops.progress import (
    COMPLETE_PCT,
    EXTRACT_END_PCT,
    EXTRACT_START_PCT,
    MINIMUM_PCT,
    report,
    scaled,
)
from tests.installer.fakes import RecordingProgress

_MISSING_COMMAND = ["o7debrief-no-such-command-exists"]
_TIMEOUT_S = 10.0


def test_report_does_nothing_without_a_reporter() -> None:
    report(None, COMPLETE_PCT, "Done.")


def test_report_forwards_one_update() -> None:
    progress = RecordingProgress()

    report(progress, EXTRACT_START_PCT, "Extracting files...")

    assert progress.updates == [(EXTRACT_START_PCT, "Extracting files...")]


def test_scaled_maps_progress_into_the_phase_span() -> None:
    half = 50
    whole = 100

    assert scaled(MINIMUM_PCT, whole, EXTRACT_START_PCT, EXTRACT_END_PCT) == (
        EXTRACT_START_PCT
    )
    assert scaled(whole, whole, EXTRACT_START_PCT, EXTRACT_END_PCT) == EXTRACT_END_PCT
    assert scaled(half, whole, EXTRACT_START_PCT, EXTRACT_END_PCT) == 30


def test_scaled_reports_the_end_of_a_phase_with_nothing_to_do() -> None:
    assert scaled(MINIMUM_PCT, MINIMUM_PCT, EXTRACT_START_PCT, EXTRACT_END_PCT) == (
        EXTRACT_END_PCT
    )


def test_a_result_knows_whether_it_succeeded() -> None:
    assert CommandResult(0, "").ok is True
    assert CommandResult(1, "").ok is False


def test_default_runner_is_the_subprocess_runner() -> None:
    assert isinstance(default_runner(), SubprocessRunner)


def test_powershell_command_runs_a_script_non_interactively() -> None:
    args = powershell_command("$x = 1")

    assert args[0] == "powershell"
    assert "-NoProfile" in args
    assert "-NonInteractive" in args
    assert args[-2:] == ["-Command", "$x = 1"]


def test_powershell_command_can_hide_its_window() -> None:
    args = powershell_command("$x = 1", hidden=True)

    assert "-WindowStyle" in args
    assert "Hidden" in args


def test_the_runner_captures_output_from_a_real_command() -> None:
    result = SubprocessRunner().run(["cmd", "/c", "echo", "hello"], timeout=_TIMEOUT_S)

    assert result.ok is True
    assert "hello" in result.stdout


def test_the_runner_reports_a_command_that_cannot_start() -> None:
    result = SubprocessRunner().run(_MISSING_COMMAND, timeout=_TIMEOUT_S)

    assert result.returncode == FAILED_RETURNCODE
    assert result.ok is False


def test_the_runner_starts_a_detached_command() -> None:
    SubprocessRunner().start_detached(["cmd", "/c", "exit"])


def test_the_runner_is_silent_when_a_detached_command_cannot_start() -> None:
    SubprocessRunner().start_detached(_MISSING_COMMAND)
