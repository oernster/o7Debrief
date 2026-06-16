"""ReleaseSource port: supplies the latest published release version.

The concrete implementation lives in infrastructure and queries the project's
GitHub releases. The application reads the latest version only through this
port, so it never depends on the network or on GitHub's payload shape. A source
that cannot reach the network returns None rather than raising, keeping the
update check non-blocking and silent on failure.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["ReleaseSource"]


class ReleaseSource(Protocol):
    """A source of the latest published release version."""

    def latest_version(self) -> str | None:
        """Return the latest released version string, or None if unreachable."""
        ...
