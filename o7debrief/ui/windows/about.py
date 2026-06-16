"""About dialog for o7Debrief: icon, author, version and open source credits.

Mirrors the layout of the author's other desktop apps: the application icon, a
short identity block (name, tagline, version, author, licence line), then a
scrollable credits section acknowledging the open source projects o7Debrief is
built on and the wider Python community. The version is read from the package;
the icon is injected so the dialog reuses the very icon the tray shows.

This module belongs to the ui layer and imports the application layer (only the
package version, which carries no behaviour) and PySide6.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from o7debrief import __version__
from o7debrief.ui.windows.dialog_theme import HEADING_COLOUR, apply_dialog_theme

__all__ = ["AboutDialog"]

_TITLE = "About o7 Debrief"
_CLOSE_TEXT = "Close"
_AUTHOR = "Oliver Ernster"

# Dialog geometry and typography, as named layout constants.
_ICON_PX = 96
_MIN_WIDTH_PX = 540
_BODY_MIN_HEIGHT_PX = 360
_SPACING_PX = 8

# Open source credits as discrete HTML list items, one per dependency o7Debrief
# actually ships or builds with. Date ranges use an en-dash entity, not a dash
# in the source.
_CREDITS = (
    "<li><b>Python</b> - Copyright &copy; 2001&ndash;2026 Python Software "
    "Foundation. Licensed under the PSF Licence.</li>",
    "<li><b>PySide6 (Qt for Python)</b> - Copyright &copy; The Qt Company "
    "Ltd. Licensed under the LGPL-3.0.</li>",
    "<li><b>Jinja2</b> - Copyright &copy; 2007 Pallets. Licensed under the "
    "BSD 3-Clause Licence.</li>",
    "<li><b>Nuitka</b> - Copyright &copy; Kay Hayen. Licensed under the "
    "Apache Licence 2.0.</li>",
    "<li><b>pytest</b> - Copyright &copy; 2004&ndash;2026 Holger Krekel and "
    "the pytest contributors. Licensed under the MIT Licence.</li>",
    "<li><b>black</b> - Copyright &copy; 2018&ndash;2026 &#321;ukasz Langa "
    "and contributors. Licensed under the MIT Licence.</li>",
    "<li><b>flake8</b> - Copyright &copy; 2011&ndash;2026 Tarek Ziad&eacute; "
    "and the flake8 contributors. Licensed under the MIT Licence.</li>",
)


def _about_html() -> str:
    """Return the About body as HTML, with the live version filled in."""
    credits_html = "\n".join(_CREDITS)
    return (
        f'<h2 style="color: {HEADING_COLOUR}; margin-bottom: 2px;">o7 Debrief</h2>'
        "<p><b>Commander Mission Debrief</b></p>"
        "<p>A local-first session debrief generator for Elite Dangerous.</p>"
        f"<p><b>Version:</b> {__version__}</p>"
        f"<p><b>Author:</b> {_AUTHOR}</p>"
        "<p>Distributed under the GNU Lesser General Public Licence v3.0 "
        "(LGPL-3.0).</p>"
        "<hr>"
        f'<h3 style="color: {HEADING_COLOUR};">Open Source Credits</h3>'
        "<p>o7 Debrief is built on the shoulders of the following open source "
        "projects and their communities:</p>"
        f"<ul>{credits_html}</ul>"
        "<p>My thanks to the Python community for providing an outstanding "
        "ecosystem that makes projects like this possible.</p>"
    )


class AboutDialog(QDialog):
    """Shows the o7Debrief icon, author, version and open source credits."""

    def __init__(
        self, icon: QIcon | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_TITLE)
        self.setMinimumWidth(_MIN_WIDTH_PX)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(_SPACING_PX)

        if icon is not None and not icon.isNull():
            image = QLabel()
            image.setPixmap(icon.pixmap(QSize(_ICON_PX, _ICON_PX)))
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(_about_html())
        body.setMinimumHeight(_BODY_MIN_HEIGHT_PX)
        layout.addWidget(body)

        row = QHBoxLayout()
        close_button = QPushButton(_CLOSE_TEXT)
        close_button.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)
