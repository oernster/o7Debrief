"""Incremental tail reader for append-only journal files.

This is the byte-offset plus partial-line algorithm lifted from the author's
EDColonisationAsst journal ingestion, reduced to a single pure function with no
watchdog, asyncio or colonisation concerns. Elite Dangerous appends journal
lines one at a time; reading while the game is mid-write can yield a final line
with no trailing newline. The reader therefore returns any trailing partial so
the caller can prepend it on the next pass, guaranteeing no event is lost or
double-counted.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["TailResult", "read_new_bytes", "EMPTY_OFFSET", "NO_PARTIAL"]

# A fresh read starts at byte zero with no carried-over partial line.
EMPTY_OFFSET = 0
NO_PARTIAL = b""

# The newline byte that terminates each complete journal line.
_NEWLINE = b"\n"
# Index of the last split part (the trailing, possibly incomplete, line).
_TRAILING = -1
# Slice end excluding the trailing part: all parts known to be complete.
_COMPLETE_END = -1


@dataclass(frozen=True, slots=True)
class TailResult:
    """The outcome of one incremental read of a journal file.

    ``complete_lines`` holds the newly completed, non-empty, decoded lines in
    file order. ``new_offset`` is the byte position to resume from next time,
    and ``new_partial`` is any trailing bytes not yet terminated by a newline.
    """

    complete_lines: tuple[str, ...]
    new_offset: int
    new_partial: bytes


def _normalise_for_rotation(
    path: Path, since_offset: int, partial: bytes
) -> tuple[int, bytes]:
    """Reset the offset and partial when the file shrank (rotation/truncation).

    If the file is now smaller than the offset we previously recorded, the file
    was rotated or truncated, so we must start again from the beginning.
    """
    try:
        current_size = path.stat().st_size
    except OSError:
        current_size = EMPTY_OFFSET
    if current_size < since_offset:
        return EMPTY_OFFSET, NO_PARTIAL
    return since_offset, partial


def _split_lines(buffer: bytes) -> tuple[list[bytes], bytes]:
    """Split a byte buffer into complete line parts and a trailing remainder.

    The remainder is ``b""`` when the buffer ended on a newline; otherwise it
    is the unterminated final line to be carried over to the next read.
    """
    parts = buffer.split(_NEWLINE)
    complete = parts[:_COMPLETE_END]
    remainder = parts[_TRAILING]
    return complete, remainder


def _decode_complete(parts: list[bytes]) -> tuple[str, ...]:
    """Decode complete line parts to stripped, non-empty UTF-8 strings.

    Decoding replaces undecodable bytes rather than failing, matching the
    tolerant per-line behaviour the journal reader needs.
    """
    lines: list[str] = []
    for part in parts:
        if not part:
            continue
        text = part.decode("utf-8", errors="replace").strip()
        if text:
            lines.append(text)
    return tuple(lines)


def read_new_bytes(
    path: Path,
    since_offset: int = EMPTY_OFFSET,
    partial: bytes = NO_PARTIAL,
) -> TailResult:
    """Read bytes appended to ``path`` since ``since_offset`` and split lines.

    The carried-over ``partial`` from the previous call is prepended to the
    freshly read bytes before splitting. Returns the completed lines, the new
    byte offset to resume from and any new trailing partial. A missing or
    unreadable file yields no lines and leaves the offset unchanged.
    """
    start_offset, carried = _normalise_for_rotation(path, since_offset, partial)

    try:
        with open(path, "rb") as handle:
            handle.seek(start_offset)
            chunk = handle.read()
    except OSError:
        return TailResult((), start_offset, carried)

    new_offset = start_offset + len(chunk)
    buffer = carried + chunk
    complete_parts, remainder = _split_lines(buffer)
    return TailResult(_decode_complete(complete_parts), new_offset, remainder)
