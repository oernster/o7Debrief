"""The HKCU registry record: what makes the app an installed program.

Three registrations live here, all per user so no step needs administrator
rights:

- the Uninstall key, which puts the app in "Apps & features" with a working
  Uninstall action and is the source of truth for installed state;
- the Run value, which starts the app at Windows sign-in;
- the AppUserModelId class the app writes for its notifications, removed on
  uninstall so nothing is left behind.

Which keys are written is a value rather than a constant baked into each
function. Production passes the real set; a test passes a scratch set, so the
behaviour is exercised in full without ever touching the user's own
registration. British spelling is used in comments. No em dashes appear
anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from installer.constants import (
    APP_AUMID,
    APP_DISPLAY_NAME,
    APP_PUBLISHER,
    APP_URL,
    AUMID_CLASSES_SUBKEY,
    RUN_SUBKEY,
    RUN_VALUE,
    UNINSTALL_FLAG,
    UNINSTALL_KEY,
)

DISPLAY_NAME = "DisplayName"
DISPLAY_VERSION = "DisplayVersion"
INSTALL_LOCATION = "InstallLocation"
UNINSTALL_STRING = "UninstallString"
DISPLAY_ICON = "DisplayIcon"
PUBLISHER = "Publisher"
URL_INFO_ABOUT = "URLInfoAbout"
NO_MODIFY = "NoModify"
NO_REPAIR = "NoRepair"
ESTIMATED_SIZE = "EstimatedSize"

_FLAG_SET = 1


@dataclass(frozen=True, slots=True)
class RegistryKeys:
    """Every HKCU location the installer reads or writes."""

    uninstall_key: str = UNINSTALL_KEY
    run_subkey: str = RUN_SUBKEY
    run_value: str = RUN_VALUE
    classes_subkey: str = AUMID_CLASSES_SUBKEY
    aumid: str = APP_AUMID

    @property
    def toast_key(self) -> str:
        """Return the key holding the app's notification registration."""
        return rf"{self.classes_subkey}\{self.aumid}"


DEFAULT_KEYS = RegistryKeys()


def read_string(key: str, name: str) -> str | None:
    """Return an HKCU string value, or None when the key or value is absent."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            return str(winreg.QueryValueEx(handle, name)[0])
    except OSError:
        return None


def write_uninstall_entry(
    install_dir: Path,
    uninstaller: Path,
    version: str,
    *,
    display_icon: Path | None = None,
    estimated_kb: int | None = None,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> None:
    """Register the app under HKCU so it appears in Apps and features."""
    import winreg

    icon = str(display_icon) if display_icon is not None else str(install_dir)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, keys.uninstall_key) as handle:
        winreg.SetValueEx(handle, DISPLAY_NAME, 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(handle, DISPLAY_VERSION, 0, winreg.REG_SZ, version)
        winreg.SetValueEx(handle, INSTALL_LOCATION, 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(
            handle,
            UNINSTALL_STRING,
            0,
            winreg.REG_SZ,
            f'"{uninstaller}" {UNINSTALL_FLAG}',
        )
        winreg.SetValueEx(handle, DISPLAY_ICON, 0, winreg.REG_SZ, icon)
        winreg.SetValueEx(handle, PUBLISHER, 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(handle, URL_INFO_ABOUT, 0, winreg.REG_SZ, APP_URL)
        winreg.SetValueEx(handle, NO_MODIFY, 0, winreg.REG_DWORD, _FLAG_SET)
        winreg.SetValueEx(handle, NO_REPAIR, 0, winreg.REG_DWORD, _FLAG_SET)
        if estimated_kb is not None:
            winreg.SetValueEx(handle, ESTIMATED_SIZE, 0, winreg.REG_DWORD, estimated_kb)


def delete_key(key: str) -> None:
    """Remove an HKCU key, doing nothing when it is already absent."""
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except OSError:
        return


def delete_uninstall_entry(keys: RegistryKeys = DEFAULT_KEYS) -> None:
    """Remove the Uninstall registration."""
    delete_key(keys.uninstall_key)


def delete_toast_identity(keys: RegistryKeys = DEFAULT_KEYS) -> None:
    """Remove the app's notification (AppUserModelId) registration."""
    delete_key(keys.toast_key)


def installed_version(keys: RegistryKeys = DEFAULT_KEYS) -> str | None:
    """Return the registered installed version, or None when not installed."""
    return read_string(keys.uninstall_key, DISPLAY_VERSION)


def installed_location(keys: RegistryKeys = DEFAULT_KEYS) -> Path | None:
    """Return the registered install location, or None when not installed.

    A recorded location that is not absolute is treated as absent: it cannot be
    acted on, and Path would quietly turn an empty value into the current
    directory, which is the one place an uninstall must never point at.
    """
    raw = read_string(keys.uninstall_key, INSTALL_LOCATION)
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else None


def set_autostart(
    enabled: bool,
    exe_path: Path,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> None:
    """Add or remove the Run entry that starts the app at sign-in."""
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, keys.run_subkey) as handle:
            if enabled:
                winreg.SetValueEx(
                    handle, keys.run_value, 0, winreg.REG_SZ, f'"{exe_path}"'
                )
                return
            try:
                winreg.DeleteValue(handle, keys.run_value)
            except OSError:
                return
    except OSError:
        return


def is_autostart_enabled(keys: RegistryKeys = DEFAULT_KEYS) -> bool:
    """Return True when the sign-in Run entry is present."""
    return read_string(keys.run_subkey, keys.run_value) is not None
