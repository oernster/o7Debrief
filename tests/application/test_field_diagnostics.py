"""Tests for noticing a currency field a matching rule never found.

A rule that names a field the event does not carry yields zero, which reads
as "earned nothing" when the truth is "never read". These cover that the
mismatch is reported once per event type and field, that a rule which does not
apply is not reported and that the notice reaches the rendered report.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.application.services.field_diagnostics import missing_currency_fields
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.rules.rollup_spec import MomentRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from tests.application import domain_builders as build
from tests.application.fakes import (
    BIG_PAYOUT,
    HIGH_VALUE_EXOBIO,
    LONG_JUMP_LY,
    SCHEMA_VERSION,
    event,
    number_format,
)

_MISSION = "MissionCompleted"
_COINS_FIELD = "MercCoins"
_PAID = 500
_FIRST = 0
_SECOND = 10


def _rule(**overrides) -> MomentRule:
    fields = {
        "event_type": _MISSION,
        "kind": MomentKind.MISSION_COMPLETE,
        "domain": ActivityDomain.MISSIONS,
        "mode": ActivityMode.SHIP,
        "magnitude_field": None,
        "credits_field": None,
        "coins_field": _COINS_FIELD,
    }
    fields.update(overrides)
    return MomentRule(**fields)


def _spec(*rules: MomentRule, labels: tuple[tuple[str, str], ...] = ()) -> RollupSpec:
    return RollupSpec(
        schema_version=SCHEMA_VERSION,
        rules=rules,
        thresholds=ThresholdSet(
            long_jump_ly=LONG_JUMP_LY,
            big_payout_credits=BIG_PAYOUT,
            high_value_exobio_credits=HIGH_VALUE_EXOBIO,
        ),
        labels=labels,
    )


def test_a_named_field_the_event_lacks_is_reported() -> None:
    events = (event(_MISSION, _FIRST, Reward=1000),)
    assert missing_currency_fields(events, _spec(_rule())) == (
        (_MISSION, _COINS_FIELD),
    )


def test_a_field_the_event_carries_is_not_reported() -> None:
    events = (event(_MISSION, _FIRST, **{_COINS_FIELD: _PAID}),)
    assert missing_currency_fields(events, _spec(_rule())) == ()


def test_a_non_integer_value_counts_as_not_carried() -> None:
    events = (event(_MISSION, _FIRST, **{_COINS_FIELD: "lots"}),)
    assert missing_currency_fields(events, _spec(_rule())) == (
        (_MISSION, _COINS_FIELD),
    )


def test_a_boolean_is_not_mistaken_for_a_reward_of_one() -> None:
    events = (event(_MISSION, _FIRST, **{_COINS_FIELD: True}),)
    assert missing_currency_fields(events, _spec(_rule())) == (
        (_MISSION, _COINS_FIELD),
    )


def test_the_same_mismatch_is_reported_once_however_often_it_happens() -> None:
    events = (event(_MISSION, _FIRST), event(_MISSION, _SECOND))
    assert missing_currency_fields(events, _spec(_rule())) == (
        (_MISSION, _COINS_FIELD),
    )


def test_a_rule_naming_no_currency_field_is_not_reported() -> None:
    events = (event(_MISSION, _FIRST),)
    assert missing_currency_fields(events, _spec(_rule(coins_field=None))) == ()


def test_a_rule_whose_filter_the_event_fails_is_not_reported() -> None:
    # That rule was never going to read the field, so saying so would be noise.
    rule = _rule(where_field="Name", where_contains=("operation",))
    events = (event(_MISSION, _FIRST, Name="courier_delivery"),)
    assert missing_currency_fields(events, _spec(rule)) == ()


def test_an_event_no_rule_matches_is_not_reported() -> None:
    events = (event("FSDJump", _FIRST),)
    assert missing_currency_fields(events, _spec(_rule())) == ()


def test_the_notice_reaches_the_report_naming_the_event_and_the_field() -> None:
    debrief = build.debrief(moments=(), activity=ActivityRollup(modes_used=()))
    view = DebriefPresenter(_spec(_rule()), number_format()).present(
        debrief, ((_MISSION, _COINS_FIELD),)
    )
    expected = (
        "MissionCompleted carried no MercCoins, "
        "so any amount it should hold reads as zero."
    )
    assert view.to_context()["notices"] == [expected]


def test_the_notice_wording_is_configurable_through_the_spec() -> None:
    labels = (("label.diagnostic.missing_field", "{field} absent from {event}"),)
    debrief = build.debrief(moments=(), activity=ActivityRollup(modes_used=()))
    view = DebriefPresenter(_spec(_rule(), labels=labels), number_format()).present(
        debrief, ((_MISSION, _COINS_FIELD),)
    )
    assert view.to_context()["notices"] == ["MercCoins absent from MissionCompleted"]


def test_a_clean_reading_produces_no_notices() -> None:
    debrief = build.debrief(moments=(), activity=ActivityRollup(modes_used=()))
    view = DebriefPresenter(_spec(_rule()), number_format()).present(debrief)
    assert view.to_context()["notices"] == []


_JUMP = "FSDJump"
_DISTANCE_FIELD = "JumpDist"


def _jump_rule(**overrides) -> MomentRule:
    fields = {
        "event_type": _JUMP,
        "kind": MomentKind.JUMP,
        "domain": ActivityDomain.TRAVEL,
        "mode": ActivityMode.SHIP,
        "magnitude_field": _DISTANCE_FIELD,
        "credits_field": None,
        "coins_field": None,
    }
    fields.update(overrides)
    return MomentRule(**fields)


def test_a_magnitude_field_the_event_omits_is_noticed() -> None:
    """The guard the jump-distance defect went undetected for years without."""
    events = (event(_JUMP, _FIRST, StarSystem="Sol"),)

    assert missing_currency_fields(events, _spec(_jump_rule())) == (
        (_JUMP, _DISTANCE_FIELD),
    )


def test_a_fractional_magnitude_is_read_and_never_noticed() -> None:
    """A jump distance is stated as a real quantity, which is perfectly usable."""
    events = (event(_JUMP, _FIRST, JumpDist=12.129),)

    assert missing_currency_fields(events, _spec(_jump_rule())) == ()


def test_a_whole_magnitude_is_read_and_never_noticed() -> None:
    events = (event(_JUMP, _FIRST, JumpDist=12),)

    assert missing_currency_fields(events, _spec(_jump_rule())) == ()


def test_a_boolean_never_passes_for_a_magnitude() -> None:
    events = (event(_JUMP, _FIRST, JumpDist=True),)

    assert missing_currency_fields(events, _spec(_jump_rule())) == (
        (_JUMP, _DISTANCE_FIELD),
    )


def test_a_rule_naming_no_magnitude_field_is_never_noticed() -> None:
    events = (event(_JUMP, _FIRST),)

    assert (
        missing_currency_fields(events, _spec(_jump_rule(magnitude_field=None))) == ()
    )
