"""Tests for WindowsAutostart against a throwaway registry sub-key.

These never touch the real ``...\\Run`` entry: the store is pointed at a
disposable sub-key under HKCU, exercised, then deleted. Windows-only.
"""

from __future__ import annotations

import sys

import pytest

from o7debrief.infrastructure.autostart.windows_autostart import WindowsAutostart

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Windows-only registry feature"
)

_TEST_SUBKEY = r"Software\o7DebriefAutostartTest"
_TEST_VALUE = "o7DebriefTest"
_FAKE_COMMAND = r'"C:\fake\o7Debrief.exe"'


def _cleanup() -> None:
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _TEST_SUBKEY)
    except OSError:
        pass


def test_enable_query_disable_roundtrip() -> None:
    autostart = WindowsAutostart(subkey=_TEST_SUBKEY, value_name=_TEST_VALUE)
    try:
        assert autostart.is_enabled() is False

        autostart.enable(_FAKE_COMMAND)
        assert autostart.is_enabled() is True

        autostart.disable()
        assert autostart.is_enabled() is False

        # Disabling again is a harmless no-op.
        autostart.disable()
        assert autostart.is_enabled() is False
    finally:
        _cleanup()
