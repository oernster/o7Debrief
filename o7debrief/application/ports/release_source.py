"""ReleaseSource port: supplies the latest published release.

The concrete implementation lives in infrastructure and queries the project's
GitHub releases. The application reads releases only through this port, so it
never depends on the network or on GitHub's payload shape. A source that
cannot reach the network returns None rather than raising, keeping the update
check non-blocking and silent on failure.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from o7debrief.application.dto.release_info import ReleaseInfo

__all__ = ["ReleaseSource"]


class ReleaseSource(Protocol):
    """A source of the latest published release."""

    def latest_release(self) -> ReleaseInfo | None:
        """Return the latest published release, or None if unreachable."""
        ...
