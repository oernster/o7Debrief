"""Tests for SingleInstanceLock: exclusivity, release and idempotency.

The lock is redirected to a temporary per-user directory so the tests never
touch the real %LOCALAPPDATA% and never collide with a running app. The lock
file path is chosen from environment variables, so pointing those at tmp_path
is enough to isolate the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from o7debrief.ui.tray import single_instance
from o7debrief.ui.tray.single_instance import SingleInstanceLock, user_lock_dir

# Environment variables the lock consults for its per-user base directory.
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG_RUNTIME = "XDG_RUNTIME_DIR"
_ENV_XDG_CACHE = "XDG_CACHE_HOME"
_ENV_FLATPAK_ID = "FLATPAK_ID"

# Application id a flatpak build runs under, used to check the sandbox branch.
_FLATPAK_APP_ID = "uk.codecrafter.o7Debrief"


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every per-user base the lock might use at a temporary directory."""
    target = str(tmp_path)
    monkeypatch.setenv(_ENV_LOCALAPPDATA, target)
    monkeypatch.setenv(_ENV_XDG_RUNTIME, target)
    monkeypatch.setenv(_ENV_XDG_CACHE, target)
    monkeypatch.delenv(_ENV_FLATPAK_ID, raising=False)


def test_acquire_succeeds_then_releases() -> None:
    """A single lock acquires successfully and releases without error."""
    lock = SingleInstanceLock()
    try:
        assert lock.acquire() is True
    finally:
        lock.release()


def test_acquire_is_idempotent_within_one_instance() -> None:
    """Calling acquire twice on the same held lock returns True both times."""
    lock = SingleInstanceLock()
    try:
        assert lock.acquire() is True
        assert lock.acquire() is True
    finally:
        lock.release()


def test_second_instance_is_blocked_until_first_releases() -> None:
    """A second lock cannot acquire while the first holds it, then can."""
    first = SingleInstanceLock()
    second = SingleInstanceLock()
    try:
        assert first.acquire() is True
        assert second.acquire() is False
        first.release()
        assert second.acquire() is True
    finally:
        first.release()
        second.release()


def test_release_without_acquire_is_safe() -> None:
    """Releasing a lock that was never acquired does nothing and does not raise."""
    lock = SingleInstanceLock()
    lock.release()


def test_the_lock_directory_sits_under_the_runtime_directory(tmp_path: Path) -> None:
    """Outside a sandbox the lock lives in the app's own runtime subdirectory.

    The runtime resolution is called directly rather than through the platform
    branch above it. Pretending to be Linux by rewriting ``os.name`` also
    rewrites which concrete path class ``Path`` builds; a POSIX path cannot be
    instantiated on Windows at all, so the pretence breaks before the code under
    test is reached. Handing the directory in tests the same logic without lying
    about the host.
    """
    assert single_instance._runtime_lock_dir(tmp_path) == tmp_path / "o7Debrief"


def test_inside_a_flatpak_the_lock_directory_is_the_shared_app_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In the sandbox the lock moves to the directory every instance shares.

    Each flatpak instance gets its own runtime directory, so a lock file
    directly beneath it would be invisible to the next launch: the guard would
    admit a second tray and the summon marker would never be seen. The
    application subdirectory is the one place flatpak shares between instances,
    which is what makes both the guard and the summon route work in the sandbox.
    """
    monkeypatch.setenv(_ENV_FLATPAK_ID, _FLATPAK_APP_ID)

    assert (
        single_instance._runtime_lock_dir(tmp_path)
        == tmp_path / "app" / _FLATPAK_APP_ID
    )


def test_the_lock_directory_is_the_one_the_app_actually_uses(tmp_path: Path) -> None:
    """The public resolver returns a per-user app directory on this host too."""
    assert user_lock_dir() == tmp_path / "o7Debrief"
