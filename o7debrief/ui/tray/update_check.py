"""Coordinate a manual 'check for updates' from the tray.

Given an update service, a notifier and a web opener, this runs the check and
either announces that an update is available and opens the releases page, or
announces that the app is up to date. It holds no Qt or service state of its
own: the controller passes its notifier and opener in, so this stays a small,
testable piece of policy. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from o7debrief.application.services.update_service import UpdateService

__all__ = ["check_for_updates"]

# Notification captions and bodies for the two outcomes of an update check.
_AVAILABLE_TITLE = "Update available"
_AVAILABLE_BODY = "{version} is available. Opening the releases page."
_UP_TO_DATE_TITLE = "Up to date"
_UP_TO_DATE_BODY = "You are running the latest version."


def check_for_updates(
    update_service: UpdateService,
    notify: Callable[[str, str], None],
    web_opener: Callable[[str], bool],
    releases_url: str,
) -> None:
    """Run the check, announcing the outcome and opening releases if newer."""
    status = update_service.check()
    if status.update_available:
        notify(_AVAILABLE_TITLE, _AVAILABLE_BODY.format(version=status.latest))
        web_opener(releases_url)
    else:
        notify(_UP_TO_DATE_TITLE, _UP_TO_DATE_BODY)
