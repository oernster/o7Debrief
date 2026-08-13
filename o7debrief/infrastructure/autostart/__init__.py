"""Autostart infrastructure: launch o7Debrief at sign-in.

There is one adapter per platform and the composition root picks between them:
``WindowsAutostart`` (see ``windows_autostart``) adds or removes a per-user
``HKCU\\...\\Run`` registry entry and ``LinuxAutostart`` (see
``linux_autostart``) writes or removes an XDG autostart desktop entry. Both are
per-user, so the app can start in the system tray when the user signs in and no
administrator or root rights are needed.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
