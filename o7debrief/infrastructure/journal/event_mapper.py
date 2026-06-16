"""Map parsed journal dicts into domain ``RawEvent`` objects.

A journal record is a JSON object with an ``event`` type, a ``timestamp`` and an
arbitrary payload. This module turns such a dict into the domain's ``RawEvent``:
the timestamp is parsed via ``EventTime.parse`` (the domain's only timestamp
entry point), and the remaining payload keys become a stable, sorted tuple of
``(key, value)`` pairs so two events with the same payload compare equal.

Records missing an event type or a parseable timestamp are mapped to None, so a
single malformed record is skipped rather than aborting the whole read.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import Any

from o7debrief.domain.errors import O7DebriefError
from o7debrief.domain.model.raw_event import RawEvent
from o7debrief.domain.value_objects.event_time import EventTime

__all__ = ["map_record", "map_records", "EVENT_KEY", "TIMESTAMP_KEY"]

# The two reserved journal keys. ``event`` names the type; ``timestamp`` is the
# event-time. Both are consumed structurally and excluded from the field tuple.
EVENT_KEY = "event"
TIMESTAMP_KEY = "timestamp"


def _fields_from(record: dict[str, Any]) -> tuple[tuple[str, object], ...]:
    """Return the payload as a tuple of (key, value) pairs sorted by key.

    The reserved ``event`` and ``timestamp`` keys are excluded; everything else
    is kept verbatim. Sorting by key gives a deterministic, comparable order.
    """
    pairs = [
        (key, value)
        for key, value in record.items()
        if key not in (EVENT_KEY, TIMESTAMP_KEY)
    ]
    pairs.sort(key=lambda item: item[0])
    return tuple(pairs)


def map_record(record: dict[str, Any]) -> RawEvent | None:
    """Map one parsed journal dict to a ``RawEvent``, or None if unmappable.

    Returns None when the record lacks a non-empty ``event`` type, lacks a
    string ``timestamp``, or carries a timestamp the domain cannot parse.
    """
    event_type = record.get(EVENT_KEY)
    if not isinstance(event_type, str) or not event_type:
        return None

    timestamp = record.get(TIMESTAMP_KEY)
    if not isinstance(timestamp, str) or not timestamp:
        return None

    try:
        event_time = EventTime.parse(timestamp)
    except O7DebriefError:
        return None

    return RawEvent(
        event_type=event_type,
        event_time=event_time,
        fields=_fields_from(record),
    )


def map_records(records: tuple[dict[str, Any], ...]) -> tuple[RawEvent, ...]:
    """Map many parsed dicts to RawEvents, dropping any that are unmappable."""
    events: list[RawEvent] = []
    for record in records:
        event = map_record(record)
        if event is not None:
            events.append(event)
    return tuple(events)
