"""Tests for SingleInstanceLock: exclusivity, release and idempotency.

The lock is redirected to a temporary per-user directory so the tests never
touch the real %LOCALAPPDATA% and never collide with a running app. The lock
file path is chosen from environment variables, so pointing those at tmp_path
is enough to isolate the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from o7debrief.ui.tray.single_instance import SingleInstanceLock

# Environment variables the lock consults for its per-user base directory.
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG_RUNTIME = "XDG_RUNTIME_DIR"
_ENV_XDG_CACHE = "XDG_CACHE_HOME"


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every per-user base the lock might use at a temporary directory."""
    target = str(tmp_path)
    monkeypatch.setenv(_ENV_LOCALAPPDATA, target)
    monkeypatch.setenv(_ENV_XDG_RUNTIME, target)
    monkeypatch.setenv(_ENV_XDG_CACHE, target)


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
