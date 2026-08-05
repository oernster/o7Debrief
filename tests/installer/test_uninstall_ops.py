"""Removing the application, its shortcuts and its registrations.

Every location is redirected, so nothing here removes a real installation.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from installer.constants import APP_DISPLAY_NAME
from installer.ops.errors import AppRunningError
from installer.ops.progress import (
    COMPLETE_PCT,
    REMOVE_FILES_PCT,
    REMOVE_SETTINGS_PCT,
)
from installer.ops.uninstall_ops import (
    DEFERRED_DELETE_ATTEMPTS,
    deferred_delete_script,
    remove_install_dir,
    schedule_delete_after_exit,
    uninstall,
)
from installer.state.registry import (
    RegistryKeys,
    installed_version,
    is_autostart_enabled,
    set_autostart,
    write_uninstall_entry,
)
from tests.installer.fakes import (
    FakeRunner,
    RecordingProgress,
    idle_result,
    running_result,
)


def test_the_deferred_script_polls_rather_than_waiting_once(tmp_path: Path) -> None:
    script = deferred_delete_script(tmp_path)

    assert str(tmp_path) in script
    assert f"-lt {DEFERRED_DELETE_ATTEMPTS}" in script
    assert "Remove-Item" in script


def test_the_deferred_script_escapes_a_quote_in_the_path() -> None:
    script = deferred_delete_script(Path("C:/it's here"))

    assert "it''s here" in script


def test_schedule_delete_after_exit_starts_a_hidden_detached_helper(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()

    schedule_delete_after_exit(tmp_path, runner)

    args, _cwd = runner.detached[0]
    assert args[0] == "powershell"
    assert "Hidden" in args


def test_remove_install_dir_does_nothing_when_it_has_already_gone(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()

    remove_install_dir(tmp_path / "absent", runner)

    assert runner.detached == []


def test_remove_install_dir_deletes_a_directory_it_is_not_running_from(
    tmp_path: Path,
) -> None:
    install_dir = tmp_path / "installed"
    install_dir.mkdir()
    (install_dir / "file.txt").write_text("x", encoding="utf-8")
    runner = FakeRunner()

    remove_install_dir(install_dir, runner)

    assert not install_dir.exists()
    assert runner.detached == []


def test_remove_install_dir_defers_when_it_holds_the_running_executable() -> None:
    """The registered uninstaller cannot delete its own running image."""
    runner = FakeRunner()

    remove_install_dir(Path(sys.executable).parent, runner)

    assert len(runner.detached) == 1


def test_uninstall_removes_shortcuts_registrations_and_files(
    scratch_keys: RegistryKeys, isolated_profile: Path, tmp_path: Path
) -> None:
    install_dir = tmp_path / "installed"
    install_dir.mkdir()
    write_uninstall_entry(
        install_dir, install_dir / "Setup.exe", "1.6.0", keys=scratch_keys
    )
    set_autostart(True, install_dir / "o7Debrief.exe", scratch_keys)
    desktop_link = isolated_profile / "Desktop" / f"{APP_DISPLAY_NAME}.lnk"
    desktop_link.write_bytes(b"lnk")
    progress = RecordingProgress()

    uninstall(
        remove_settings=False,
        progress=progress,
        runner=FakeRunner(default=idle_result()),
        keys=scratch_keys,
    )

    assert not desktop_link.exists()
    assert installed_version(scratch_keys) is None
    assert is_autostart_enabled(scratch_keys) is False
    assert not install_dir.exists()
    assert REMOVE_FILES_PCT in progress.percentages
    assert progress.percentages[-1] == COMPLETE_PCT


def test_uninstall_leaves_settings_alone_unless_asked(
    scratch_keys: RegistryKeys, isolated_profile: Path, tmp_path: Path
) -> None:
    settings = tmp_path / "settings"
    settings.mkdir()
    (settings / "preferences.json").write_text("{}", encoding="utf-8")
    progress = RecordingProgress()

    uninstall(
        remove_settings=False,
        progress=progress,
        runner=FakeRunner(default=idle_result()),
        keys=scratch_keys,
        settings_dir=settings,
    )

    assert settings.exists()
    assert REMOVE_SETTINGS_PCT not in progress.percentages


def test_uninstall_removes_settings_when_asked(
    scratch_keys: RegistryKeys, isolated_profile: Path, tmp_path: Path
) -> None:
    settings = tmp_path / "settings"
    settings.mkdir()
    (settings / "preferences.json").write_text("{}", encoding="utf-8")

    uninstall(
        remove_settings=True,
        runner=FakeRunner(default=idle_result()),
        keys=scratch_keys,
        settings_dir=settings,
    )

    assert not settings.exists()


def test_uninstall_refuses_while_the_app_is_running(
    scratch_keys: RegistryKeys, isolated_profile: Path, tmp_path: Path
) -> None:
    settings = tmp_path / "settings"
    settings.mkdir()

    with pytest.raises(AppRunningError):
        uninstall(
            remove_settings=True,
            runner=FakeRunner(default=running_result()),
            keys=scratch_keys,
            settings_dir=settings,
        )

    assert settings.exists()
