"""Tolerant JSON line parsing for journal files.

Adapted from the author's EDColonisationAsst journal parser: the JSON-decode and
tolerant-per-line shape, with the colonisation event routing removed. Each
journal line is a JSON object; a line that is blank or not a JSON object is
skipped rather than raising, so one corrupt line never aborts a whole file.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["parse_line", "parse_lines", "read_lines"]

# The byte-order mark an editor may write at the start of a re-saved file. The
# game never writes one; JSON refuses it, so it would cost the first line.
# Removed here rather than at each decode because both the cold read and the
# live tail pass every line through this function.
_BYTE_ORDER_MARK = "﻿"


def parse_line(line: str) -> dict[str, Any] | None:
    """Parse one journal line into a dict or None if it is not a JSON object.

    Whitespace and a leading byte-order mark are stripped first. Invalid JSON
    or JSON that is not an object (for example a bare array or number) yields
    None so the caller can skip it.
    """
    text = line.strip().lstrip(_BYTE_ORDER_MARK)
    if not text:
        return None
    try:
        decoded = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(decoded, dict):
        return decoded
    return None


def parse_lines(lines: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    """Parse many lines, dropping any that are not JSON objects."""
    parsed: list[dict[str, Any]] = []
    for line in lines:
        record = parse_line(line)
        if record is not None:
            parsed.append(record)
    return tuple(parsed)


def read_lines(path: Path) -> tuple[str, ...]:
    """Return every line of a journal file, unparsed, for ``parse_lines``.

    The lines are handed back raw so a caller can tell how many held something
    from how many became records. A missing or unreadable file yields an empty
    tuple rather than raising, so a transient read error degrades gracefully.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return tuple(handle.readlines())
    except OSError:
        return ()
