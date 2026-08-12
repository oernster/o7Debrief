"""Tests for the installer's step log and its installed-version subtitle.

Both exist because of the same reported failure: the setup program appeared to
do nothing and the application never started. The log is what makes a repeat of
that answerable from the machine instead of guessed at, and the subtitle is what
tells the user which version they are actually replacing.
"""

from __future__ import annotations

from pathlib import Path

from installer.shared.logging_setup import (
    installer_log_path,
    log_step,
)
from installer.state.model import InstallState, StateSnapshot
from installer.ui._main_window_build import (
    INSTALLED_SUBTITLE_UNKNOWN,
    WELCOME_SUBTITLE,
    subtitle_text,
)


def _snapshot(state: str, installed_version: str) -> StateSnapshot:
    return StateSnapshot(
        state=state,
        bundled_version="2.2.0",
        installed_version=installed_version,
        install_dir=Path("C:/somewhere"),
        autostart=False,
    )


def test_a_step_is_appended_with_a_timestamp(tmp_path: Path) -> None:
    log = tmp_path / "installer.log"

    log_step("first step", log)
    log_step("second step", log)

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(" first step")
    assert lines[1].endswith(" second step")
    # The stamp is an ISO date and time, so the order of events is recoverable.
    assert lines[0].startswith("20")
    assert "T" in lines[0].split(" ")[0]


def test_a_log_that_cannot_be_written_is_never_fatal(tmp_path: Path) -> None:
    """Diagnostics must never become the reason an install fails."""
    unwritable = tmp_path / "no-such-directory" / "installer.log"

    log_step("a step", unwritable)

    assert not unwritable.exists()


def test_the_default_log_path_is_the_per_user_temporary_directory() -> None:
    assert installer_log_path().name == "o7debrief-installer.log"


def test_the_subtitle_names_the_installed_version_before_an_upgrade() -> None:
    """The header states the version installed; this states the one replaced."""
    text = subtitle_text(_snapshot(InstallState.UPGRADE, "2.1.0"))

    assert "2.1.0" in text


def test_the_subtitle_names_the_version_on_a_reinstall_too() -> None:
    assert "2.2.0" in subtitle_text(_snapshot(InstallState.REINSTALL, "2.2.0"))


def test_an_installed_version_that_was_never_read_is_not_printed_as_nothing() -> None:
    """A registration can exist with no recorded version, which is not a version."""
    text = subtitle_text(_snapshot(InstallState.REINSTALL, ""))

    assert text == INSTALLED_SUBTITLE_UNKNOWN


def test_a_fresh_install_is_welcomed_rather_than_told_what_it_replaces() -> None:
    text = subtitle_text(_snapshot(InstallState.NOT_INSTALLED, ""))

    assert text == WELCOME_SUBTITLE
