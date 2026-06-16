"""MENU_STYLESHEET: dark-dossier styling for the tray menu.

Held in its own module so the tray menu's visual style lives in one place,
matching the splash and dialogs, while the controller stays focused on
behaviour rather than carrying a long stylesheet literal. British spelling is
used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["MENU_STYLESHEET"]

# Dark-dossier styling for the tray menu, matching the splash and dialogs so the
# whole app reads as one piece rather than a native grey menu.
MENU_STYLESHEET = """
QMenu {
    background-color: #16161d;
    border: 1px solid #2a2a33;
    padding: 6px;
    color: #d7d7da;
}
QMenu::item {
    padding: 8px 32px 8px 18px;
    margin: 1px 4px;
    border-radius: 6px;
}
QMenu::item:selected { background-color: #2a2a33; color: #f8a24a; }
QMenu::item:disabled { color: #6f6f78; }
QMenu::separator { height: 1px; background: #2a2a33; margin: 6px 8px; }
"""
