"""Header, headline, timeline, rank and footer builders for the presenter.

These turn the domain ``SessionDebrief`` into the formatted sub-views the
``DebriefView`` carries. All wording comes through the label resolver and all
numbers and times through the value formatter, so nothing here hardcodes a
display literal or reads a clock.

This module is application-layer and imports only application symbols. It
reads the domain debrief, moment and rank objects by attribute (duck typing)
and names their types as forward references, so it never imports the domain.
The star-system field name is the journal's own vocabulary, declared locally
as a named constant rather than imported from the domain.
"""

from __future__ import annotations

from o7debrief.application.dto.debrief_view import (
    FooterView,
    HeaderView,
    HeadlineItem,
    RankChange,
    TimelineCategory,
    TimelineEntry,
)
from o7debrief.application.services.label_resolver import mode_string_from_name
from o7debrief.application.services.presenter_domains import DOMAIN_ORDER
from o7debrief.application.services.timeline_text import row_text

__all__ = [
    "build_footer",
    "build_header",
    "build_headline",
    "build_ranks",
    "build_timeline",
    "build_timeline_categories",
]

# Journal field naming the star system an event occurred in. This is the
# journal's vocabulary (mirrored by the domain), declared here so this module
# stays free of a domain import.
_STAR_SYSTEM_FIELD = "StarSystem"

# Default display strings, resolved through the spec so they stay configurable.
_UNKNOWN_SYSTEM = ("system.unknown", "Unknown")
_UNKNOWN_SHIP = ("header.ship", "Unknown ship")
# The credits headline now names a balance rather than a change, because the
# change moved to the delta slot beside it. The old "net_credits" key is kept as
# the lookup so an existing taxonomy override is not silently dropped.
_CREDITS_HEADLINE = ("net_credits", "Credits")
# Shown in the value slot when the journal stated no balance at all. Distinct
# wording is the whole point: it must not be mistakable for an amount.
_BALANCE_UNKNOWN = ("credits.balance_unknown", "No reading")
# Shown in the delta slot when the journal stated too few balances for the
# session change to be measured. Never a zero, which would read as break-even.
_CHANGE_UNKNOWN = ("credits.change_unknown", "Change unread")
_JUMPS_HEADLINE = ("jumps", "Jumps")
_BODIES_HEADLINE = ("bodies_scanned", "Bodies scanned")
_KILLS_HEADLINE = ("kills", "Kills")
_APP_NAME = ("footer.app_name", "o7 Debrief")
_APP_VERSION = ("footer.app_version", "0")
_LICENSE = ("footer.license", "")
_GENERATED = ("footer.generated", "")
# Label shown beside a ladder whose tier did not change this period.
_RANK_NO_CHANGE = ("rank.no_change", "(no change)")
# Shown in place of a percentage when no reading is known at all. Distinct
# wording is the point: it must not be mistakable for a standing of zero.
_RANK_NO_READING = ("rank.no_reading", "No reading")

# Delta CSS classes for a headline value's direction.
_POSITIVE_CLASS = "positive"
_NEGATIVE_CLASS = "negative"
_NEUTRAL_CLASS = "neutral"
# Sign threshold for choosing a delta class.
_ZERO = 0


def _system_text(system, resolver) -> str:
    """Return a system's display name, else the configured unknown default."""
    if system is None:
        return resolver.generic(*_UNKNOWN_SYSTEM)
    return str(system)


def _visited_text(visited, fmt, resolver) -> str:
    """Return the systems-visited count, else the configured unknown default.

    A commander is always somewhere, so a count of zero is never a true
    reading. None means nothing was recorded and the report says so instead.
    """
    if visited is None:
        return resolver.generic(*_UNKNOWN_SYSTEM)
    return fmt.integer(visited)


def build_header(debrief, fmt, resolver) -> HeaderView:
    """Build the header sub-view from the commander, window and systems."""
    return HeaderView(
        commander=debrief.commander.name,
        ship=debrief.ship or resolver.generic(*_UNKNOWN_SHIP),
        ship_name=debrief.ship_name,
        session_start=fmt.datetime(debrief.window.start.iso_utc),
        session_end=fmt.datetime(debrief.window.end.iso_utc),
        duration=fmt.duration(debrief.window.duration_s),
        start_system=_system_text(debrief.start_system, resolver),
        end_system=_system_text(debrief.end_system, resolver),
        systems_visited=_visited_text(debrief.systems_visited, fmt, resolver),
    )


def _delta_class(value: int) -> str:
    """Return the CSS direction class for a signed value."""
    if value > _ZERO:
        return _POSITIVE_CLASS
    if value < _ZERO:
        return _NEGATIVE_CLASS
    return _NEUTRAL_CLASS


def _net_credits_item(debrief, fmt, resolver) -> HeadlineItem:
    """Build the credits headline: the balance, with the session change beside it.

    The value slot carries the level and the delta slot the change. They used to
    carry the same number, so a session with no credit events rendered its zero
    delta in the value slot and read as a balance of nothing to anyone glancing
    at the report. The balance is whatever the journal last stated; when it
    stated none, the value slot says so rather than showing a figure the reader
    would take for a real one.
    """
    net = debrief.net_credits_delta
    balance = debrief.credits_balance
    value_display = (
        resolver.generic(*_BALANCE_UNKNOWN)
        if balance is None
        else fmt.credits(balance.value)
    )
    # A net change of None means the journal stated too few balances to measure
    # one. The delta slot then says so rather than showing a zero the reader
    # would take for a session that broke even.
    delta_display = (
        resolver.generic(*_CHANGE_UNKNOWN) if net is None else fmt.signed_credits(net)
    )
    return HeadlineItem(
        label=resolver.headline_label(*_CREDITS_HEADLINE),
        value_display=value_display,
        delta_display=delta_display,
        delta_class=_NEUTRAL_CLASS if net is None else _delta_class(net),
    )


def _count_item(label_key: tuple[str, str], count: int, resolver, fmt) -> HeadlineItem:
    """Build a simple count headline item with no delta."""
    return HeadlineItem(
        label=resolver.headline_label(*label_key),
        value_display=fmt.integer(count),
        delta_display=None,
        delta_class=_NEUTRAL_CLASS,
    )


def build_headline(debrief, fmt, resolver) -> tuple[HeadlineItem, ...]:
    """Build the headline metrics row from the activity rollups."""
    activity = debrief.activity
    jumps = activity.flight.jumps if activity.flight is not None else _ZERO
    scanned = (
        activity.exploration.bodies_scanned
        if activity.exploration is not None
        else _ZERO
    )
    kills = activity.combat.kills if activity.combat is not None else _ZERO
    return (
        _net_credits_item(debrief, fmt, resolver),
        _count_item(_JUMPS_HEADLINE, jumps, resolver, fmt),
        _count_item(_BODIES_HEADLINE, scanned, resolver, fmt),
        _count_item(_KILLS_HEADLINE, kills, resolver, fmt),
    )


def _moment_system(moment) -> str | None:
    """Return the star system named in a moment's detail, if any."""
    for key, value in moment.detail:
        if key == _STAR_SYSTEM_FIELD and isinstance(value, str) and value.strip():
            return value
    return None


def _timeline_entry(moment, fmt, resolver, renderer) -> TimelineEntry:
    """Build one formatted timeline entry from a single moment.

    The row's icon is the moment's activity (domain) glyph, so it shows what
    was done; the control mode rides along as the compact tag and full label.
    The row text comes from ``timeline_text.row_text``, which assembles death,
    ship-launched-vehicle, bounty and mission rows itself and words every other
    row from the moment's taxonomy template. The formatter is handed on so a
    mission row can show its coins; the renderer so a template can be rendered.
    """
    mode = mode_string_from_name(moment.mode.name)
    return TimelineEntry(
        time_display=fmt.time(moment.occurred_at.iso_utc),
        mode=mode,
        mode_label=resolver.mode_label(mode),
        mode_tag=resolver.mode_tag(mode),
        icon=resolver.domain_icon(moment.domain.name.lower()),
        text=row_text(moment, resolver, fmt, renderer),
        system=_moment_system(moment),
    )


def build_timeline(debrief, fmt, resolver, renderer=None) -> tuple[TimelineEntry, ...]:
    """Build one timeline entry per moment, most recent first."""
    return tuple(
        _timeline_entry(moment, fmt, resolver, renderer)
        for moment in reversed(debrief.moments)
    )


def build_timeline_categories(
    debrief, fmt, resolver, renderer=None
) -> tuple[TimelineCategory, ...]:
    """Group the timeline by activity domain, in the canonical domain order.

    Each category carries only its own moments, most recent first, so the
    report can offer per-category views beside the full session log.
    Domains with no moments this session are omitted.
    """
    grouped: dict[str, list[TimelineEntry]] = {}
    for moment in reversed(debrief.moments):
        key = moment.domain.name.lower()
        grouped.setdefault(key, []).append(
            _timeline_entry(moment, fmt, resolver, renderer)
        )
    categories: list[TimelineCategory] = []
    for key in DOMAIN_ORDER:
        entries = grouped.get(key)
        if not entries:
            continue
        categories.append(
            TimelineCategory(
                key=key,
                label=resolver.domain_title(key),
                icon=resolver.domain_icon(key),
                count=len(entries),
                entries=tuple(entries),
            )
        )
    return tuple(categories)


def build_ranks(debrief, fmt, resolver) -> tuple[RankChange, ...]:
    """Build a RankChange for every ladder in the standing, in order.

    A promoted ladder renders its from/to tiers; a steady one carries the
    configurable no-change note instead, so the full standing is shown either
    way. The note text comes through the resolver so it is never hardcoded.

    The percentage shown is the domain's level, which is this period's reading
    where there was one and the last known reading otherwise. A ladder with no
    reading at all says so rather than showing a figure a reader would take
    for a standing of zero.
    """
    no_change = resolver.generic(*_RANK_NO_CHANGE)
    no_reading = resolver.generic(*_RANK_NO_READING)
    changes: list[RankChange] = []
    for delta in debrief.rank_progression:
        key = delta.ladder.name.lower()
        level = delta.progress_pct
        changes.append(
            RankChange(
                ladder_title=resolver.ladder_title(key),
                from_tier_name=resolver.tier_name(key, delta.from_tier),
                to_tier_name=resolver.tier_name(key, delta.to_tier),
                promoted=delta.promoted,
                note="" if delta.promoted else no_change,
                progress_pct=level,
                progress_display=(
                    no_reading if level is None else fmt.percent_level(level)
                ),
            )
        )
    return tuple(changes)


def build_footer(debrief, fmt, resolver) -> FooterView:
    """Build the footer sub-view: app identity and the journal span.

    ``generated`` is resolved from the spec rather than a wall clock, since
    the presenter must not read the clock; the journal span comes from the
    session window's event-times.
    """
    return FooterView(
        app_name=resolver.generic(*_APP_NAME),
        app_version=resolver.generic(*_APP_VERSION),
        license=resolver.generic(*_LICENSE),
        generated=resolver.generic(*_GENERATED),
        journal_first=fmt.datetime(debrief.window.start.iso_utc),
        journal_last=fmt.datetime(debrief.window.end.iso_utc),
    )
