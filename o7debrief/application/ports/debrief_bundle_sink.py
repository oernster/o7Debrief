"""DebriefBundleSink port: persists a rendered bundle, writing only what moved.

The history report is regenerated every time the game closes, so most of what
a run produces is identical to what is already on disk. A sink implementing
this port compares before it writes and leaves an unchanged file alone: after
a four-minute session the index and the current period's page move and forty
older pages are not touched.

The result states what was written and what was skipped, so the saving is
observable rather than assumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # pragma: no cover - type-only import, no runtime dependency
    from o7debrief.application.dto.bundle import DebriefBundle

__all__ = ["BundleWriteResult", "DebriefBundleSink"]


@dataclass(frozen=True, slots=True)
class BundleWriteResult:
    """What a bundle write did: where to open it and how much it moved."""

    entry_path: str
    written: tuple[str, ...]
    skipped: tuple[str, ...]
    removed: tuple[str, ...]


class DebriefBundleSink(Protocol):
    """A destination that stores a bundle, skipping unchanged files."""

    def write_bundle(
        self, bundle: DebriefBundle, output_dir: str = ""
    ) -> BundleWriteResult:
        """Write the bundle's changed files; return where it was written.

        ``output_dir`` overrides the sink's default destination when non-empty.
        """
        ...
