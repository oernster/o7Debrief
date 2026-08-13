"""LinuxAutostart: enable or disable launching o7Debrief at sign-in on Linux.

The Linux counterpart of ``WindowsAutostart``, with the same three methods so
the composition root can pick one by platform and nothing downstream knows which
it got.

Where Windows uses a per-user registry value, Linux uses the XDG autostart
convention: a desktop entry in ``$XDG_CONFIG_HOME/autostart`` (``~/.config/
autostart`` by default) is launched when the session starts. Every mainstream
desktop honours it, which matters more here than elegance, because o7 Debrief's
whole Linux proposition is that it is already running when the Commander quits
the game.

The directory is injectable so a test writes into a temporary tree rather than
the user's real session configuration.

Two notes for the sandboxed build. The autostart directory sits outside the
flatpak's own data, so the manifest must grant ``xdg-config/autostart:create``
or every toggle here fails silently. And the command written into the entry is
run by the host session rather than from inside the sandbox, so for a flatpak it
has to be a ``flatpak run`` invocation; the composition root decides that,
because only it knows how the running copy was started.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["LinuxAutostart"]

# The XDG base-directory variable and the conventional fallback beneath home.
_ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
_DEFAULT_CONFIG_DIR = ".config"
_AUTOSTART_DIR_NAME = "autostart"

# Identity of the entry this adapter owns. The file name is the app id, which is
# the desktop convention and keeps it from colliding with anything else.
_DEFAULT_APP_ID = "uk.co.oernster.o7Debrief"
_DEFAULT_NAME = "o7 Debrief"
_DESKTOP_SUFFIX = ".desktop"
_ENCODING = "utf-8"

# The entry itself. ``X-GNOME-Autostart-enabled`` is written explicitly because
# a desktop entry left behind by an earlier version can carry it set to false,
# and GNOME honours that in preference to the file merely existing.
_DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name={name}
Comment=Watch the Elite Dangerous journal and debrief each session
Exec={command}
Icon={app_id}
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""

# The key and value that mark an existing entry as switched off. An entry
# carrying either is treated as disabled, since that is how the desktop treats
# it; reporting it as enabled would make the settings checkbox lie.
_HIDDEN_KEY = "Hidden=true"
_GNOME_DISABLED = "X-GNOME-Autostart-enabled=false"


class LinuxAutostart:
    """Toggles an XDG autostart entry (port-free infrastructure helper)."""

    def __init__(
        self,
        app_id: str = _DEFAULT_APP_ID,
        name: str = _DEFAULT_NAME,
        autostart_dir: Path | str | None = None,
    ) -> None:
        self._app_id = app_id
        self._name = name
        self._autostart_dir = (
            Path(autostart_dir) if autostart_dir is not None else _default_dir()
        )

    @property
    def entry_path(self) -> Path:
        """Return the path of the desktop entry this adapter owns."""
        return self._autostart_dir / f"{self._app_id}{_DESKTOP_SUFFIX}"

    def is_enabled(self) -> bool:
        """Return whether an entry exists and is not marked as switched off.

        An unreadable entry counts as disabled rather than raising: the caller
        is a settings checkbox and refusing to draw is worse than drawing the
        state the desktop will actually act on.
        """
        path = self.entry_path
        try:
            if not path.is_file():
                return False
            text = path.read_text(encoding=_ENCODING)
        except OSError:
            return False
        return _HIDDEN_KEY not in text and _GNOME_DISABLED not in text

    def enable(self, command: str) -> None:
        """Write the entry so the session launches ``command`` at sign-in.

        The directory is created when absent, which is the normal case on a
        desktop where nothing has registered an autostart entry before.
        """
        path = self.entry_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _DESKTOP_TEMPLATE.format(
                name=self._name, command=command, app_id=self._app_id
            ),
            encoding=_ENCODING,
        )

    def disable(self) -> None:
        """Remove the entry if present; do nothing when it is absent.

        Removal rather than a ``Hidden=true`` marker, so switching the setting
        off leaves nothing behind for a later version to misread.
        """
        try:
            self.entry_path.unlink()
        except OSError:
            return


def _default_dir() -> Path:
    """Return the user's XDG autostart directory."""
    config_home = os.environ.get(_ENV_XDG_CONFIG_HOME)
    base = Path(config_home) if config_home else Path.home() / _DEFAULT_CONFIG_DIR
    return base / _AUTOSTART_DIR_NAME
