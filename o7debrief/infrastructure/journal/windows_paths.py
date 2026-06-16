"""Windows Saved Games discovery via the Known Folders API.

Lifted from the author's EDColonisationAsst (``utils/windows.py``) and kept
deliberately small. ``get_saved_games_path`` asks Windows for the real Saved
Games folder through ``SHGetKnownFolderPath`` and falls back to ``USERPROFILE``
when the WinAPI is unavailable (for example on non-Windows platforms, where
``ctypes.windll`` does not exist). It only ever reads paths; it never writes.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

__all__ = ["get_saved_games_path", "FOLDERID_SAVED_GAMES"]

# Known Folder ID for "Saved Games" as defined by the Windows shell.
FOLDERID_SAVED_GAMES = "{4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4}"

# A Windows GUID's trailing Data4 member is an eight-byte array; this is a fixed
# structural constant of the GUID layout, not a domain value.
_GUID_DATA4_BYTES = 8

# The dwFlags argument to SHGetKnownFolderPath: 0 selects the default behaviour.
_KF_FLAG_DEFAULT = 0

# Characters stripped from the registry-style GUID string before hex decoding.
_GUID_DASH = "-"
_GUID_OPEN = "{"
_GUID_CLOSE = "}"
_EMPTY = ""

# Subfolder under the user profile when the Known Folders API is unavailable.
_SAVED_GAMES_DIRNAME = "Saved Games"
_USERPROFILE_ENV = "USERPROFILE"


class GUID(ctypes.Structure):
    """A Windows GUID with a fixed-width layout matching the shell API.

    Fixed-width integer types are used so the struct layout matches Windows
    GUIDs even when the module is imported on a non-Windows platform (where
    ``c_ulong`` may be 64-bit).
    """

    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * _GUID_DATA4_BYTES),
    ]


def _guid_from_string(guid_string: str) -> GUID:
    """Build a GUID structure from a registry-style GUID string."""
    hex_text = (
        guid_string.replace(_GUID_DASH, _EMPTY)
        .replace(_GUID_OPEN, _EMPTY)
        .replace(_GUID_CLOSE, _EMPTY)
    )
    return GUID.from_buffer_copy(bytes.fromhex(hex_text))


def _path_from_winapi() -> Path | None:
    """Return the Saved Games path via SHGetKnownFolderPath, or None.

    Any WinAPI failure (including a missing ``windll`` on non-Windows) returns
    None so the caller can fall back to the user profile. The returned pointer
    is freed with CoTaskMemFree in all cases.
    """
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None

    ptr: ctypes.c_wchar_p | None = None
    try:
        ptr = ctypes.c_wchar_p()
        folder_guid = _guid_from_string(FOLDERID_SAVED_GAMES)
        windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_guid),
            _KF_FLAG_DEFAULT,
            None,
            ctypes.byref(ptr),
        )
        value = ptr.value
        if value:
            return Path(value)
        return None
    except Exception:  # noqa: BLE001 - any WinAPI failure falls back below.
        return None
    finally:
        if ptr is not None:
            try:
                windll.ole32.CoTaskMemFree(ptr)
            except Exception:  # noqa: BLE001 - freeing failures are non-fatal.
                pass


def get_saved_games_path() -> Path | None:
    """Return the user's Saved Games folder, or None when it cannot be found.

    The Known Folders API is preferred; when it is unavailable the value of the
    ``USERPROFILE`` environment variable is used. Returns None if neither path
    can be resolved.
    """
    winapi_path = _path_from_winapi()
    if winapi_path is not None:
        return winapi_path

    user_profile = os.environ.get(_USERPROFILE_ENV)
    if user_profile:
        return Path(user_profile) / _SAVED_GAMES_DIRNAME
    return None
