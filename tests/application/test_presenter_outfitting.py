"""Tests for the outfitting and shipyard section plus the engineering split.

Two defects sit behind these. A session could sell eighty stored modules for
nearly two billion credits and the report recorded none of it, so the balance
moved with nothing on the page to account for it. And an experimental effect is
reported by the journal as an ``EngineerCraft`` exactly like a grade roll, so a
session spent choosing effects read as a session of heavy modification.
"""

from __future__ import annotations

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import (
    ActivityRollup,
    EngineeringRollup,
    ShipyardRollup,
)
from o7debrief.domain.value_objects.credits import Credits
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

# Figures taken from a real journal session: eighty stored modules sold, five
# bought and four ships sold, with nothing bought.
_MODULES_SOLD = 80
_MODULES_BOUGHT = 5
_MODULE_EARNED = 1_966_278_800
_MODULE_SPEND = 6_172_743
_SHIPS_SOLD = 4
_SHIP_EARNED = 58_688_282
_TRANSFERS = 2
_TRANSFER_FEES = 1_636_815


def _section(activity: ActivityRollup, key: str, labels=()) -> dict:
    """Return one domain section from a presented debrief, as a plain dict."""
    debrief = build.debrief(moments=(), activity=activity)
    presenter = DebriefPresenter(spec(labels), number_format(), app_version="1.2.3")
    context = presenter.present(debrief).to_context()
    return next(s for s in context["domains"] if s["key"] == key)


def _stats(activity: ActivityRollup, key: str, labels=()) -> dict[str, str]:
    section = _section(activity, key, labels)
    return {stat["label"]: stat["value_display"] for stat in section["stats"]}


def _outfitting(rollup: ShipyardRollup, labels=()) -> dict[str, str]:
    return _stats(ActivityRollup(shipyard=rollup, modes_used=()), "shipyard", labels)


def test_each_side_of_the_trade_is_counted_and_priced_apart() -> None:
    """A net figure would report a full refit as though nothing happened."""
    stats = _outfitting(
        ShipyardRollup(
            modules_bought=_MODULES_BOUGHT,
            modules_sold=_MODULES_SOLD,
            module_spend=Credits(_MODULE_SPEND),
            module_earned=Credits(_MODULE_EARNED),
            ships_sold=_SHIPS_SOLD,
            ship_earned=Credits(_SHIP_EARNED),
            transfers=_TRANSFERS,
            transfer_fees=Credits(_TRANSFER_FEES),
        )
    )

    assert stats["Modules bought"] == "5"
    assert stats["Spent on modules"] == "6,172,743 Cr"
    assert stats["Modules sold"] == "80"
    assert stats["Earned from modules"] == "1,966,278,800 Cr"
    assert stats["Ships bought"] == "0"
    assert stats["Spent on ships"] == "0 Cr"
    assert stats["Ships sold"] == "4"
    assert stats["Earned from ships"] == "58,688,282 Cr"


def test_a_transfer_fee_is_neither_a_purchase_nor_a_sale() -> None:
    """Moving a stored ship costs real money and buys nothing.

    Folded into either side it would distort it, so it gets its own pair of
    lines. One transfer in a live journal cost 1,626,451 Cr.
    """
    stats = _outfitting(
        ShipyardRollup(transfers=_TRANSFERS, transfer_fees=Credits(_TRANSFER_FEES))
    )

    assert stats["Ship transfers"] == "2"
    assert stats["Transfer fees"] == "1,636,815 Cr"


def test_a_section_shows_the_note_its_taxonomy_declares() -> None:
    """A section can state what its figures leave out.

    The outfitting section needs it: a Vessel Hangar and a part-exchange are
    both absent from its totals. The note was declared in the taxonomy and
    never read back, so no section could say anything of the sort.
    """
    section = _section(
        ActivityRollup(shipyard=ShipyardRollup(), modes_used=()),
        "shipyard",
        labels=(("domain.shipyard.note", "Hangar bays are counted elsewhere."),),
    )

    assert section["note"] == "Hangar bays are counted elsewhere."


def test_the_outfitting_wording_is_configurable() -> None:
    """Nothing in the report hardcodes a display string."""
    stats = _outfitting(
        ShipyardRollup(modules_sold=_MODULES_SOLD),
        labels=(("label.shipyard.modules_sold", "Kit sold"),),
    )

    assert stats["Kit sold"] == "80"


def test_a_grade_roll_and_an_experimental_are_counted_apart() -> None:
    """The journal reports both as an EngineerCraft; they are different work.

    A grade is rolled over and over for one module; an effect is chosen once
    and applied once. Counted together, four effects and thirty rolls read as
    thirty-four modifications.
    """
    stats = _stats(
        ActivityRollup(
            engineering=EngineeringRollup(crafted=30, experimentals=4),
            modes_used=(),
        ),
        "engineering",
    )

    assert stats["Modification rolls"] == "30"
    assert stats["Experimental effects"] == "4"
