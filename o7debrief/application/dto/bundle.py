"""DebriefBundle DTO: a debrief rendered as a small set of related files.

A session report is one self-contained file and stays one, because it is small
and being able to hand the whole thing to somebody is the point of it. A whole
history is not small and grows on every quit, so it is rendered as a bundle
instead: an index, a page per period, and one stylesheet shared by all of them
rather than the same ``:root`` block repeated on every page.

The bundle is described here in terms of relative paths and bytes alone, so
the application layer never learns what a directory is; the sink turns these
into files. ``entry_point`` names the file a reader opens, which is what the
archive lists and what the tray opens after a run.

This module belongs to the application layer and imports the standard library
only. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["BundleFile", "DebriefBundle"]


@dataclass(frozen=True, slots=True)
class BundleFile:
    """One file in a bundle: where it sits, and what is in it."""

    relative_path: str
    content: bytes


@dataclass(frozen=True, slots=True)
class DebriefBundle:
    """A rendered debrief as a directory name, an entry point and its files."""

    directory_name: str
    entry_point: str
    files: tuple[BundleFile, ...]
