"""Autostart infrastructure: launch o7Debrief at Windows sign-in.

The public adapter is ``WindowsAutostart`` (see ``windows_autostart``), which
adds or removes a per-user ``HKCU\\...\\Run`` registry entry so the app can start
in the system tray when the user signs in. No administrator rights are needed.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
