"""Tests for the fleet carrier section: jumps made and the distance they covered.

A carrier jump is unlike a ship jump: the journal states where the carrier
arrived but never how far it came, so the distance is derived from the gaps
between consecutive stated positions rather than read outright. That leaves the
first jump of a session unmeasurable, and these tests hold the report to saying
so instead of passing a short total off as the whole distance.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup, CarrierRollup
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec


def _carrier_stats(rollup: CarrierRollup, labels=()) -> dict[str, str]:
    """Return the carrier section's stats as a label-to-value mapping."""
    debrief = build.debrief(
        moments=(),
        activity=ActivityRollup(carrier=rollup, modes_used=()),
    )
    presenter = DebriefPresenter(spec(labels), number_format())
    context = presenter.present(debrief).to_context()
    section = next(s for s in context["domains"] if s["key"] == "carrier")
    return {stat["label"]: stat["value_display"] for stat in section["stats"]}


def test_a_fully_measured_run_states_the_distance_plainly() -> None:
    stats = _carrier_stats(
        CarrierRollup(jumps=8, distance_ly=3296.15, legs_measured=8, legs_total=8)
    )

    assert stats["Carrier jumps"] == "8"
    assert stats["Distance"] == "3,296.2 ly"


def test_an_unmeasurable_first_leg_is_declared_rather_than_hidden() -> None:
    """Nine jumps, eight measurable: the report says which legs it covers."""
    stats = _carrier_stats(
        CarrierRollup(jumps=9, distance_ly=3296.15, legs_measured=8, legs_total=9)
    )

    assert stats["Distance"] == "3,296.2 ly (over 8 of 9 jumps)"


def test_a_run_with_no_stated_positions_reports_no_distance() -> None:
    stats = _carrier_stats(
        CarrierRollup(jumps=3, distance_ly=0.0, legs_measured=0, legs_total=3)
    )

    assert stats["Distance"] == "0.0 ly (over 0 of 3 jumps)"


def test_the_partial_wording_is_configurable() -> None:
    """Nothing in the report hardcodes a display string."""
    stats = _carrier_stats(
        CarrierRollup(jumps=9, distance_ly=3296.15, legs_measured=8, legs_total=9),
        labels=(
            (
                "label.carrier.distance_partial",
                "{distance} across {measured}/{total} legs",
            ),
        ),
    )

    assert stats["Distance"] == "3,296.2 ly across 8/9 legs"
