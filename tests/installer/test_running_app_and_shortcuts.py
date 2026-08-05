"""Detecting and closing the running application, and writing its shortcuts.

Every external command is observed through the recording runner, so no test
ends a real process or writes a real shortcut. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.constants import APP_DISPLAY_NAME, ENV_APPDATA, EXE_NAME
from installer.ops.errors import AppStillRunningError
from installer.ops.running_app import (
    CLOSE_POLL_ATTEMPTS,
    close_running_app,
    is_app_running,
    launch,
)
from installer.ops.shortcuts import (
    apply_shortcuts,
    create_shortcut,
    remove_all_shortcuts,
    remove_shortcut,
    shortcut_script,
)
from tests.installer.fakes import FakeRunner, idle_result, running_result


def _sleeps() -> tuple[list[float], object]:
    """Return a recorder and the sleeper that feeds it, so no test waits."""
    recorded: list[float] = []
    return recorded, recorded.append


def test_is_app_running_reads_the_task_list() -> None:
    runner = FakeRunner([running_result()])

    assert is_app_running(runner) is True
    assert runner.commands[0][0] == "tasklist"
    assert f"imagename eq {EXE_NAME}" in runner.commands[0]


def test_is_app_running_is_false_when_nothing_matches() -> None:
    assert is_app_running(FakeRunner([idle_result()])) is False


def test_close_running_app_ends_the_process_and_waits_for_the_lock() -> None:
    runner = FakeRunner([running_result(), running_result(), idle_result()])
    recorded, sleeper = _sleeps()

    close_running_app(runner, sleep=sleeper)

    assert runner.commands[0][0] == "taskkill"
    assert EXE_NAME in runner.commands[0]
    assert len(recorded) == 1


def test_close_running_app_returns_at_once_when_it_has_already_gone() -> None:
    runner = FakeRunner(default=idle_result())
    recorded, sleeper = _sleeps()

    close_running_app(runner, sleep=sleeper)

    assert recorded == []


def test_close_running_app_reports_a_process_that_will_not_end() -> None:
    runner = FakeRunner(default=running_result())
    recorded, sleeper = _sleeps()

    with pytest.raises(AppStillRunningError):
        close_running_app(runner, sleep=sleeper)

    assert len(recorded) == CLOSE_POLL_ATTEMPTS


def test_close_running_app_accepts_a_process_that_goes_on_the_final_check() -> None:
    """The last wait is followed by one more look, so a late exit still counts."""
    scripted = [idle_result()] + [running_result()] * CLOSE_POLL_ATTEMPTS
    runner = FakeRunner(scripted, default=idle_result())
    _recorded, sleeper = _sleeps()

    close_running_app(runner, sleep=sleeper)


def test_launch_starts_the_app_detached_in_its_own_directory(tmp_path: Path) -> None:
    runner = FakeRunner()
    exe = tmp_path / EXE_NAME

    launch(exe, runner)

    assert runner.detached == [([str(exe)], str(tmp_path))]


def test_the_shortcut_script_sets_target_and_working_directory(tmp_path: Path) -> None:
    exe = tmp_path / EXE_NAME
    link = tmp_path / "link.lnk"

    script = shortcut_script(exe, link, None)

    assert str(exe) in script
    assert str(tmp_path) in script
    assert "IconLocation" not in script
    assert script.endswith("$s.Save()")


def test_the_shortcut_script_carries_the_icon_when_there_is_one(
    tmp_path: Path,
) -> None:
    icon = tmp_path / "o7debrief.ico"

    script = shortcut_script(tmp_path / EXE_NAME, tmp_path / "link.lnk", icon)

    assert f"$s.IconLocation = '{icon}'" in script


def test_create_shortcut_runs_the_scripting_host(tmp_path: Path) -> None:
    runner = FakeRunner()
    exe = tmp_path / EXE_NAME
    link = tmp_path / "links" / "o7 Debrief.lnk"

    create_shortcut(exe, link, runner=runner)

    assert link.parent.is_dir()
    assert runner.commands[0][0] == "powershell"


def test_create_shortcut_uses_the_installed_icon_when_present(tmp_path: Path) -> None:
    runner = FakeRunner()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "o7debrief.ico").write_bytes(b"ico")

    create_shortcut(tmp_path / EXE_NAME, tmp_path / "link.lnk", runner=runner)

    assert "IconLocation" in runner.commands[0][-1]


def test_create_shortcut_is_silent_when_the_folder_cannot_be_made(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")

    create_shortcut(tmp_path / EXE_NAME, blocker / "link.lnk", runner=runner)

    assert runner.commands == []


def test_remove_shortcut_deletes_the_file(tmp_path: Path) -> None:
    link = tmp_path / "link.lnk"
    link.write_bytes(b"lnk")

    remove_shortcut(link)

    assert not link.exists()


def test_remove_shortcut_accepts_no_shortcut_at_all() -> None:
    remove_shortcut(None)


def test_remove_shortcut_is_silent_when_the_path_cannot_be_removed(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "a-directory"
    directory.mkdir()

    remove_shortcut(directory)

    assert directory.is_dir()


def test_apply_shortcuts_creates_both_when_both_are_wanted(
    isolated_profile: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()

    apply_shortcuts(tmp_path / EXE_NAME, desktop=True, start_menu=True, runner=runner)

    assert len(runner.commands) == 2


def test_apply_shortcuts_removes_the_ones_that_are_not_wanted(
    isolated_profile: Path, tmp_path: Path
) -> None:
    desktop_link = isolated_profile / "Desktop" / f"{APP_DISPLAY_NAME}.lnk"
    desktop_link.write_bytes(b"lnk")
    runner = FakeRunner()

    apply_shortcuts(tmp_path / EXE_NAME, desktop=False, start_menu=False, runner=runner)

    assert not desktop_link.exists()
    assert runner.commands == []


def test_apply_shortcuts_skips_the_start_menu_without_appdata(
    monkeypatch: pytest.MonkeyPatch, isolated_profile: Path, tmp_path: Path
) -> None:
    monkeypatch.delenv(ENV_APPDATA, raising=False)
    runner = FakeRunner()

    apply_shortcuts(tmp_path / EXE_NAME, desktop=True, start_menu=True, runner=runner)

    assert len(runner.commands) == 1


def test_remove_all_shortcuts_deletes_both(isolated_profile: Path) -> None:
    desktop_link = isolated_profile / "Desktop" / f"{APP_DISPLAY_NAME}.lnk"
    desktop_link.write_bytes(b"lnk")

    remove_all_shortcuts()

    assert not desktop_link.exists()
