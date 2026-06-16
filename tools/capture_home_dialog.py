"""Dev utility: render the o7 Debrief home dialog to docs/assets/home-screen.png.

Builds the real HomeDialog with representative sample data and grabs it straight
to a PNG. The native Qt platform is used (not offscreen) so fonts resolve; grab()
never shows a window, so nothing flashes on screen. Run from the repository root:

    .\\venv\\Scripts\\python.exe tools\\capture_home_dialog.py
"""

from __future__ import annotations

import os

# Render at 2x for a crisp asset. Set before QApplication reads it.
os.environ.setdefault("QT_SCALE_FACTOR", "2")

import sys  # noqa: E402  (import after the scale environment is set)
from pathlib import Path  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from o7debrief.ui.windows.home import HomeDialog  # noqa: E402

_ICON = _ROOT / "assets" / "o7debrief.ico"
_OUT = _ROOT / "docs" / "assets" / "home-screen.png"
_STATUS = "Recording session: 128 events."
_RECENT = (
    "debrief_2026-06-15_21-00-00.html",
    "debrief_2026-06-15_18-30-00.html",
)


def _noop() -> None:
    """Do nothing; stands in for the dialog's injected action callbacks."""
    return None


def main() -> int:
    """Render the home dialog to the gh-pages asset path; return a process code."""
    app = QApplication(sys.argv)
    dialog = HomeDialog(
        _STATUS,
        _RECENT,
        on_debrief_last=_noop,
        on_debrief_history=_noop,
        on_settings=_noop,
        on_about=_noop,
        on_open_recent=lambda _path: None,
        icon=QIcon(str(_ICON)),
    )
    dialog.ensurePolished()
    dialog.adjustSize()
    pixmap = dialog.grab()
    saved = pixmap.save(str(_OUT))
    app.quit()
    print(f"saved={saved} path={_OUT} size={pixmap.width()}x{pixmap.height()}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
