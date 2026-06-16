"""JsonRankSnapshotStore: persist per-commander rank snapshots as JSON.

This adapter implements the application ``RankSnapshotStore`` port. Each
commander's last-known rank state is stored as a small JSON file under a
configured directory, keyed by the commander's frontier id, and written
atomically (a temporary file plus ``os.replace``) so a snapshot is never left
half-written. A missing or unreadable snapshot loads as None, so the first ever
run simply has no prior state to compare against.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.domain.value_objects.commander_id import CommanderId

__all__ = ["JsonRankSnapshotStore"]

# JSON keys for a stored snapshot.
_FID = "commander_fid"
_TIERS = "tiers"
_PCTS = "pcts"
_CAPTURED = "captured_iso"

# Filename shape for a commander's snapshot and the atomic-write temp suffix.
_FILE_PREFIX = "rank_"
_FILE_SUFFIX = ".json"
_TEMP_SUFFIX = ".tmp"
# Character substituted for any filesystem-unsafe character in a frontier id.
_SAFE_CHAR = "_"
# Encoding used for the JSON snapshot files.
_ENCODING = "utf-8"
# Number of elements in a serialised (key, value) pair.
_PAIR_LEN = 2
# Captured-time used when a stored snapshot omits one.
_EMPTY_CAPTURED = ""


def _safe_fid(fid: str) -> str:
    """Return a filesystem-safe form of a frontier id for use in a filename."""
    return "".join(char if char.isalnum() else _SAFE_CHAR for char in fid)


def _pairs_to_lists(pairs: tuple[tuple[str, int], ...]) -> list[list]:
    """Convert (key, value) pairs to JSON-friendly [key, value] lists."""
    return [[key, value] for key, value in pairs]


def _lists_to_pairs(raw: object) -> tuple[tuple[str, int], ...]:
    """Convert decoded [key, value] lists back to a tuple of (key, value).

    Anything not shaped like a list of two-element [str, int] lists is dropped,
    so a corrupt or hand-edited snapshot degrades to empty rather than raising.
    """
    if not isinstance(raw, list):
        return ()
    pairs: list[tuple[str, int]] = []
    for item in raw:
        if isinstance(item, list) and len(item) == _PAIR_LEN:
            key, value = item
            if (
                isinstance(key, str)
                and isinstance(value, int)
                and not isinstance(value, bool)
            ):
                pairs.append((key, value))
    return tuple(pairs)


def _snapshot_from(data: dict, fallback_fid: str) -> RankSnapshot:
    """Build a RankSnapshot from a decoded JSON dict, tolerating odd shapes."""
    fid = data.get(_FID)
    return RankSnapshot(
        commander_fid=fid if isinstance(fid, str) and fid else fallback_fid,
        tiers=_lists_to_pairs(data.get(_TIERS)),
        pcts=_lists_to_pairs(data.get(_PCTS)),
        captured_iso=str(data.get(_CAPTURED, _EMPTY_CAPTURED)),
    )


class JsonRankSnapshotStore:
    """Stores per-commander rank snapshots as JSON (port: RankSnapshotStore)."""

    def __init__(self, directory: Path | str) -> None:
        self._directory = Path(directory)

    def load(self, commander: CommanderId) -> RankSnapshot | None:
        """Return the saved snapshot for a commander, or None if absent."""
        path = self._path_for(commander.fid)
        try:
            text = path.read_text(encoding=_ENCODING)
        except OSError:
            return None
        try:
            data = json.loads(text)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        return _snapshot_from(data, commander.fid)

    def save(self, commander: CommanderId, snapshot: RankSnapshot) -> None:
        """Persist a commander's snapshot atomically as JSON."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._path_for(commander.fid)
        temporary = path.with_name(f"{path.name}{_TEMP_SUFFIX}")
        payload = {
            _FID: snapshot.commander_fid,
            _TIERS: _pairs_to_lists(snapshot.tiers),
            _PCTS: _pairs_to_lists(snapshot.pcts),
            _CAPTURED: snapshot.captured_iso,
        }
        temporary.write_text(json.dumps(payload), encoding=_ENCODING)
        os.replace(temporary, path)

    def _path_for(self, fid: str) -> Path:
        """Return the snapshot file path for a frontier id."""
        return self._directory / f"{_FILE_PREFIX}{_safe_fid(fid)}{_FILE_SUFFIX}"
