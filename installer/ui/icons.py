"""Loading the real application icon and claiming a taskbar identity.

The icon is always the bundled file. Painting a glyph onto a pixmap would ship a
setup program whose icon does not match the application it installs. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon

from installer.constants import INSTALLER_AUMID
from installer.ops.payload import icon_file


def app_icon() -> QIcon:
    """Return the bundled application icon, or an empty icon when absent."""
    path = icon_file()
    if path is None:
        return QIcon()
    return QIcon(str(path))


def set_app_user_model_id(aumid: str = INSTALLER_AUMID) -> None:
    """Give the setup program a stable taskbar identity (best effort)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(aumid)
    except (OSError, AttributeError):
        return
