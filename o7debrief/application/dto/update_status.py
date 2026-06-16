"""UpdateStatus DTO: the outcome of a single update check.

Returned by the UpdateService so the ui can decide whether to point the user at
the releases page. ``latest`` is None when the release source could not be
reached, in which case ``update_available`` is always False.
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
