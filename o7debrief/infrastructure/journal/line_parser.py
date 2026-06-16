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

__all__ = ["parse_line", "parse_lines", "parse_file"]


def parse_line(line: str) -> dict[str, Any] | None:
    """Parse one journal line into a dict, or None if it is not a JSON object.

    Whitespace is stripped first. Invalid JSON, or JSON that is not an object
    (for example a bare array or number), yields None so the caller can skip it.
    """
    text = line.strip()
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


def parse_file(path: Path) -> tuple[dict[str, Any], ...]:
    """Parse every line of a journal file into dicts, tolerating bad lines.

    A missing or unreadable file yields an empty tuple rather than raising, so
    a transient read error degrades gracefully.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            raw_lines = tuple(handle.readlines())
    except OSError:
        return ()
    return parse_lines(raw_lines)
