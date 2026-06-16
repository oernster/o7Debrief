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

__all__ = [
    "build_header",
    "build_headline",
    "build_timeline",
    "build_timeline_categories",
    "build_ranks",
    "build_footer",
]

# Journal field naming the star system an event occurred in. This is the
# journal's vocabulary (mirrored by the domain), declared here so this module
# stays free of a domain import.
_STAR_SYSTEM_FIELD = "StarSystem"

# Default display strings, resolved through the spec so they stay configurable.
_UNKNOWN_SYSTEM = ("system.unknown", "Unknown")
_UNKNOWN_SHIP = ("header.ship", "Unknown ship")
_NET_CREDITS = ("net_credits", "Net credits")
_JUMPS_HEADLINE = ("jumps", "Jumps")
_BODIES_HEADLINE = ("bodies_scanned", "Bodies scanned")
_KILLS_HEADLINE = ("kills", "Kills")
_APP_NAME = ("footer.app_name", "o7 Debrief")
_APP_VERSION = ("footer.app_version", "0")
_LICENSE = ("footer.license", "")
_GENERATED = ("footer.generated", "")
# Label shown beside a ladder whose tier did not change this period.
_RANK_NO_CHANGE = ("rank.no_change", "(no change)")
# Progress percentage used when a ladder's closing percentage is unknown.
_NO_PCT = 0

# Delta CSS classes for a headline value's direction.
_POSITIVE_CLASS = "positive"
_NEGATIVE_CLASS = "negative"
_NEUTRAL_CLASS = "neutral"
# Sign threshold for choosing a delta class.
_ZERO = 0


def _distinct_systems(moments) -> int:
    """Count the distinct star systems named across the moments' detail."""
    seen: set[str] = set()
    for moment in moments:
        for key, value in moment.detail:
            if key == _STAR_SYSTEM_FIELD and isinstance(value, str) and value.strip():
                seen.add(value)
    return len(seen)


def _system_text(system, resolver) -> str:
    """Return a system's display name, or the configured unknown default."""
    if system is None:
        return resolver.generic(*_UNKNOWN_SYSTEM)
    return str(system)


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
        systems_visited=fmt.integer(_distinct_systems(debrief.moments)),
    )


def _delta_class(value: int) -> str:
    """Return the CSS direction class for a signed value."""
    if value > _ZERO:
        return _POSITIVE_CLASS
    if value < _ZERO:
        return _NEGATIVE_CLASS
    return _NEUTRAL_CLASS


def _net_credits_item(debrief, fmt, resolver) -> HeadlineItem:
    """Build the net-credits headline item with a signed delta."""
    net = debrief.net_credits_delta.value
    return HeadlineItem(
        label=resolver.headline_label(*_NET_CREDITS),
        value_display=fmt.credits(net),
        delta_display=fmt.signed_credits(net),
        delta_class=_delta_class(net),
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


def _timeline_entry(moment, fmt, resolver) -> TimelineEntry:
    """Build one formatted timeline entry from a single moment.

    The row's icon is the moment's activity (domain) glyph, so it shows what
    was done; the control mode rides along as the compact tag and full label.
    """
    mode = mode_string_from_name(moment.mode.name)
    return TimelineEntry(
        time_display=fmt.time(moment.occurred_at.iso_utc),
        mode=mode,
        mode_label=resolver.mode_label(mode),
        mode_tag=resolver.mode_tag(mode),
        icon=resolver.domain_icon(moment.domain.name.lower()),
        text=moment.label,
        system=_moment_system(moment),
    )


def build_timeline(debrief, fmt, resolver) -> tuple[TimelineEntry, ...]:
    """Build one timeline entry per moment, in chronological order."""
    return tuple(_timeline_entry(moment, fmt, resolver) for moment in debrief.moments)


def build_timeline_categories(debrief, fmt, resolver) -> tuple[TimelineCategory, ...]:
    """Group the timeline by activity domain, in the canonical domain order.

    Each category carries only its own moments, still chronological, so the
    report can offer per-category views beside the full time-ordered log.
    Domains with no moments this session are omitted.
    """
    grouped: dict[str, list[TimelineEntry]] = {}
    for moment in debrief.moments:
        key = moment.domain.name.lower()
        grouped.setdefault(key, []).append(_timeline_entry(moment, fmt, resolver))
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


def build_ranks(debrief, resolver) -> tuple[RankChange, ...]:
    """Build a RankChange for every ladder in the standing, in order.

    A promoted ladder renders its from/to tiers; a steady one carries the
    configurable no-change note instead, so the full standing is shown either
    way. The note text comes through the resolver so it is never hardcoded.
    """
    no_change = resolver.generic(*_RANK_NO_CHANGE)
    changes: list[RankChange] = []
    for delta in debrief.rank_progression:
        key = delta.ladder.name.lower()
        changes.append(
            RankChange(
                ladder_title=resolver.ladder_title(key),
                from_tier_name=resolver.tier_name(key, delta.from_tier),
                to_tier_name=resolver.tier_name(key, delta.to_tier),
                promoted=delta.promoted,
                note="" if delta.promoted else no_change,
                progress_pct=delta.end_pct if delta.end_pct is not None else _NO_PCT,
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
