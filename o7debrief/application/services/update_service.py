"""UpdateService: decide whether a newer release is available.

The service asks the injected ``ReleaseSource`` for the latest published
version and compares it against the running version. The one network call the
otherwise offline-first app makes happens indirectly through the source, and
the service never raises for an unreachable source: the source returns None and
the service reports no update available. The result is a plain ``UpdateStatus``.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.application.dto.update_status import UpdateStatus
from o7debrief.application.services.version_compare import is_newer

if TYPE_CHECKING:
    from o7debrief.application.ports.release_source import ReleaseSource

__all__ = ["UpdateService"]


class UpdateService:
    """Compares the running version against the latest available release."""

    def __init__(self, source: ReleaseSource, current_version: str) -> None:
        self._source = source
        self._current_version = current_version

    def check(self) -> UpdateStatus:
        """Return the update status for the running version.

        A source that cannot be reached yields a None latest version and so a
        status reporting no update, keeping the check silent on failure.
        """
        latest = self._source.latest_version()
        available = latest is not None and is_newer(latest, self._current_version)
        return UpdateStatus(
            current=self._current_version,
            latest=latest,
            update_available=available,
        )
