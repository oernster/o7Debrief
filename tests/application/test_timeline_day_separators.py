"""Tests for day separators in the session log.

A log that covers one day shows no separators at all, so a session report
renders exactly as it did before the feature existed. A log that covers
several shows one heading per day that has rows, newest first, computed per
panel rather than once for the whole report: a category panel holding one
afternoon's rows stays undated even when the full log spans months.

Every displayed time is UTC and the day is read from the same instant
untouched, so a clock change in any local zone cannot move a row into the
wrong day group. The two British transitions are asserted directly because
they are the cases a local-time implementation would get wrong: the hour that
repeats in autumn and the hour that is skipped in spring.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.conceptual_moment import ConceptualMoment
from o7debrief.domain.value_objects.credits import Credits
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    MomentKind,
)
from o7debrief.domain.value_objects.event_time import EventTime
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

# The formatted day headings the taxonomy date format produces for the
# instants used below. Spelled out so a change to the format is caught here
# rather than silently altering every report.
_DAY_13 = "Thu 13 Aug 2026"
_DAY_14 = "Fri 14 Aug 2026"
_DAY_15 = "Sat 15 Aug 2026"
# The last Sunday of March 2026, when the British clock jumps from 01:00 to
# 02:00, and the last Sunday of October, when 01:00 to 02:00 runs twice.
_SPRING_FORWARD_DAY = "Sun 29 Mar 2026"
_FALL_BACK_DAY = "Sun 25 Oct 2026"


def _presenter() -> DebriefPresenter:
    """Return a presenter wired to the taxonomy labels and number format."""
    return DebriefPresenter(spec(), number_format())


def _moment(
    iso: str,
    domain: ActivityDomain = ActivityDomain.TRAVEL,
    kind: MomentKind = MomentKind.JUMP,
) -> ConceptualMoment:
    """Build one moment at an explicit UTC instant."""
    return ConceptualMoment(
        kind=kind,
        domain=domain,
        mode=ActivityMode.SHIP,
        occurred_at=EventTime.parse(iso),
        label=kind.name,
        magnitude=0.0,
        credits_delta=Credits(0),
        coins_delta=Credits(0),
        detail=(),
        text_template="",
    )


def _view(*moments: ConceptualMoment):
    """Present a debrief holding exactly these moments, oldest first."""
    debrief = build.debrief(moments=moments, activity=build.full_activity())
    return _presenter().present(debrief)


def _separators(entries) -> list[str]:
    """Return the day headings a panel would draw, in render order."""
    return [entry.day_separator for entry in entries if entry.day_separator]


def _panel(view, key: str):
    """Return the entries of the named category panel."""
    for category in view.timeline_categories:
        if category.key == key:
            return category.entries
    raise AssertionError(f"no category panel named {key}")


def test_a_single_day_log_carries_no_separators_anywhere() -> None:
    """One day of rows renders as it always did: not a heading in sight."""
    view = _view(
        _moment("2026-08-13T09:00:00Z"),
        _moment("2026-08-13T15:15:30Z"),
    )

    assert _separators(view.timeline) == []
    assert all(entry.day_separator == "" for entry in view.timeline)
    for category in view.timeline_categories:
        assert _separators(category.entries) == []


def test_a_multi_day_log_heads_each_day_once_newest_first() -> None:
    """Each day with rows gets exactly one heading, in the descending order."""
    view = _view(
        _moment("2026-08-13T16:00:30Z"),
        _moment("2026-08-14T10:36:35Z"),
        _moment("2026-08-14T11:48:26Z"),
        _moment("2026-08-15T15:15:30Z"),
    )

    assert _separators(view.timeline) == [_DAY_15, _DAY_14, _DAY_13]
    # The heading sits on the first row of its day, not on a row of its own,
    # so no row is lost and none is duplicated.
    assert len(view.timeline) == 4
    assert view.timeline[0].day_separator == _DAY_15
    assert view.timeline[1].day_separator == _DAY_14
    assert view.timeline[2].day_separator == ""
    assert view.timeline[3].day_separator == _DAY_13


def test_an_empty_log_produces_no_entries_and_no_separators() -> None:
    """No moments means no rows and no empty day group to render."""
    view = _view()

    assert view.timeline == ()
    assert view.timeline_categories == ()


def test_a_session_crossing_midnight_shows_both_days() -> None:
    """The one case where a single play session needs separators."""
    view = _view(
        _moment("2026-08-13T23:40:00Z"),
        _moment("2026-08-14T00:20:00Z"),
    )

    assert _separators(view.timeline) == [_DAY_14, _DAY_13]


def test_a_panel_covering_fewer_days_than_the_log_stays_undated() -> None:
    """A category confined to one day shows no headings, whatever the log does.

    Separators are computed per panel precisely for this: the combat panel
    holds one day's rows, so dating it would be noise, while the full log
    spanning two days is dated as it should be.
    """
    view = _view(
        _moment("2026-08-13T09:00:00Z", ActivityDomain.TRAVEL),
        _moment("2026-08-14T09:00:00Z", ActivityDomain.TRAVEL),
        _moment("2026-08-14T10:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
        _moment("2026-08-14T11:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
    )

    assert _separators(view.timeline) == [_DAY_14, _DAY_13]
    assert _separators(_panel(view, "combat")) == []
    assert _separators(_panel(view, "travel")) == [_DAY_14, _DAY_13]


def test_the_repeated_autumn_hour_makes_one_day_group_not_two() -> None:
    """Fall-back replays 01:00 to 02:00 locally; in UTC it is one plain day.

    Both instants read as 01:30 on a British clock, an hour apart. Grouping on
    the displayed instant keeps them a single day with both rows intact, where
    grouping on a converted local time risks a duplicate heading.
    """
    view = _view(
        _moment("2026-10-25T00:30:00Z"),
        _moment("2026-10-25T01:30:00Z"),
    )

    assert _separators(view.timeline) == []
    assert len(view.timeline) == 2


def test_the_skipped_spring_hour_loses_no_row_and_no_day() -> None:
    """Spring-forward removes a local hour; the UTC day either side is one day."""
    view = _view(
        _moment("2026-03-29T00:30:00Z"),
        _moment("2026-03-29T01:30:00Z"),
        _moment("2026-03-30T00:30:00Z"),
    )

    assert _separators(view.timeline) == ["Mon 30 Mar 2026", _SPRING_FORWARD_DAY]
    assert len(view.timeline) == 3


def test_the_day_before_a_transition_is_its_own_group() -> None:
    """A transition day and the day before it stay two distinct headings."""
    view = _view(
        _moment("2026-10-24T23:30:00Z"),
        _moment("2026-10-25T00:30:00Z"),
    )

    assert _separators(view.timeline) == [_FALL_BACK_DAY, "Sat 24 Oct 2026"]


def test_the_footer_names_the_zone_every_time_is_shown_in() -> None:
    """The report says which clock it is quoting rather than leaving it open."""
    view = _view(_moment("2026-08-13T09:00:00Z"))

    assert view.footer.timezone == number_format().timezone_label
