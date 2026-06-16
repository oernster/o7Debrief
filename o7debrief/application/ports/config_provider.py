"""ConfigProvider port: supplies the rollup specification to the application.

The concrete implementation reads the taxonomy file and builds a domain
``RollupSpec``. The application depends only on this port, so it never
touches TOML parsing or the file system directly.
"""

from __future__ import annotations

from typing import Protocol

from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["ConfigProvider"]


class ConfigProvider(Protocol):
    """A source of the event-to-beat rollup specification."""

    def load(self) -> RollupSpec:
        """Build and return the rollup specification."""
        ...

    def schema_version(self) -> str:
        """Return the schema version the provider was built against."""
        ...
