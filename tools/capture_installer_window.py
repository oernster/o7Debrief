"""Dev utility: render the setup window to a PNG without building an installer.

Checking the setup window used to mean cutting a release, downloading it through
the application's own update check and running the installer, so a misaligned
label or a wrong version cost a full release cycle to see. This renders the real
window straight to a PNG instead.

Both states are captured. The live one reads this machine's actual registry, so
it shows exactly what the setup program would show if run now. The synthetic one
forces the fresh-install state, which cannot be seen on a machine that already
has the application. The native Qt platform is used (not offscreen) so fonts
resolve; grab() never shows a window, so nothing flashes on screen. Run from the
repository root:

    .\\venv\\Scripts\\python.exe tools\\capture_installer_window.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from installer.ops.paths import install_target  # noqa: E402
from installer.state.model import InstallState, StateSnapshot  # noqa: E402
from installer.ui._main_window_build import build_window  # noqa: E402
from installer.ui.main_window import InstallerWindow  # noqa: E402
from installer.ui.themes import (  # noqa: E402
    STYLESHEET,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

_LIVE_OUT = _ROOT / "installer-window-live.png"
_FRESH_OUT = _ROOT / "installer-window-fresh.png"
# A version for the synthetic capture only. The live capture reads the real one.
_SAMPLE_VERSION = "0.0.0"
_LAYOUT_PASSES = 3


def _settle(window: QWidget, app: QApplication) -> None:
    """Let the layout resolve before the widget is grabbed."""
    window.ensurePolished()
    for _ in range(_LAYOUT_PASSES):
        window.layout().activate()
        app.processEvents()


def _capture_live(app: QApplication) -> None:
    """Grab the real window, reading this machine's own install state."""
    window = InstallerWindow()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    _settle(window, app)
    window.grab().save(str(_LIVE_OUT))
    snapshot = window._snapshot  # noqa: SLF001 (a capture script, not production)
    print(
        f"wrote {_LIVE_OUT} "
        f"(state={snapshot.state} installed={snapshot.installed_version or 'none'} "
        f"bundled={snapshot.bundled_version})"
    )


def _capture_fresh(app: QApplication) -> None:
    """Grab the fresh-install state, which an installed machine cannot show.

    Built from the layout directly rather than the window class, so the state is
    forced rather than detected. Repair and Uninstall are hidden by the window
    itself, so they appear here even though a real fresh install hides them.
    """
    window = QWidget()
    window.setStyleSheet(STYLESHEET)
    build_window(
        window,
        StateSnapshot(
            state=InstallState.NOT_INSTALLED,
            bundled_version=_SAMPLE_VERSION,
            installed_version="",
            install_dir=install_target(),
            autostart=False,
        ),
    )
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    _settle(window, app)
    window.grab().save(str(_FRESH_OUT))
    print(f"wrote {_FRESH_OUT} (synthetic fresh-install state)")


def main() -> int:
    """Capture both setup-window states to PNGs beside the repository root."""
    app = QApplication(sys.argv)
    _capture_live(app)
    _capture_fresh(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
