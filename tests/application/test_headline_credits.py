"""Tests for the credits headline: a balance, with the session change beside it.

Split out of the presenter tests as its own subject. The headline used to put
the same net delta in both the value slot and the delta slot, so a session with
no credit events rendered "0 Cr" in the slot a reader takes for their balance.
These tests hold the two slots apart; they also hold an absent reading apart from a
balance of nothing.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

# A balance large enough that nobody would mistake it for a session's takings,
# taken from a real journal reading rather than invented.
REAL_BALANCE = 33_455_794_489
SESSION_PAYOUT = 750
# The login that stated the balance, taken from the same real journal.
READING_TIME = "2026-08-15T18:49:38Z"


def _credits_headline(debrief, labels: tuple[tuple[str, str], ...] = ()) -> dict:
    """Return the credits item from a presented debrief's headline row."""
    presenter = DebriefPresenter(spec(labels), number_format(), app_version="1.2.3")
    context = presenter.present(debrief).to_context()
    return next(i for i in context["headline"] if i["label"] == "Credits")


def _quiet_debrief(**kwargs):
    """A debrief with no moments, so only the credit figures vary."""
    return build.debrief(moments=(), activity=ActivityRollup(modes_used=()), **kwargs)


def test_neutral_class_when_the_session_changed_nothing() -> None:
    assert _credits_headline(_quiet_debrief(net_credits=0))["delta_class"] == "neutral"


def test_positive_class_and_signed_delta_when_the_session_earned() -> None:
    debrief = build.debrief(
        moments=(),
        activity=build.full_activity(),
        net_credits=SESSION_PAYOUT,
    )

    net = _credits_headline(debrief)
    assert net["delta_class"] == "positive"
    assert net["delta_display"] == "+750 Cr"


def test_the_balance_and_the_change_occupy_different_slots() -> None:
    """The defect that prompted this: both slots carried the same delta."""
    debrief = _quiet_debrief(net_credits=0, credits_balance=REAL_BALANCE)

    net = _credits_headline(debrief)
    assert net["value_display"] == "33,455,794,489 Cr"
    assert net["delta_display"] == "+0 Cr"


def test_an_absent_reading_is_never_rendered_as_an_amount() -> None:
    net = _credits_headline(_quiet_debrief(net_credits=0, credits_balance=None))

    assert net["value_display"] == "No reading"


def test_a_real_zero_balance_reads_differently_from_no_reading() -> None:
    """A commander who genuinely has nothing is not the same as no reading."""
    net = _credits_headline(_quiet_debrief(net_credits=0, credits_balance=0))

    assert net["value_display"] == "0 Cr"


def test_the_absent_reading_wording_is_configurable() -> None:
    """Nothing in the report hardcodes a display string."""
    net = _credits_headline(
        _quiet_debrief(net_credits=0, credits_balance=None),
        labels=(("label.credits.balance_unknown", "Balance unknown"),),
    )

    assert net["value_display"] == "Balance unknown"


def test_a_loss_reads_as_a_loss() -> None:
    """The defect this closes: a session that lost twenty million read as a gain.

    The change used to be summed from the moments, which priced income and
    nothing else, so an eleven million credit rebuy left no mark on it. It is
    now the difference between the balances the journal states at each end,
    which is negative when the commander ended the session poorer.
    """
    net = _credits_headline(_quiet_debrief(net_credits=-20_110_001))

    assert net["delta_class"] == "negative"
    assert net["delta_display"] == "-20,110,001 Cr"


def test_an_unmeasurable_change_is_omitted_rather_than_announced() -> None:
    """A change that could not be measured is left out, never worded.

    It once read "Change unread", which is true and useless: it reports the
    absence of one quantity out of the unbounded set the report did not
    measure. What the session's events did come to is a real figure and has a
    headline card of its own. Rendering a zero here would be worse still, since
    a reader takes it for a session that broke even.
    """
    net = _credits_headline(_quiet_debrief(net_credits=None))

    assert net["delta_display"] is None


def test_an_absent_balance_still_fills_the_value_slot() -> None:
    """The value slot is not optional, which is why it words its absence.

    Something must occupy it or a blank card reads as a balance of nothing.
    The delta slot has no such obligation, so it is simply omitted.
    """
    net = _credits_headline(_quiet_debrief(net_credits=None, credits_balance=None))

    assert net["value_display"] == "No reading"
    assert net["delta_display"] is None


def test_the_balance_says_when_it_was_read() -> None:
    """The defect this closes: a login reading passing for the balance now.

    The journal states a balance at a login and never again, so on a session
    spanning nineteen hours of selling and outfitting the headline was the
    figure the commander had before any of it. The reading stands, because it
    is what the journal said; what it lacked was the moment it was taken.
    """
    net = _credits_headline(
        _quiet_debrief(
            net_credits=None,
            credits_balance=REAL_BALANCE,
            credits_balance_at=READING_TIME,
        )
    )

    assert net["value_display"] == "33,455,794,489 Cr"
    assert net["note_display"] == "Read at login, 2026-08-15 18:49:38"


def test_no_reading_carries_no_reading_time() -> None:
    """A time for a reading that never happened would contradict the slot above."""
    net = _credits_headline(_quiet_debrief(net_credits=None, credits_balance=None))

    assert net["note_display"] is None


def test_the_reading_time_wording_is_configurable() -> None:
    net = _credits_headline(
        _quiet_debrief(credits_balance=REAL_BALANCE, credits_balance_at=READING_TIME),
        labels=(("label.credits.balance_read_at", "as of {time}"),),
    )

    assert net["note_display"] == "as of 2026-08-15 18:49:38"
