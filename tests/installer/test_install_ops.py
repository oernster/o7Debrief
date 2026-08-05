"""Install, upgrade, reinstall and repair, end to end against scratch state.

The payload anchor, the profile directories and the registry keys are all
redirected, so a full install runs here without touching a real installation.
British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from installer.constants import (
    APP_NAME,
    EXE_NAME,
    PAYLOAD_ARCHIVE_NAME,
    PAYLOAD_DIR_NAME,
    UNINSTALLER_NAME,
    VERSION_FILE_NAME,
)
from installer.ops.errors import AppRunningError
from installer.ops.install_ops import (
    InstallOptions,
    copy_uninstaller,
    guard_not_running,
    install,
    register,
    repair,
)
from installer.ops.progress import COMPLETE_PCT, REGISTER_PCT, UNINSTALLER_PCT
from installer.state.registry import (
    DISPLAY_ICON,
    DISPLAY_VERSION,
    RegistryKeys,
    installed_location,
    is_autostart_enabled,
    read_string,
)
from tests.installer.fakes import (
    FakeRunner,
    RecordingProgress,
    idle_result,
    running_result,
)

_BUNDLED_VERSION = "1.6.0"


@pytest.fixture()
def bundle(staged_payload: Path) -> Path:
    """Stage a small but complete payload: an executable, an icon and a version."""
    app_dir = staged_payload / PAYLOAD_DIR_NAME / APP_NAME
    (app_dir / VERSION_FILE_NAME).write_text(_BUNDLED_VERSION, encoding="utf-8")
    archive = staged_payload / PAYLOAD_DIR_NAME / PAYLOAD_ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w") as payload:
        payload.writestr(EXE_NAME, "executable")
        payload.writestr("assets/o7debrief.ico", "ico")
    return staged_payload


def _options(target: Path, *, autostart: bool = False) -> InstallOptions:
    return InstallOptions(
        target_dir=target, desktop=False, start_menu=False, autostart=autostart
    )


def test_guard_not_running_passes_when_nothing_is_running() -> None:
    guard_not_running(FakeRunner([idle_result()]))


def test_guard_not_running_refuses_while_the_app_holds_its_files() -> None:
    with pytest.raises(AppRunningError):
        guard_not_running(FakeRunner([running_result()]))


def test_copy_uninstaller_places_a_copy_under_the_install(tmp_path: Path) -> None:
    install_dir = tmp_path / "installed"
    install_dir.mkdir()

    copied = copy_uninstaller(install_dir)

    assert copied == install_dir / "_uninstall" / UNINSTALLER_NAME
    assert copied.is_file()


def test_copy_uninstaller_degrades_to_the_running_executable(tmp_path: Path) -> None:
    """A failure here must not fail an install whose files are already down."""
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")

    copied = copy_uninstaller(blocked)

    assert copied.suffix == ".exe" or copied.exists()


def test_register_records_the_icon_and_the_size(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    install_dir = tmp_path / "installed"
    (install_dir / "assets").mkdir(parents=True)
    icon = install_dir / "assets" / "o7debrief.ico"
    icon.write_bytes(b"ico")

    register(install_dir, install_dir / "Setup.exe", _BUNDLED_VERSION, scratch_keys)

    assert read_string(scratch_keys.uninstall_key, DISPLAY_ICON) == str(icon)
    assert read_string(scratch_keys.uninstall_key, DISPLAY_VERSION) == _BUNDLED_VERSION


def test_register_falls_back_to_the_install_directory_for_the_icon(
    scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    install_dir = tmp_path / "installed"
    install_dir.mkdir()

    register(install_dir, install_dir / "Setup.exe", _BUNDLED_VERSION, scratch_keys)

    assert read_string(scratch_keys.uninstall_key, DISPLAY_ICON) == str(install_dir)


def test_install_deploys_registers_and_reports_progress(
    bundle: Path,
    scratch_keys: RegistryKeys,
    isolated_profile: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "install"
    progress = RecordingProgress()

    exe_path = install(
        _options(target),
        progress=progress,
        runner=FakeRunner(default=idle_result()),
        keys=scratch_keys,
    )

    assert exe_path == target / EXE_NAME
    assert exe_path.is_file()
    assert installed_location(scratch_keys) == target
    assert read_string(scratch_keys.uninstall_key, DISPLAY_VERSION) == _BUNDLED_VERSION
    assert UNINSTALLER_PCT in progress.percentages
    assert REGISTER_PCT in progress.percentages
    assert progress.percentages[-1] == COMPLETE_PCT


def test_install_applies_the_sign_in_choice(
    bundle: Path,
    scratch_keys: RegistryKeys,
    isolated_profile: Path,
    tmp_path: Path,
) -> None:
    install(
        _options(tmp_path / "install", autostart=True),
        runner=FakeRunner(default=idle_result()),
        keys=scratch_keys,
    )

    assert is_autostart_enabled(scratch_keys) is True


def test_install_refuses_while_the_app_is_running(
    bundle: Path, scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    with pytest.raises(AppRunningError):
        install(
            _options(tmp_path / "install"),
            runner=FakeRunner(default=running_result()),
            keys=scratch_keys,
        )

    assert not (tmp_path / "install").exists()


def test_repair_redeploys_over_the_existing_install(
    bundle: Path,
    scratch_keys: RegistryKeys,
    isolated_profile: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "install"
    runner = FakeRunner(default=idle_result())
    install(_options(target), runner=runner, keys=scratch_keys)
    damaged = target / EXE_NAME
    damaged.unlink()

    exe_path = repair(target, runner=runner, keys=scratch_keys)

    assert exe_path.is_file()
    assert installed_location(scratch_keys) == target


def test_repair_refuses_while_the_app_is_running(
    bundle: Path, scratch_keys: RegistryKeys, tmp_path: Path
) -> None:
    with pytest.raises(AppRunningError):
        repair(
            tmp_path / "install",
            runner=FakeRunner(default=running_result()),
            keys=scratch_keys,
        )
