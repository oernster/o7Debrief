"""FilesystemBundleSink: write a bundle to a directory, touching only changes.

This adapter implements the application ``DebriefBundleSink`` port. It writes
each file of a bundle into one stable directory, comparing the bytes it is
about to write against the bytes already there and skipping any file that has
not moved. A history report is regenerated on every quit, so after a short
session that is one index and one page written and every older page left
exactly as it was, with no bookkeeping to keep in step and nothing to seal.

Files under the bundle's own pages directory that the bundle no longer
contains are removed, so a change of paging or a switch to rolled-up mode does
not leave orphan pages behind that navigation no longer reaches. The pruning
is confined to that one generated directory and to the bundle's own file type,
so nothing a reader put there is at risk.

Every write goes through a temporary file and an atomic replace, so a reader
refreshing the report mid-write sees the old file or the whole new one.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
from pathlib import Path

from o7debrief.application.dto.bundle import DebriefBundle
from o7debrief.application.ports.debrief_bundle_sink import BundleWriteResult

__all__ = ["FilesystemBundleSink"]

# Suffix of the temporary file written before the atomic replace into place.
_TEMP_SUFFIX = ".tmp"
# The subdirectory whose stale files are pruned. Only generated pages live
# here, so it is the one place a removal is safe without asking.
_PAGES_DIR = "pages"


class FilesystemBundleSink:
    """Persists a bundle to a directory (port: DebriefBundleSink)."""

    def __init__(self, output_dir: Path | str) -> None:
        self._output_dir = Path(output_dir)

    def write_bundle(
        self, bundle: DebriefBundle, output_dir: str = ""
    ) -> BundleWriteResult:
        """Write the bundle's changed files; return what moved and what did not."""
        base = Path(output_dir) if output_dir else self._output_dir
        root = base / bundle.directory_name
        written: list[str] = []
        skipped: list[str] = []
        for item in bundle.files:
            target = root / item.relative_path
            if _is_unchanged(target, item.content):
                skipped.append(str(target))
                continue
            _write_atomically(target, item.content)
            written.append(str(target))
        removed = _prune(root, bundle)
        return BundleWriteResult(
            entry_path=str(root / bundle.entry_point),
            written=tuple(written),
            skipped=tuple(skipped),
            removed=tuple(removed),
        )


def _is_unchanged(target: Path, content: bytes) -> bool:
    """Return whether the file already holds exactly these bytes."""
    if not target.is_file():
        return False
    return target.read_bytes() == content


def _write_atomically(target: Path, content: bytes) -> None:
    """Write the bytes to the target through a sibling temporary file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}{_TEMP_SUFFIX}")
    temporary.write_bytes(content)
    os.replace(temporary, target)


def _prune(root: Path, bundle: DebriefBundle) -> list[str]:
    """Remove generated pages the bundle no longer contains."""
    pages = root / _PAGES_DIR
    if not pages.is_dir():
        return []
    wanted = {
        (root / item.relative_path).resolve()
        for item in bundle.files
        if item.relative_path.startswith(f"{_PAGES_DIR}/")
    }
    suffix = Path(bundle.entry_point).suffix
    removed: list[str] = []
    for entry in sorted(pages.iterdir()):
        if not entry.is_file() or entry.suffix != suffix:
            continue
        if entry.resolve() in wanted:
            continue
        entry.unlink()
        removed.append(str(entry))
    return removed
