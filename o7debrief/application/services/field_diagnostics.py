"""Notice when a rule names a payload field the matching event never carried.

A rule that names a currency field the event does not hold yields zero. As a
domain rule that is exactly right: a missing field must not fabricate a number.
As reporting it is dangerous, because the report then states that a session
earned nothing where the truth is that nothing was ever read. The two are
indistinguishable to a reader; the failure is silent by construction.

This is not a hypothetical. The taxonomy's ``coins_field`` names the key an
Operation's Merc Coins reward is read from. That name is an assumption:
no published schema documents it, Frontier's journal manual has not been
revised since 2021 and the reward may not even ride the event the rule
matches. If the guess is wrong, every Operation reports zero coins forever
and nothing says so.

So the mismatch is gathered here and reported in the debrief itself. It fires
once per event type and field rather than once per event, because the reader
needs to know that a field is missing, not how many times.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.moment_factory import matches_filter
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["missing_currency_fields"]


def _carries_currency(event: RawEvent, field: str) -> bool:
    """Return whether the event holds a usable integer at ``field``.

    A boolean is rejected explicitly, because bool is a subclass of int and a
    stray True would otherwise pass for a reward of one.
    """
    value = event.get(field)
    return isinstance(value, int) and not isinstance(value, bool)


def missing_currency_fields(
    events: tuple[RawEvent, ...], spec: RollupSpec
) -> tuple[tuple[str, str], ...]:
    """Return the (event type, field) pairs a matching rule named in vain.

    Only rules that genuinely apply are considered: a rule with a where-filter
    the event fails was never going to read the field, so reporting it would
    be noise. Pairs come back in the order first seen, without repeats.
    """
    found: list[tuple[str, str]] = []
    for event in events:
        for rule in spec.rules_for(event.event_type):
            field = rule.coins_field
            if field is None or not matches_filter(event, rule):
                continue
            if _carries_currency(event, field):
                continue
            pair = (event.event_type, field)
            if pair not in found:
                found.append(pair)
    return tuple(found)
