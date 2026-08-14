"""Tests for Windows Saved Games discovery via the Known Folders API.

The module was written to be safe off Windows: it reaches the WinAPI through
``getattr(ctypes, "windll", None)`` and falls back to ``USERPROFILE``, so it
imports and answers on any platform. That shape is exactly what makes it
testable here. The module's own ``ctypes`` reference is replaced with a small
hand-written stand-in, so the branches (no WinAPI, a call that fails, a pointer
that comes back empty, a free that raises) are exercised as branches rather
than left to whichever machine the suite happens to run on.

What is not claimed: none of this proves the real shell API returns the right
folder. That is unprovable in a unit test on any platform. What is proved is
the decision logic around it, which is where the failure modes live.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

from o7debrief.infrastructure.journal import windows_paths

# A Saved Games path the fake WinAPI hands back.
_WINAPI_PATH = r"D:\Games\Saved Games"
# A user profile used for the fallback route.
_PROFILE = r"D:\Users\Commander"
# The Known Folder GUID's bytes, decoded from the registry-style string. The
# struct is compared as bytes rather than field by field: a GUID's text form is
# big-endian while its first three fields are read in the platform's own order,
# so a field comparison would assert the byte order rather than the identity.
_FOLDERID_BYTES = bytes.fromhex("4C5C32FFBB9D43B0B5B42D72E54EAAA4")


class _FakePointer:
    """Stands in for ``ctypes.c_wchar_p``: it only has to carry a value."""

    def __init__(self, value: str | None = None) -> None:
        self.value = value


class _FakeShell32:
    """Writes a path into the pointer the caller passed, as the real API does."""

    def __init__(self, value: str | None, raises: bool = False) -> None:
        self._value = value
        self._raises = raises
        self.guid = None

    def SHGetKnownFolderPath(self, guid, flags, token, pointer):
        """Mirror the WinAPI signature; the name is Windows', not ours."""
        if self._raises:
            raise OSError("SHGetKnownFolderPath failed")
        self.guid = guid
        pointer.value = self._value


class _FakeOle32:
    """Records each free. A refusing one exercises the other path through finally."""

    def __init__(self, raises: bool = False) -> None:
        self._raises = raises
        self.freed = 0

    def CoTaskMemFree(self, pointer):
        """Mirror the WinAPI signature; the name is Windows', not ours."""
        if self._raises:
            raise OSError("CoTaskMemFree failed")
        self.freed += 1


class _FakeWindll:
    def __init__(self, shell32: _FakeShell32, ole32: _FakeOle32) -> None:
        self.shell32 = shell32
        self.ole32 = ole32


class _FakeCtypes:
    """The subset of ctypes the module reaches for at call time."""

    def __init__(self, windll: _FakeWindll | None) -> None:
        if windll is not None:
            self.windll = windll

    def c_wchar_p(self) -> _FakePointer:
        return _FakePointer()

    def byref(self, value):
        """Hand back the object itself, so a fake can write to it."""
        return value


def _install(monkeypatch, value: str | None, call_raises=False, free_raises=False):
    """Point the module at a fake WinAPI and return its ole32 for inspection."""
    ole32 = _FakeOle32(raises=free_raises)
    shell32 = _FakeShell32(value, raises=call_raises)
    monkeypatch.setattr(
        windows_paths, "ctypes", _FakeCtypes(_FakeWindll(shell32, ole32))
    )
    return ole32


def test_the_folder_guid_decodes_to_the_windows_layout() -> None:
    """The registry-style GUID string becomes the struct Windows expects."""
    guid = windows_paths._guid_from_string(windows_paths.FOLDERID_SAVED_GAMES)

    assert isinstance(guid, ctypes.Structure)
    assert bytes(guid) == _FOLDERID_BYTES


def test_no_winapi_at_all_yields_no_path(monkeypatch) -> None:
    """Off Windows there is no windll, which is a None rather than a crash."""
    monkeypatch.setattr(windows_paths, "ctypes", _FakeCtypes(None))

    assert windows_paths._path_from_winapi() is None


def test_the_winapi_path_is_returned_and_the_pointer_freed(monkeypatch) -> None:
    ole32 = _install(monkeypatch, _WINAPI_PATH)

    assert windows_paths._path_from_winapi() == Path(_WINAPI_PATH)
    assert ole32.freed == 1


def test_an_empty_pointer_yields_no_path(monkeypatch) -> None:
    """The call can succeed and still hand back nothing."""
    ole32 = _install(monkeypatch, None)

    assert windows_paths._path_from_winapi() is None
    assert ole32.freed == 1


def test_a_failing_winapi_call_yields_no_path_and_still_frees(monkeypatch) -> None:
    """Any WinAPI failure falls back rather than propagating."""
    ole32 = _install(monkeypatch, _WINAPI_PATH, call_raises=True)

    assert windows_paths._path_from_winapi() is None
    assert ole32.freed == 1


def test_a_failing_free_does_not_lose_the_answer(monkeypatch) -> None:
    """Freeing is best effort: a failure there must not discard the path."""
    _install(monkeypatch, _WINAPI_PATH, free_raises=True)

    assert windows_paths._path_from_winapi() == Path(_WINAPI_PATH)


def test_saved_games_prefers_the_winapi_answer(monkeypatch) -> None:
    monkeypatch.setattr(windows_paths, "_path_from_winapi", lambda: Path(_WINAPI_PATH))

    assert windows_paths.get_saved_games_path() == Path(_WINAPI_PATH)


def test_saved_games_falls_back_to_the_user_profile(monkeypatch) -> None:
    """Without the WinAPI the profile is used, with the conventional subfolder."""
    monkeypatch.setattr(windows_paths, "_path_from_winapi", lambda: None)
    monkeypatch.setenv(windows_paths._USERPROFILE_ENV, _PROFILE)

    expected = Path(_PROFILE) / windows_paths._SAVED_GAMES_DIRNAME
    assert windows_paths.get_saved_games_path() == expected


def test_no_winapi_and_no_profile_is_no_answer(monkeypatch) -> None:
    """Nothing is invented when neither route resolves."""
    monkeypatch.setattr(windows_paths, "_path_from_winapi", lambda: None)
    monkeypatch.delenv(windows_paths._USERPROFILE_ENV, raising=False)

    assert windows_paths.get_saved_games_path() is None
