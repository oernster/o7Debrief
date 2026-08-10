"""UpdateStatus DTO: the outcome of a single update check.

Returned by the UpdateService so the ui can decide what to offer. ``latest``
is None when the release source could not be reached, in which case
``update_available`` is always False. ``download_url`` names the platform's
own installer asset when the release carries one; ``page_url`` is the human
releases page the ui falls back to.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["UpdateStatus"]


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    """The result of comparing the running version against the latest release."""

    current: str
    latest: str | None
    update_available: bool
    download_url: str | None = None
    page_url: str | None = None
