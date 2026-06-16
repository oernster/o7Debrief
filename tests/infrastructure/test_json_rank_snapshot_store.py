"""Tests for JsonRankSnapshotStore: round-trip, absence and corruption."""

from __future__ import annotations

from pathlib import Path

from o7debrief.application.dto.rank_snapshot import RankSnapshot
from o7debrief.domain.value_objects.commander_id import CommanderId
from o7debrief.infrastructure.rank.json_rank_snapshot_store import (
    JsonRankSnapshotStore,
)

_CAPTURED = "2026-06-15T20:00:00+00:00"


def _commander(fid: str = "F1234") -> CommanderId:
    return CommanderId(fid=fid, name="Jameson")


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    store = JsonRankSnapshotStore(tmp_path)
    snapshot = RankSnapshot(
        commander_fid="F1234",
        tiers=(("combat", 4), ("trade", 2)),
        pcts=(("combat", 10),),
        captured_iso=_CAPTURED,
    )

    store.save(_commander(), snapshot)

    assert store.load(_commander()) == snapshot


def test_load_returns_none_when_absent(tmp_path: Path) -> None:
    store = JsonRankSnapshotStore(tmp_path)

    assert store.load(_commander("UNSEEN")) is None


def test_load_returns_none_on_corrupt_file(tmp_path: Path) -> None:
    store = JsonRankSnapshotStore(tmp_path)
    snapshot = RankSnapshot(
        commander_fid="F1234", tiers=(), pcts=(), captured_iso=_CAPTURED
    )
    store.save(_commander(), snapshot)
    # Corrupt the only stored file so the decode fails.
    stored = next(Path(tmp_path).glob("rank_*.json"))
    stored.write_text("{not valid json", encoding="utf-8")

    assert store.load(_commander()) is None


def test_unsafe_fid_is_sanitised_but_still_roundtrips(tmp_path: Path) -> None:
    store = JsonRankSnapshotStore(tmp_path)
    commander = _commander("F/12:34")
    snapshot = RankSnapshot(
        commander_fid="F/12:34", tiers=(("combat", 1),), pcts=(), captured_iso=_CAPTURED
    )

    store.save(commander, snapshot)

    files = list(Path(tmp_path).glob("rank_*.json"))
    assert len(files) == 1
    assert "/" not in files[0].name and ":" not in files[0].name
    assert store.load(commander) == snapshot
