"""DebriefSink port: persists rendered debrief bytes to a destination.

The concrete sink decides where bytes go (a file on disk, for example).
It returns the location it wrote to so the application can report the
paths produced for a run.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["DebriefSink"]


class DebriefSink(Protocol):
    """A destination that stores rendered debrief content."""

    def write(
        self, name: str, content: bytes, suffix: str, output_dir: str = ""
    ) -> str:
        """Write ``content`` under ``name`` with ``suffix``; return the path.

        ``output_dir`` overrides the sink's default destination when non-empty.
        """
        ...
