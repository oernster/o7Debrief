"""FilesystemSink: write rendered debrief bytes atomically to a directory.

This adapter implements the application ``DebriefSink`` port. It writes each
rendered debrief to a configured output directory under a name and suffix,
using a temporary file plus ``os.replace`` so a reader never sees a half-written
file. It returns the path written so the caller can report it.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["FilesystemSink"]

# Separator placed between the debrief name and its file-type suffix.
_SUFFIX_SEPARATOR = "."
# Suffix of the temporary file written before the atomic replace into place.
_TEMP_SUFFIX = ".tmp"


class FilesystemSink:
    """Persists rendered debrief bytes to a directory (port: DebriefSink)."""

    def __init__(self, output_dir: Path | str) -> None:
        self._output_dir = Path(output_dir)

    def write(
        self, name: str, content: bytes, suffix: str, output_dir: str = ""
    ) -> str:
        """Write ``content`` as ``name.suffix`` atomically; return its path.

        Writes into ``output_dir`` when given, otherwise the configured default
        directory. The chosen directory is created if absent. The bytes are
        first written to a sibling temporary file and then moved into place with
        ``os.replace``, which is atomic on one filesystem, so a concurrent
        reader sees either the old file or the whole new one, never a partial.
        """
        destination = Path(output_dir) if output_dir else self._output_dir
        destination.mkdir(parents=True, exist_ok=True)
        filename = f"{name}{_SUFFIX_SEPARATOR}{suffix}"
        target = destination / filename
        temporary = destination / f"{filename}{_TEMP_SUFFIX}"
        temporary.write_bytes(content)
        os.replace(temporary, target)
        return str(target)
