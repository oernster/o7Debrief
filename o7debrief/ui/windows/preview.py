"""Debrief preview: open a rendered debrief in the default browser.

The HTML exporter writes a self-contained ``.html`` file (inlined CSS, no
JavaScript); previewing it is simply opening that file in whatever browser
the user has set as default. This uses the standard library ``webbrowser``
so the ui depends on no extra package and no infrastructure. The path is
turned into a ``file://`` URI first so spaces and Windows separators are
handled correctly.

This module belongs to the ui layer and imports the standard library only.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

__all__ = ["open_debrief"]


def open_debrief(path: str) -> bool:
    """Open a rendered debrief file in the default browser.

    Returns whether the browser was successfully invoked, mirroring
    ``webbrowser.open``. The path is resolved to an absolute ``file://`` URI
    so it opens reliably regardless of the current working directory.
    """
    uri = Path(path).resolve().as_uri()
    return webbrowser.open(uri)
