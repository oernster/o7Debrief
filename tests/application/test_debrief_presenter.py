"""Tests for the DebriefPresenter and its section builders."""

from __future__ import annotations

from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.application.services.presenter_sections import _delta_class
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
    RankLadder,
)


def _presenter(labels: tuple[tuple[str, str], ...] = ()) -> DebriefPresenter:
    return DebriefPresenter(spec(labels), number_format())


def _full_moments():
    """Moments covering all three modes, a long jump, a promotion, big payout."""
    return (
        build.moment(
            MomentKind.JUMP,
            ActivityDomain.TRAVEL,
            1,
            magnitude=60,
            system="Sol",
        ),
        build.moment(
            MomentKind.BOUNTY,
            ActivityDomain.COMBAT,
            2,
            credits=BIG_PAYOUT_MOMENT,
            system="Sol",
        ),
        build.moment(
            MomentKind.SRV_DEPLOY,
            ActivityDomain.SRV,
            3,
            mode=ActivityMode.SRV,
        ),
        build.moment(
            MomentKind.DISEMBARK,
            ActivityDomain.ON_FOOT,
            4,
            mode=ActivityMode.ON_FOOT,
            system="Achenar",
        ),
        build.moment(MomentKind.PROMOTION, ActivityDomain.MISSIONS, 5),
    )


# A moment credit value above the taxonomy big-payout threshold.
BIG_PAYOUT_MOMENT = 2000000


def _full_ranks():
    """One promoted ladder and one steady ladder with growth."""
    return (
        build.rank_delta(
            RankLadder.COMBAT,
            from_tier=3,
            to_tier=4,
            promoted=True,
            start_pct=90,
            end_pct=10,
            growth_pct=None,
            tier_ups=1,
        ),
        build.rank_delta(
            RankLadder.TRADE,
            from_tier=2,
            to_tier=2,
            promoted=False,
            start_pct=20,
            end_pct=55,
            growth_pct=35,
            tier_ups=0,
        ),
    )


def test_present_full_debrief_yields_contract_shape() -> None:
    debrief = build.debrief(
        moments=_full_moments(),
        activity=build.full_activity(),
        ranks=_full_ranks(),
        net_credits=BIG_PAYOUT_MOMENT,
    )

    context = _presenter().present(debrief).to_context()

    # Header: commander, formatted times, systems and a visited count.
    assert context["header"]["commander"] == "Jameson"
    assert context["header"]["start_system"] == "Sol"
    assert context["header"]["end_system"] == "Achenar"
    assert context["header"]["systems_visited"] == "2"
    assert context["header"]["duration"] == "0h 0m"
    # All eleven domains are present, in canonical order starting with travel.
    assert len(context["domains"]) == 11
    assert context["domains"][0]["key"] == "travel"
    # Timeline has one entry per moment with resolved mode strings.
    modes = [entry["mode"] for entry in context["timeline"]]
    assert modes == ["ship", "ship", "srv", "foot", "ship"]
    # Both ladders appear; the promoted one carries no steady note.
    assert len(context["ranks"]) == 2
    assert context["ranks"][0]["promoted"] is True
    assert context["ranks"][0]["note"] == ""
    assert context["ranks"][1]["promoted"] is False
    assert context["ranks"][1]["note"] == "(no change)"
    # Milestones: promotion, big payout and long jump all fire.
    assert len(context["milestones"]) == 3


def test_headline_uses_zero_when_domains_absent() -> None:
    # An activity with no flight/exploration/combat exercises the else paths.
    activity = ActivityRollup(modes_used=())
    debrief = build.debrief(
        moments=(),
        activity=activity,
        net_credits=0,
    )

    context = _presenter().present(debrief).to_context()

    headline = {item["label"]: item for item in context["headline"]}
    assert headline["Jumps"]["value_display"] == "0"
    assert headline["Bodies scanned"]["value_display"] == "0"
    assert headline["Kills"]["value_display"] == "0"


def test_delta_class_covers_all_three_directions() -> None:
    # The helper is direction-general even though net credits are never
    # negative through the domain; assert all three branches directly.
    assert _delta_class(10) == "positive"
    assert _delta_class(0) == "neutral"
    assert _delta_class(-10) == "negative"


def test_headline_neutral_class_when_net_is_zero() -> None:
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        net_credits=0,
    )

    context = _presenter().present(debrief).to_context()

    net = next(i for i in context["headline"] if i["label"] == "Net credits")
    assert net["delta_class"] == "neutral"


def test_headline_positive_class_when_net_is_positive() -> None:
    debrief = build.debrief(
        moments=(),
        activity=build.full_activity(),
        net_credits=750,
    )

    context = _presenter().present(debrief).to_context()

    net = next(i for i in context["headline"] if i["label"] == "Net credits")
    assert net["delta_class"] == "positive"
    assert net["delta_display"] == "+750 Cr"


def test_unknown_systems_use_default_when_absent() -> None:
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        start_system=None,
        end_system=None,
    )

    context = _presenter().present(debrief).to_context()

    assert context["header"]["start_system"] == "Unknown"
    assert context["header"]["end_system"] == "Unknown"
    assert context["header"]["systems_visited"] == "0"


def test_timeline_entry_without_system_is_none() -> None:
    debrief = build.debrief(
        moments=(build.moment(MomentKind.HONK, ActivityDomain.EXPLORATION, 1),),
        activity=ActivityRollup(modes_used=()),
    )

    context = _presenter().present(debrief).to_context()

    assert context["timeline"][0]["system"] is None


def test_timeline_skips_non_system_detail_pairs() -> None:
    # A moment whose detail holds only a non-system field makes _moment_system
    # iterate past a non-matching pair and fall through to None.
    from o7debrief.domain.model.conceptual_moment import ConceptualMoment
    from o7debrief.domain.value_objects.credits import Credits
    from tests.application.fakes import at

    moment = ConceptualMoment(
        kind=MomentKind.SCAN_BODY,
        domain=ActivityDomain.EXPLORATION,
        mode=ActivityMode.SHIP,
        occurred_at=at(1),
        label="SCAN_BODY",
        magnitude=0,
        credits_delta=Credits(0),
        detail=(("BodyName", "Earth"),),
    )
    debrief = build.debrief(
        moments=(moment,),
        activity=ActivityRollup(modes_used=()),
    )

    context = _presenter().present(debrief).to_context()

    assert context["timeline"][0]["system"] is None


def test_no_milestones_when_nothing_notable() -> None:
    # A short jump, a small payout and no promotion produce no milestones.
    moments = (
        build.moment(MomentKind.JUMP, ActivityDomain.TRAVEL, 1, magnitude=5),
        build.moment(MomentKind.BOUNTY, ActivityDomain.COMBAT, 2, credits=10),
    )
    debrief = build.debrief(moments=moments, activity=build.full_activity())

    context = _presenter().present(debrief).to_context()

    assert context["milestones"] == []


def test_rank_change_renders_tier_names_and_steady_note() -> None:
    labels = (
        ("rank.combat.title", "Combat"),
        ("rank.combat.tier.3", "Competent"),
        ("rank.combat.tier.4", "Expert"),
        ("rank.trade.title", "Trade"),
        ("rank.trade.tier.2", "Peddler"),
    )
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        ranks=_full_ranks(),
    )

    context = _presenter(labels).present(debrief).to_context()

    # The promoted ladder shows its from/to tier names and no note.
    combat = context["ranks"][0]
    assert combat["promoted"] is True
    assert combat["from_tier_name"] == "Competent"
    assert combat["to_tier_name"] == "Expert"
    assert combat["note"] == ""
    # The steady ladder shows its current tier name and the no-change note.
    trade = context["ranks"][1]
    assert trade["promoted"] is False
    assert trade["to_tier_name"] == "Peddler"
    assert trade["note"] == "(no change)"
    # The closing percentage drives the progress bar.
    assert combat["progress_pct"] == 10
    assert trade["progress_pct"] == 55


def test_rank_progress_pct_defaults_to_zero_without_closing_pct() -> None:
    delta = build.rank_delta(
        RankLadder.EMPIRE,
        from_tier=14,
        to_tier=14,
        promoted=False,
        start_pct=0,
        end_pct=None,
        growth_pct=None,
        tier_ups=0,
    )
    debrief = build.debrief(
        moments=(), activity=ActivityRollup(modes_used=()), ranks=(delta,)
    )

    context = _presenter().present(debrief).to_context()

    assert context["ranks"][0]["progress_pct"] == 0


def test_header_shows_the_ship_when_known() -> None:
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        ship="Panther Clipper Mk II",
    )

    context = _presenter().present(debrief).to_context()

    assert context["header"]["ship"] == "Panther Clipper Mk II"


def test_header_shows_the_ship_name_when_present() -> None:
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(modes_used=()),
        ship="Panther Clipper Mk II",
        ship_name="STARDUST",
    )

    context = _presenter().present(debrief).to_context()

    assert context["header"]["ship_name"] == "STARDUST"


def test_header_falls_back_to_unknown_ship_when_absent() -> None:
    debrief = build.debrief(moments=(), activity=ActivityRollup(modes_used=()))

    context = _presenter().present(debrief).to_context()

    assert context["header"]["ship"] == "Unknown ship"


def test_domain_sections_omit_absent_domains() -> None:
    # Only flight present means exactly one section is rendered.
    activity = ActivityRollup(
        flight=build.full_activity().flight,
        modes_used=(),
    )
    debrief = build.debrief(moments=(), activity=activity)

    context = _presenter().present(debrief).to_context()

    assert len(context["domains"]) == 1
    assert context["domains"][0]["key"] == "travel"
    labels = [stat["label"] for stat in context["domains"][0]["stats"]]
    assert labels == ["Jumps", "Distance"]


def test_timeline_categories_group_by_domain_in_canonical_order() -> None:
    debrief = build.debrief(moments=_full_moments(), activity=build.full_activity())

    context = _presenter().present(debrief).to_context()
    categories = context["timeline_categories"]

    # Only domains with moments appear, in the canonical domain order.
    assert [category["key"] for category in categories] == [
        "travel",
        "combat",
        "missions",
        "srv",
        "on_foot",
    ]
    # Every moment lands in exactly one category, so counts sum to the flat log.
    assert sum(category["count"] for category in categories) == len(context["timeline"])
    by_key = {category["key"]: category for category in categories}
    assert by_key["combat"]["count"] == 1
    assert by_key["combat"]["entries"][0]["text"] == "BOUNTY"
    assert by_key["combat"]["entries"][0]["mode"] == "ship"


def test_timeline_categories_empty_when_no_moments() -> None:
    debrief = build.debrief(moments=(), activity=ActivityRollup(modes_used=()))

    context = _presenter().present(debrief).to_context()

    assert context["timeline_categories"] == []
