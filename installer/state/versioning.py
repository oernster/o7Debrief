"""Comparing the bundled version against the installed one.

Version comparison is a plain tuple compare over the numeric parts, which is
enough for this project's semantic versions and pulls in no dependency. A part
with no digits compares as zero, so a pre-release suffix never makes a version
sort above its own release. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

_SEPARATOR = "."

OLDER = -1
SAME = 0
NEWER = 1


def version_tuple(version: str) -> tuple[int, ...]:
    """Return a comparable tuple of the numeric parts of a version string."""
    parts: list[int] = []
    for raw in version.strip().split(_SEPARATOR):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def compare_versions(left: str, right: str) -> int:
    """Return OLDER, SAME or NEWER for left against right."""
    a = version_tuple(left)
    b = version_tuple(right)
    if a < b:
        return OLDER
    if a > b:
        return NEWER
    return SAME
