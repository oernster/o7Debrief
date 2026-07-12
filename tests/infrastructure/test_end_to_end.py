"""End-to-end test of the one-shot debrief over the real adapters.

Wires the concrete infrastructure adapters (the real taxonomy, real journal
files in a temporary directory, the filesystem sink and the JSON rank store)
into the application one-shot use case and proves the whole pipeline: session
isolation, real credit rollups and both output formats written.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from o7debrief.application.services.debrief_builder import DebriefBuilder
from o7debrief.application.services.debrief_export_service import (
    DebriefExportService,
)
from o7debrief.application.services.debrief_presenter import (
    DebriefPresenter,
    NumberFormat,
)
from o7debrief.application.services.one_shot_debrief_service import (
    OneShotDebriefService,
)
from o7debrief.application.services.rank_analyzer import RankAnalyzer
from o7debrief.infrastructure.clock.system_clock import SystemClock
from o7debrief.infrastructure.config.toml_config_provider import TomlConfigProvider
from o7debrief.infrastructure.journal.file_journal_source import FileJournalSource
from o7debrief.infrastructure.preferences.json_preferences_store import (
    JsonPreferencesStore,
)
from o7debrief.infrastructure.rank.json_rank_snapshot_store import (
    JsonRankSnapshotStore,
)
from o7debrief.infrastructure.render.html_renderer import HtmlDebriefExporter
from o7debrief.infrastructure.render.markdown_renderer import MarkdownDebriefExporter
from o7debrief.infrastructure.sink.filesystem_sink import FilesystemSink

# Credit values the latest session earns; net credits is their sum.
_BOUNTY = 500000
_TRADE = 300000

_OLDER_SESSION = [
    {
        "timestamp": "2026-06-14T10:00:00Z",
        "event": "LoadGame",
        "Commander": "Jameson",
        "FID": "F90",
    },
    {
        "timestamp": "2026-06-14T10:05:00Z",
        "event": "FSDJump",
        "StarSystem": "Lave",
        "JumpDist": 12,
    },
    {"timestamp": "2026-06-14T10:10:00Z", "event": "Shutdown"},
]
_LATEST_SESSION = [
    {
        "timestamp": "2026-06-15T20:00:00Z",
        "event": "LoadGame",
        "Commander": "Jameson",
        "FID": "F90",
    },
    {
        "timestamp": "2026-06-15T20:05:00Z",
        "event": "FSDJump",
        "StarSystem": "Sol",
        "JumpDist": 8,
    },
    {
        "timestamp": "2026-06-15T20:06:00Z",
        "event": "Bounty",
        "Target": "Pirate",
        "TotalReward": _BOUNTY,
    },
    {
        "timestamp": "2026-06-15T20:10:00Z",
        "event": "MarketSell",
        "Type": "Gold",
        "Count": 5,
        "TotalSale": _TRADE,
    },
    {"timestamp": "2026-06-15T20:30:00Z", "event": "Shutdown"},
]

# A SellOrganicData payload carries no top-level credit total: the value is the
# sum of each BioData entry's Value and first-discovery Bonus. These feed the
# regression below, whose total is their sum.
_EXOBIO_VALUE_ONE = 1500000
_EXOBIO_BONUS_ONE = 1500000
_EXOBIO_VALUE_TWO = 500000
_EXOBIO_TOTAL = _EXOBIO_VALUE_ONE + _EXOBIO_BONUS_ONE + _EXOBIO_VALUE_TWO

_EXOBIO_SESSION = [
    {
        "timestamp": "2026-06-16T09:00:00Z",
        "event": "LoadGame",
        "Commander": "Jameson",
        "FID": "F90",
    },
    {
        "timestamp": "2026-06-16T09:30:00Z",
        "event": "SellOrganicData",
        "MarketID": 3700062976,
        "BioData": [
            {
                "Genus": "$Codex_Ent_Bacterial_Genus_Name;",
                "Species": "$Codex_Ent_Bacterial_05_Name;",
                "Value": _EXOBIO_VALUE_ONE,
                "Bonus": _EXOBIO_BONUS_ONE,
            },
            {
                "Genus": "$Codex_Ent_Stratum_Genus_Name;",
                "Species": "$Codex_Ent_Stratum_02_Name;",
                "Value": _EXOBIO_VALUE_TWO,
                "Bonus": 0,
            },
        ],
    },
    {"timestamp": "2026-06-16T10:00:00Z", "event": "Shutdown"},
]


def _taxonomy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "debrief_taxonomy.toml"


def _number_format(path: Path) -> NumberFormat:
    with open(path, "rb") as handle:
        table = tomllib.load(handle)["format"]
    return NumberFormat(
        credits_suffix=table["credits_suffix"],
        coins_suffix=table["coins_suffix"],
        distance_suffix=table["distance_suffix"],
        thousands=table["thousands"],
        duration_format=table["duration_format"],
        time_format=table["time_format"],
        datetime_format=table["datetime_format"],
    )


def _one_shot(journal_dir, export_dir, state_dir) -> OneShotDebriefService:
    taxonomy = _taxonomy_path()
    spec = TomlConfigProvider(taxonomy).load()
    export_service = DebriefExportService(
        (MarkdownDebriefExporter(), HtmlDebriefExporter()),
        FilesystemSink(export_dir),
        SystemClock(),
    )
    return OneShotDebriefService(
        journal_source=FileJournalSource(journal_dir),
        debrief_builder=DebriefBuilder(spec),
        presenter=DebriefPresenter(spec, _number_format(taxonomy)),
        export_service=export_service,
        preferences_store=JsonPreferencesStore(state_dir),
        rank_store=JsonRankSnapshotStore(state_dir),
        rank_analyzer=RankAnalyzer(),
        clock=SystemClock(),
    )


def test_one_shot_writes_the_default_html_format(
    tmp_path, journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _OLDER_SESSION + _LATEST_SESSION)

    result = _one_shot(
        journal_dir, tmp_path / "debriefs", tmp_path / "state"
    ).debrief_last_session()

    # The default preference is HTML, so exactly one HTML file is written.
    assert [Path(p).suffix for p in result.paths] == [".html"]
    assert Path(result.paths[0]).exists()


def test_one_shot_isolates_latest_session_and_sums_credits(
    tmp_path, journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _OLDER_SESSION + _LATEST_SESSION)

    result = _one_shot(
        journal_dir, tmp_path / "debriefs", tmp_path / "state"
    ).debrief_last_session()
    html = next(Path(p) for p in result.paths if p.endswith(".html")).read_text(
        encoding="utf-8"
    )

    assert "Jameson" in html
    assert "800,000" in html  # net credits = bounty + trade, digit-grouped
    assert "Sol" in html  # the latest session's system
    assert "Lave" not in html  # the older session is excluded
    # Activity icons reach the page: the bounty shows the combat swords and the
    # sale shows the trade glyph, not a ship, proving rows show the activity.
    assert "⚔️" in html
    assert "\U0001f4b1" in html


def test_one_shot_persists_a_rank_snapshot(
    tmp_path, journal_dir_factory, write_journal_lines
) -> None:
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _LATEST_SESSION)
    state_dir = tmp_path / "state"

    _one_shot(journal_dir, tmp_path / "debriefs", state_dir).debrief_last_session()

    assert len(list(Path(state_dir).glob("rank_*.json"))) == 1


def test_one_shot_sums_exobiology_credits_from_biodata(
    tmp_path, journal_dir_factory, write_journal_lines
) -> None:
    # Regression: SellOrganicData has no top-level credit key, so the exobiology
    # rollup must sum Value and Bonus across BioData. Before the fix this read a
    # missing key and silently rolled up to zero.
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _EXOBIO_SESSION)

    result = _one_shot(
        journal_dir, tmp_path / "debriefs", tmp_path / "state"
    ).debrief_last_session()
    html = next(Path(p) for p in result.paths if p.endswith(".html")).read_text(
        encoding="utf-8"
    )

    assert format(_EXOBIO_TOTAL, ",") in html  # 3,500,000, digit-grouped


def test_all_history_debrief_spans_sessions_and_writes_no_snapshot(
    tmp_path, journal_dir_factory, write_journal_lines
) -> None:
    # The all-history debrief covers every session (both systems appear, unlike
    # the last-session debrief that excludes the older one) and, being a
    # read-only view, it persists no rank snapshot.
    journal_dir = journal_dir_factory()
    write_journal_lines(journal_dir, _OLDER_SESSION + _LATEST_SESSION)
    state_dir = tmp_path / "state"

    result = _one_shot(
        journal_dir, tmp_path / "debriefs", state_dir
    ).debrief_all_history()
    html = next(Path(p) for p in result.paths if p.endswith(".html")).read_text(
        encoding="utf-8"
    )

    assert "Lave" in html
    assert "Sol" in html
    assert list(state_dir.glob("rank_*.json")) == []
