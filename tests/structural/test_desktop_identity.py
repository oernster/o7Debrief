"""Pin the Linux desktop identity across the two files that must agree on it.

A desktop decides that a window belongs to an installed application by matching
the window's own identity against the installed entry. That identity is stated
in two places which no compiler, import or test previously connected: the
application id in ``build_flatpak.sh``, which names the installed ``.desktop``
file and the two names ``main.py`` hands to Qt for the running window.

The failure when they drift is quiet and easy to misread. Nothing raises and
nothing looks broken; the app simply opens its window as a second, unrelated
launcher entry with a generic icon beside the one the user started it from. That
reads as a desktop-environment quirk rather than as a defect in this repository,
which is exactly why it is pinned here instead of left to be noticed.

Both matching paths are covered because the app runs under either. Wayland
matches on the application id, which ``main.py`` sets through
``setDesktopFileName``. X11 and XWayland match on ``WM_CLASS``, which Qt takes
from the application name and which the desktop entry restates as
``StartupWMClass``.

This test reads the shell script as text on purpose. It is the delivery recipe
rather than an importable module, so the only honest way to assert what it will
write is to read what it says.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import re
from pathlib import Path

# The files that have to agree, relative to the repository root.
BUILD_SCRIPT = "build_flatpak.sh"
COMPOSITION_ROOT = "main.py"

# The assignments each identity is read from. Each is anchored to the start of a
# line so a mention inside a comment cannot be mistaken for the definition.
_APP_ID_PATTERN = re.compile(r'^APP_ID="([^"]+)"', re.MULTILINE)
_DESKTOP_FILE_PATTERN = re.compile(r'^_DESKTOP_FILE_NAME = "([^"]+)"', re.MULTILINE)
_APP_DIR_PATTERN = re.compile(r'^_APP_DIR_NAME = "([^"]+)"', re.MULTILINE)
_STARTUP_WM_CLASS_PATTERN = re.compile(r"^StartupWMClass=(.+)$", re.MULTILINE)


def _repo_root() -> Path:
    """Return the repository root; this test lives two directories below it."""
    return Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    """Return the text of a file at the repository root."""
    return (_repo_root() / name).read_text(encoding="utf-8")


def _single_match(pattern: re.Pattern[str], text: str, what: str) -> str:
    """Return the one captured value for a pattern, failing if it is not unique.

    A second definition is as much a defect as none at all: it means the value
    is set twice and the reader cannot tell which one wins.
    """
    found = pattern.findall(text)
    assert found, f"no {what} found; the pattern this test relies on has moved"
    assert len(found) == 1, f"{what} is defined {len(found)} times: {found}"
    return found[0].strip()


def test_the_composition_root_declares_the_packaged_application_id() -> None:
    """main.py hands Qt the same application id the desktop entry is named for.

    Under Wayland this is the whole of how a window is matched to its launcher,
    so a drift here costs the association silently.
    """
    app_id = _single_match(_APP_ID_PATTERN, _read(BUILD_SCRIPT), "APP_ID")
    declared = _single_match(
        _DESKTOP_FILE_PATTERN, _read(COMPOSITION_ROOT), "_DESKTOP_FILE_NAME"
    )

    assert declared == app_id, (
        "the desktop file name in main.py and APP_ID in build_flatpak.sh have "
        f"drifted: {declared!r} against {app_id!r}. The installed entry is named "
        "from APP_ID, so the running window would no longer match it."
    )


def test_the_desktop_entry_declares_the_window_class_qt_will_use() -> None:
    """The entry's StartupWMClass matches the name Qt derives WM_CLASS from.

    This is the X11 and XWayland half of the same association. Qt takes the
    class from the application name, so the entry has to restate that exact
    value rather than the application id.
    """
    script = _read(BUILD_SCRIPT)
    application_name = _single_match(
        _APP_DIR_PATTERN, _read(COMPOSITION_ROOT), "_APP_DIR_NAME"
    )
    startup_class = _single_match(_STARTUP_WM_CLASS_PATTERN, script, "StartupWMClass")

    assert startup_class == application_name, (
        "StartupWMClass in the generated desktop entry does not match the "
        f"application name Qt reports: {startup_class!r} against "
        f"{application_name!r}. Under X11 the window would not match its launcher."
    )
