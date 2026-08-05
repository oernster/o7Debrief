"""Fixtures that keep the installer suite off the real machine.

Two isolations matter. The registry keys the installer writes are values rather
than constants, so every test that writes one is given a scratch key under a
test-only root and that key is removed afterwards. The per-user locations come
from environment variables, so the profile directories are redirected into a
temporary tree. Between them, running this suite never touches an actual
o7Debrief installation. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from installer.constants import (
    APP_NAME,
    ENV_APPDATA,
    ENV_LOCALAPPDATA,
    PAYLOAD_DIR_NAME,
)
from installer.ops import payload as payload_module
from installer.state.registry import RegistryKeys

TEST_KEY_ROOT = r"Software\o7DebriefInstallerTests"
_USER_PROFILE = "USERPROFILE"


def delete_tree(key: str) -> None:
    """Remove an HKCU key and everything under it."""
    import winreg

    try:
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key)
    except OSError:
        return
    with handle:
        while True:
            try:
                child = winreg.EnumKey(handle, 0)
            except OSError:
                break
            delete_tree(rf"{key}\{child}")
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except OSError:
        return


@pytest.fixture()
def scratch_keys() -> Iterator[RegistryKeys]:
    """Yield a unique set of HKCU keys, removed again afterwards."""
    root = rf"{TEST_KEY_ROOT}\{uuid.uuid4().hex}"
    keys = RegistryKeys(
        uninstall_key=rf"{root}\Uninstall",
        run_subkey=rf"{root}\Run",
        run_value="o7DebriefTest",
        classes_subkey=rf"{root}\Classes",
        aumid="OliverErnster.o7Debrief.Test",
    )
    try:
        yield keys
    finally:
        delete_tree(root)


@pytest.fixture()
def staged_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the payload anchor at a temporary installer package directory.

    The real payload is a quarter of a gigabyte staged by the build, so no test
    reads it. Redirecting the anchor lets a small bundle stand in for it.
    """
    root = tmp_path / "installer"
    (root / PAYLOAD_DIR_NAME / APP_NAME).mkdir(parents=True)
    monkeypatch.setattr(payload_module, "installer_root", lambda: root)
    monkeypatch.setattr(payload_module, "program_root", lambda: root.parent)
    return root


@pytest.fixture()
def isolated_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the per-user profile locations into a temporary tree."""
    home = tmp_path / "profile"
    (home / "Desktop").mkdir(parents=True)
    local = home / "AppData" / "Local"
    roaming = home / "AppData" / "Roaming"
    local.mkdir(parents=True)
    roaming.mkdir(parents=True)
    monkeypatch.setenv(_USER_PROFILE, str(home))
    monkeypatch.setenv(ENV_LOCALAPPDATA, str(local))
    monkeypatch.setenv(ENV_APPDATA, str(roaming))
    return home
