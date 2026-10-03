"""What the report says about the parts of the journal it could not read.

A figure the journal never stated is never reported as zero (I10); the same
honesty applies to the reading itself. A line that could not be read and
a balance that is not a usable amount both leave a gap in the report; a reader
told nothing takes the gap for a fact. Each is therefore named in the notices.
"""

from __future__ import annotations

from tests.application.fakes import FakeExporter, FakeRankStore, event
from tests.application.service_builders import build_one_shot_service

# A balance below zero, which no Credits amount can hold.
_NEGATIVE_BALANCE = -5
_UNREADABLE_LINES = 3


def _session(*middle):
    return (
        event("Commander", 0, Name="Jameson", FID="F1234"),
        *middle,
        event("Shutdown", 9),
    )


def _notices_of(exporter: FakeExporter) -> tuple[str, ...]:
    (view,) = exporter.rendered
    return view.notices


def test_a_balance_that_is_not_an_amount_is_left_out_and_said_so() -> None:
    """The defect: one odd balance aborted the debrief and lost every figure."""
    html = FakeExporter("html", b"")
    service = build_one_shot_service(
        latest=_session(event("LoadGame", 1, Credits=_NEGATIVE_BALANCE)),
        store=FakeRankStore(),
        exporters=(html,),
    )

    service.debrief_last_session()

    (notice,) = _notices_of(html)
    assert "LoadGame" in notice and "Credits" in notice


def test_lines_that_could_not_be_read_are_counted_in_the_report() -> None:
    html = FakeExporter("html", b"")
    service = build_one_shot_service(
        latest=_session(event("LoadGame", 1)),
        store=FakeRankStore(),
        exporters=(html,),
        unreadable_lines=_UNREADABLE_LINES,
    )

    service.debrief_last_session()

    (notice,) = _notices_of(html)
    assert str(_UNREADABLE_LINES) in notice


def test_the_history_report_names_both_kinds_of_gap() -> None:
    html = FakeExporter("html", b"")
    history = _session(event("LoadGame", 1, Credits=_NEGATIVE_BALANCE))
    service = build_one_shot_service(
        all_events=history,
        store=FakeRankStore(),
        exporters=(html,),
        unreadable_lines=_UNREADABLE_LINES,
    )

    service.debrief_all_history()

    notices = _notices_of(html)
    assert len(notices) == 2
    assert any("Credits" in notice for notice in notices)
    assert any(str(_UNREADABLE_LINES) in notice for notice in notices)


def test_a_clean_reading_adds_no_notice() -> None:
    html = FakeExporter("html", b"")
    service = build_one_shot_service(
        latest=_session(event("LoadGame", 1, Credits=1)),
        store=FakeRankStore(),
        exporters=(html,),
    )

    service.debrief_last_session()

    assert _notices_of(html) == ()
