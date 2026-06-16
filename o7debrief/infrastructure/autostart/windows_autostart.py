"""WindowsAutostart: enable or disable launching o7Debrief at sign-in.

This adapter toggles a per-user Windows startup entry under
``HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``. Adding a
value there makes Windows run the given command when the user signs in; removing
it stops that. Because it is the per-user (HKCU) Run key, no administrator
rights are required. ``winreg`` is imported inside the methods so the module
still imports cleanly off Windows (where the feature simply is not used).

The registry sub-key and value name are injectable so tests can exercise the
logic against a throwaway key without touching the real Run entry.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["WindowsAutostart"]

# The per-user Run key and the value name o7Debrief stores its command under.
_RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "o7Debrief"


class WindowsAutostart:
    """Toggles a per-user Windows Run entry (port-free infrastructure helper)."""

    def __init__(
        self, subkey: str = _RUN_SUBKEY, value_name: str = _VALUE_NAME
    ) -> None:
        self._subkey = subkey
        self._value_name = value_name

    def is_enabled(self) -> bool:
        """Return whether the Run entry currently exists."""
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._subkey) as key:
                winreg.QueryValueEx(key, self._value_name)
            return True
        except OSError:
            return False

    def enable(self, command: str) -> None:
        """Create or update the Run entry so the command runs at sign-in."""
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self._subkey) as key:
            winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, command)

    def disable(self) -> None:
        """Remove the Run entry if present; do nothing when it is absent."""
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._subkey, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, self._value_name)
        except OSError:
            return
