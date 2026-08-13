"""Notice when a rule names a payload field the matching event never carried.

A rule that names a numeric field the event does not usably hold yields zero.
As a domain rule that is exactly right: a missing field must not fabricate a
number. As reporting it is dangerous, because the report then states that a
session earned nothing or travelled nowhere where the truth is that nothing was
ever read. The two are indistinguishable to a reader; the failure is silent by
construction.

This is not a hypothetical and it has bitten twice. The taxonomy's
``coins_field`` names the key an Operation's Merc Coins reward is read from.
That name is an assumption: no published schema documents it, Frontier's
journal manual has not been revised since 2021 and the reward may not even ride
the event the rule matches. If the guess is wrong, every Operation reports zero
coins forever and nothing says so.

The second case is why ``magnitude_field`` is watched here too. The jump rule
named ``JumpDist``, the event carried it and the reader that fetched it took
integers only, so every jump distance in the game's history was discarded and
five jumps reported nought light years travelled. Nothing said so, because the
field was present: what failed was reading it. Watching magnitude the same way
turns any repeat of that into a notice on the very first session it affects.

So the mismatch is gathered here and reported in the debrief itself. It fires
once per event type and field rather than once per event, because the reader
needs to know that a field is unread, not how many times.
"""

from __future__ import annotations

from o7debrief.domain.aggregation.moment_factory import matches_filter
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["missing_currency_fields"]


def _carries_number(event: RawEvent, field: str, allow_fractional: bool) -> bool:
    """Return whether the event holds a usable number at ``field``.

    A currency is whole by nature, so only an integer will do. A magnitude is a
    real quantity (a jump distance is stated as 12.129) and accepts either. A
    boolean is rejected in both cases, because bool is a subclass of int and a
    stray True would otherwise pass for a reward of one credit.
    """
    value = event.get(field)
    if isinstance(value, bool):
        return False
    usable = (int, float) if allow_fractional else (int,)
    return isinstance(value, usable)


def missing_currency_fields(
    events: tuple[RawEvent, ...], spec: RollupSpec
) -> tuple[tuple[str, str], ...]:
    """Return the (event type, field) pairs a matching rule named in vain.

    Both the coins field and the magnitude field are checked, since either
    reading as nothing produces a figure the reader cannot tell from a real
    zero. Only rules that genuinely apply are considered: a rule with a
    where-filter the event fails was never going to read the field, so
    reporting it would be noise. Pairs come back in the order first seen,
    without repeats.
    """
    found: list[tuple[str, str]] = []
    for event in events:
        for rule in spec.rules_for(event.event_type):
            if not matches_filter(event, rule):
                continue
            for field, fractional in (
                (rule.coins_field, False),
                (rule.magnitude_field, True),
            ):
                if field is None or _carries_number(event, field, fractional):
                    continue
                pair = (event.event_type, field)
                if pair not in found:
                    found.append(pair)
    return tuple(found)
