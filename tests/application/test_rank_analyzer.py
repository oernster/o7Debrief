"""Tests for the RankAnalyzer commander and rank-progression reader."""

from __future__ import annotations

from tests.application.fakes import event

from o7debrief.application.services.rank_analyzer import RankAnalyzer
from o7debrief.domain.value_objects.enums import RankLadder


def _analyzer() -> RankAnalyzer:
    return RankAnalyzer()


def test_extract_commander_reads_name_and_fid_from_commander_event() -> None:
    events = (event("Commander", 0, Name="Jameson", FID="F42"),)

    result = _analyzer().extract_commander(events)

    assert result is not None
    assert result.name == "Jameson"
    assert result.fid == "F42"


def test_extract_commander_reads_name_from_load_game_commander_field() -> None:
    # LoadGame uses the "Commander" field for the name and has no FID, so the
    # fid falls back to the name.
    events = (event("LoadGame", 0, Commander="Hera"),)

    result = _analyzer().extract_commander(events)

    assert result is not None
    assert result.name == "Hera"
    assert result.fid == "Hera"


def test_extract_commander_skips_events_without_a_name() -> None:
    events = (
        event("FSDJump", 0, StarSystem="Sol"),
        event("Commander", 1),
        event("Commander", 2, Name="Real"),
    )

    result = _analyzer().extract_commander(events)

    assert result is not None
    assert result.name == "Real"


def test_extract_commander_returns_none_when_nothing_identifies() -> None:
    events = (event("FSDJump", 0, StarSystem="Sol"),)

    assert _analyzer().extract_commander(events) is None


def test_analyse_reads_current_tier_from_rank_event() -> None:
    # The Rank event is the source of current tiers. With no snapshot a ladder
    # reads as unchanged at that tier rather than a promotion from zero.
    events = (event("Rank", 1, Empire=14, Federation=14),)

    deltas, end_pcts = _analyzer().analyse(events, (), ())

    assert end_pcts is None
    by_ladder = {d.ladder: d for d in deltas}
    assert by_ladder[RankLadder.EMPIRE].to_tier == 14
    assert by_ladder[RankLadder.EMPIRE].promoted is False
    assert by_ladder[RankLadder.FEDERATION].to_tier == 14


def test_analyse_marks_promotion_against_a_snapshot() -> None:
    # A higher current tier than the saved snapshot reads as a promotion.
    events = (event("Rank", 1, Combat=4),)

    deltas, _ = _analyzer().analyse(events, (("combat", 2),), ())

    combat = next(d for d in deltas if d.ladder == RankLadder.COMBAT)
    assert combat.from_tier == 2
    assert combat.to_tier == 4
    assert combat.promoted is True


def test_analyse_separates_rank_tiers_from_progress_pcts() -> None:
    # Rank carries tiers and Progress carries percentages; they share field
    # keys but must not be conflated by the reader.
    events = (event("Rank", 0, Combat=8), event("Progress", 1, Combat=50))

    deltas, end_pcts = _analyzer().analyse(events, (("combat", 8),), (("combat", 0),))

    combat = next(d for d in deltas if d.ladder == RankLadder.COMBAT)
    assert combat.to_tier == 8
    assert combat.end_pct == 50
    assert end_pcts == (("combat", 50),)


def test_analyse_uses_snapshot_starts_and_progress() -> None:
    # Start state arrives as ladder-key strings; an unknown key is dropped and
    # a boolean field on the Progress event is ignored by the integer reader.
    start_tiers = (("trade", 3), ("unknown_key", 9))
    start_pcts = (("trade", 20),)
    events = (
        event("Rank", 0, Trade=3),
        event("Progress", 1, Trade=55, Horizons=True),
        event("Progress", 2, Trade=70),
    )

    deltas, end_pcts = _analyzer().analyse(events, start_tiers, start_pcts)

    assert end_pcts == (("trade", 70),)
    trade = next(d for d in deltas if d.ladder == RankLadder.TRADE)
    assert trade.from_tier == 3
    assert trade.to_tier == 3
    assert trade.start_pct == 20
    assert trade.end_pct == 70
    assert trade.growth_pct == 50


def test_analyse_latest_tier_value_wins() -> None:
    # Two records on the same ladder: the later value wins as the current tier.
    events = (
        event("Promotion", 1, Combat=3),
        event("Promotion", 2, Combat=4),
    )

    deltas, _ = _analyzer().analyse(events, (), ())

    combat = next(d for d in deltas if d.ladder == RankLadder.COMBAT)
    assert combat.to_tier == 4


def test_analyse_without_rank_or_promotion_yields_no_standing() -> None:
    # Percentages alone (no Rank or Promotion) give no current tier, so there
    # is no standing to report even though the closing percentage is returned.
    events = (event("Progress", 1, Combat=40),)

    deltas, end_pcts = _analyzer().analyse(events, (), ())

    assert deltas == ()
    assert end_pcts == (("combat", 40),)
