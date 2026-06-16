"""Dev utility: render the o7 Debrief tray menu to docs/assets/tray-menu.png.

Builds the real TrayController menu the way the ui tests do (offscreen Qt, the
test fakes for the application services) and grabs it straight to a PNG, so the
website screenshot can be regenerated without a manual capture whenever the menu
changes. This is a development tool, not part of the shipped app. Run it from
the repository root:

    .\\venv\\Scripts\\python.exe tools\\capture_tray_menu.py
"""

from __future__ import annotations

import os

# Render at 2x for a crisp asset. The native platform is used deliberately, not
# offscreen: the offscreen plugin renders text as missing-glyph boxes because it
# does not load the system font database. grab() never shows a window, so
# nothing flashes on screen. Set before QApplication reads it.
os.environ.setdefault("QT_SCALE_FACTOR", "2")

import sys  # noqa: E402  (import after the scale environment is set)
from pathlib import Path  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from o7debrief.ui.tray.tray_controller import TrayController  # noqa: E402
from o7debrief.ui.view_models.session_view_model import (  # noqa: E402
    SessionViewModel,
)
from tests.ui.fakes import (  # noqa: E402
    FakeOneShot,
    FakeRecorder,
    RecordingOpener,
)

_ICON = _ROOT / "assets" / "o7debrief.ico"
_OUT = _ROOT / "docs" / "assets" / "tray-menu.png"


def main() -> int:
    """Render the tray menu to the gh-pages asset path; return a process code."""
    app = QApplication(sys.argv)
    controller = TrayController(
        one_shot=FakeOneShot(),
        session=SessionViewModel(FakeRecorder()),
        icon=QIcon(str(_ICON)),
        opener=RecordingOpener(),
    )
    menu = controller._tray.contextMenu()
    menu.ensurePolished()
    menu.resize(menu.sizeHint())
    pixmap = menu.grab()
    saved = pixmap.save(str(_OUT))
    app.quit()
    print(f"saved={saved} path={_OUT} size={pixmap.width()}x{pixmap.height()}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
