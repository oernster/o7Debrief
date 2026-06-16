"""Pure semantic-version comparison for the update check.

``is_newer`` answers a single question: is ``latest`` a newer release than
``current``? Both are dotted version strings with an optional leading "v" (for
example "v1.2.0"). A version that cannot be parsed as dotted integers is treated
as not-newer, so a malformed tag can never trigger a spurious update prompt.

This is application-layer logic with no domain meaning of its own and no I/O, so
it lives beside the update service that uses it. British spelling is used in
comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["is_newer"]

# Optional release-tag prefix stripped before parsing (for example "v1.2.0").
_TAG_PREFIX = "v"
# Separator between version components.
_COMPONENT_SEPARATOR = "."


def _parts(version: str) -> tuple[int, ...] | None:
    """Return a version's integer components, or None when it is malformed."""
    text = version.strip()
    if text[:1].lower() == _TAG_PREFIX:
        text = text[1:]
    try:
        return tuple(int(part) for part in text.split(_COMPONENT_SEPARATOR))
    except ValueError:
        return None


def is_newer(latest: str, current: str) -> bool:
    """Return True when ``latest`` is a strictly newer version than ``current``."""
    latest_parts = _parts(latest)
    current_parts = _parts(current)
    if latest_parts is None or current_parts is None:
        return False
    return latest_parts > current_parts
