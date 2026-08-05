"""Progress reporting for the long-running installer operations.

An install replaces every file in the bundle and an uninstall removes them
again, so both report their phase and a percentage rather than freezing behind
a single status line. Extraction is by far the longest phase, so it is given a
span of its own to report within rather than a single milestone. The callback is
optional throughout: the operations are callable headlessly with no reporter
attached. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from collections.abc import Callable

# A reporter receives a percentage and the message describing the current phase.
ProgressCallback = Callable[[int, str], None]

MINIMUM_PCT = 0
COMPLETE_PCT = 100

# Install phases, in the order they run. Extraction reports continuously
# between its start and end; the rest are single milestones.
EXTRACT_START_PCT = 5
EXTRACT_END_PCT = 55
EXTRACT_MESSAGE = "Extracting files..."
UNINSTALLER_PCT = 65
UNINSTALLER_MESSAGE = "Writing the uninstaller..."
REGISTER_PCT = 75
REGISTER_MESSAGE = "Registering the application..."
SHORTCUTS_PCT = 85
SHORTCUTS_MESSAGE = "Creating shortcuts..."
SETTINGS_PCT = 95
SETTINGS_MESSAGE = "Applying settings..."

# Uninstall phases.
REMOVE_SHORTCUTS_PCT = 20
REMOVE_SHORTCUTS_MESSAGE = "Removing shortcuts..."
REMOVE_REGISTRY_PCT = 50
REMOVE_REGISTRY_MESSAGE = "Removing registry entries..."
REMOVE_SETTINGS_PCT = 70
REMOVE_SETTINGS_MESSAGE = "Removing your settings..."
REMOVE_FILES_PCT = 90
REMOVE_FILES_MESSAGE = "Removing files..."

DONE_MESSAGE = "Done."


def report(callback: ProgressCallback | None, pct: int, message: str) -> None:
    """Send one progress update, doing nothing when no reporter is attached."""
    if callback is None:
        return
    callback(pct, message)


def scaled(done: int, total: int, start: int, end: int) -> int:
    """Return the percentage for ``done`` of ``total`` within a phase's span.

    A total of zero reports the end of the phase: there is nothing to wait for,
    so the phase is already complete.
    """
    if total <= 0:
        return end
    return start + ((end - start) * done) // total
