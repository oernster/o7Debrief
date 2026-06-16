"""Shared debrief filename naming, used by the writer and the archive reader.

The export service stamps a generated debrief as ``debrief_<timestamp>`` and the
archive lists existing debriefs by the same stem, so the stem and separator live
here once and both sides import them. A single source means a change to the
naming cannot desynchronise writing from listing.

This module belongs to the application layer and imports the standard library
only. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["NAME_STEM", "NAME_SEPARATOR", "debrief_prefix"]

# Filename stem and separator for a generated debrief, before the timestamp.
NAME_STEM = "debrief"
NAME_SEPARATOR = "_"


def debrief_prefix() -> str:
    """Return the filename prefix shared by every generated debrief."""
    return f"{NAME_STEM}{NAME_SEPARATOR}"
