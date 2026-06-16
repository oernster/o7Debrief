"""Dev utility: render docs/example-report.html from the live HtmlDebriefExporter.

Builds a representative multi-domain sample session and renders it through the
real presenter and HTML exporter, so the published example always matches what
the app produces: the tabbed session log, the ship name and the current footer.
This is a development tool, not part of the shipped app. Run from the repo root:

    .\\venv\\Scripts\\python.exe tools\\generate_example_report.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from o7debrief.application.services.config_loading_service import (  # noqa: E402
    ConfigLoadingService,
)
from o7debrief.application.services.debrief_presenter import (  # noqa: E402
    DebriefPresenter,
    NumberFormat,
)
from o7debrief.domain.aggregation.debrief_assembler import (  # noqa: E402
    STAR_SYSTEM_FIELD,
)
from o7debrief.domain.model.conceptual_moment import ConceptualMoment  # noqa: E402
from o7debrief.domain.model.rank_delta import RankDelta  # noqa: E402
from o7debrief.domain.model.rollups import (  # noqa: E402
    ActivityRollup,
    CombatRollup,
    EngineeringRollup,
    ExobiologyRollup,
    ExplorationRollup,
    FlightRollup,
    MiningRollup,
    MissionRollup,
    OnFootRollup,
    SrvRollup,
    TradeRollup,
)
from o7debrief.domain.model.session_debrief import SessionDebrief  # noqa: E402
from o7debrief.domain.value_objects.commander_id import CommanderId  # noqa: E402
from o7debrief.domain.value_objects.credits import Credits  # noqa: E402
from o7debrief.domain.value_objects.enums import (  # noqa: E402
    ActivityDomain,
    ActivityMode,
    MomentKind,
    RankLadder,
)
from o7debrief.domain.value_objects.event_time import EventTime  # noqa: E402
from o7debrief.domain.value_objects.session_window import (  # noqa: E402
    SessionWindow,
)
from o7debrief.domain.value_objects.system_name import SystemName  # noqa: E402
from o7debrief.infrastructure import TomlConfigProvider  # noqa: E402
from o7debrief.infrastructure.render.html_renderer import (  # noqa: E402
    HtmlDebriefExporter,
)

_TAXONOMY = _ROOT / "config" / "debrief_taxonomy.toml"
_OUT = _ROOT / "docs" / "example-report.html"
_DATE = "2026-06-15"
_NET_CREDITS = 7677000

# One row per session-log moment: (kind, domain, mode, time, label, credits,
# system). The label is the displayed text; the domain decides its category
# tab; credits feed the milestone scan. Enum members are named as strings so
# the table stays readable.
_MOMENTS = (
    ("JUMP", "TRAVEL", "SHIP", "19:02:10", "Jumped to", 0, "LHS 3447"),
    ("JUMP", "TRAVEL", "SHIP", "19:05:30", "Jumped to", 0, "Diaguandri"),
    ("HONK", "EXPLORATION", "SHIP", "19:08:00", "Discovery scan", 0, "Diaguandri"),
    ("SCAN_BODY", "EXPLORATION", "SHIP", "19:10:00", "Scanned a body", 0, None),
    ("SCAN_BODY", "EXPLORATION", "SHIP", "19:12:00", "Scanned a body", 0, None),
    ("MAP_BODY", "EXPLORATION", "SHIP", "19:14:00", "Mapped a body", 0, None),
    ("BOUNTY", "COMBAT", "SHIP", "19:20:00", "Collected a bounty", 725000, None),
    ("BOUNTY", "COMBAT", "SHIP", "19:22:00", "Collected a bounty", 0, None),
    ("BOND", "COMBAT", "SHIP", "19:25:00", "Earned a combat bond", 120000, None),
    ("MARKET_BUY", "TRADE", "SHIP", "19:30:00", "Bought cargo", 0, None),
    ("MARKET_SELL", "TRADE", "SHIP", "19:45:00", "Sold cargo", 512000, None),
    ("SELL_EXPLORATION", "EXPLORATION", "SHIP", "19:50:00", "Sold data", 1840000, None),
    ("DISEMBARK", "ON_FOOT", "ON_FOOT", "20:00:00", "Disembarked", 0, None),
    ("EXOBIO_SAMPLE", "EXOBIOLOGY", "ON_FOOT", "20:02:00", "Took a sample", 0, None),
    (
        "EXOBIO_SELL",
        "EXOBIOLOGY",
        "ON_FOOT",
        "20:20:00",
        "Sold organic data",
        3800000,
        None,
    ),
    ("REFINE", "MINING", "SHIP", "20:25:00", "Refined a commodity", 0, None),
    (
        "ENGINEER_CRAFT",
        "ENGINEERING",
        "SHIP",
        "20:30:00",
        "Applied a modification",
        0,
        None,
    ),
    (
        "MISSION_COMPLETE",
        "MISSIONS",
        "SHIP",
        "20:35:00",
        "Completed a mission",
        680000,
        None,
    ),
    ("PROMOTION", "COMBAT", "SHIP", "20:40:00", "Promoted in Combat", 0, None),
    ("SRV_DEPLOY", "SRV", "SRV", "20:45:00", "Deployed the SRV", 0, None),
    (
        "SETTLEMENT_VISIT",
        "ON_FOOT",
        "ON_FOOT",
        "20:50:00",
        "Visited a settlement",
        0,
        None,
    ),
)


def _moments() -> tuple[ConceptualMoment, ...]:
    """Turn the moment table into ordered ConceptualMoments for the timeline."""
    built = []
    for kind, domain, mode, clock, label, credits, system in _MOMENTS:
        detail = ((STAR_SYSTEM_FIELD, system),) if system else ()
        built.append(
            ConceptualMoment(
                kind=MomentKind[kind],
                domain=ActivityDomain[domain],
                mode=ActivityMode[mode],
                occurred_at=EventTime.parse(f"{_DATE}T{clock}Z"),
                label=label,
                magnitude=0,
                credits_delta=Credits(credits),
                detail=detail,
            )
        )
    return tuple(built)


def _activity() -> ActivityRollup:
    """A populated rollup across the domains, driving the headline and cards."""
    return ActivityRollup(
        flight=FlightRollup(jumps=2, distance_ly=55),
        exploration=ExplorationRollup(
            bodies_scanned=2,
            bodies_mapped=1,
            honks=1,
            data_sold=Credits(1840000),
        ),
        combat=CombatRollup(kills=3, bounties=Credits(725000), bonds=Credits(120000)),
        trade=TradeRollup(buys=1, sells=1, spent=Credits(0), earned=Credits(512000)),
        mining=MiningRollup(refined=1),
        missions=MissionRollup(completed=1, rewards=Credits(680000)),
        engineering=EngineeringRollup(crafted=1),
        exobiology=ExobiologyRollup(samples=1, sold=Credits(3800000)),
        srv=SrvRollup(deployments=1),
        on_foot=OnFootRollup(disembarks=1, settlements=1),
        modes_used=(ActivityMode.SHIP, ActivityMode.SRV, ActivityMode.ON_FOOT),
    )


def _ranks() -> tuple[RankDelta, ...]:
    """Two promoted ladders for the rank-progress section."""
    return (
        RankDelta(
            ladder=RankLadder.COMBAT,
            from_tier=0,
            to_tier=5,
            promoted=True,
            start_pct=80,
            end_pct=35,
            growth_pct=None,
            tier_ups=5,
        ),
        RankDelta(
            ladder=RankLadder.EXPLORE,
            from_tier=1,
            to_tier=3,
            promoted=True,
            start_pct=60,
            end_pct=20,
            growth_pct=None,
            tier_ups=2,
        ),
    )


def _debrief() -> SessionDebrief:
    """Assemble the complete sample SessionDebrief."""
    return SessionDebrief(
        commander=CommanderId(fid="F1234", name="Jameson"),
        window=SessionWindow(
            start=EventTime.parse(f"{_DATE}T19:00:00Z"),
            end=EventTime.parse(f"{_DATE}T21:00:00Z"),
            clean_shutdown=True,
        ),
        start_system=SystemName("LHS 3447"),
        end_system=SystemName("Diaguandri"),
        net_credits_delta=Credits(_NET_CREDITS),
        moments=_moments(),
        activity=_activity(),
        rank_progression=_ranks(),
        config_schema_version="1",
        ship="Cobra Mk III",
        ship_name="Stardust",
    )


def _number_format() -> NumberFormat:
    """Read the display NumberFormat from the taxonomy [format] table."""
    with _TAXONOMY.open("rb") as handle:
        table = tomllib.load(handle)["format"]
    return NumberFormat(
        credits_suffix=table["credits_suffix"],
        distance_suffix=table["distance_suffix"],
        thousands=table["thousands"],
        duration_format=table["duration_format"],
        time_format=table["time_format"],
        datetime_format=table["datetime_format"],
    )


def main() -> int:
    """Render the sample debrief to docs/example-report.html."""
    spec = ConfigLoadingService(TomlConfigProvider(str(_TAXONOMY))).load_spec()
    view = DebriefPresenter(spec, _number_format()).present(_debrief())
    html = HtmlDebriefExporter().render(view).decode("utf-8")
    _OUT.write_text(html, encoding="utf-8")
    print(f"wrote {_OUT} ({len(html)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
