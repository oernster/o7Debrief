"""DebriefView DTO: the fully formatted render contract.

The presenter produces a ``DebriefView`` holding only display-ready
strings: every credit amount is already digit-grouped, every duration and
time already formatted, every label and icon already resolved. Exporters
and the ui consume the view through ``to_context()``, which yields plain
dicts and lists in the exact shape every renderer expects.

The view is modelled as small frozen sub-views so each section is typed and
immutable, but ``to_context()`` deliberately flattens them back to plain
dicts/lists so renderers never import these classes.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "HeaderView",
    "HeadlineItem",
    "DomainStat",
    "DomainSection",
    "TimelineEntry",
    "TimelineCategory",
    "RankChange",
    "Milestone",
    "FooterView",
    "DebriefView",
]


@dataclass(frozen=True, slots=True)
class HeaderView:
    """The report header: who played, where and for how long."""

    commander: str
    ship: str
    session_start: str
    session_end: str
    duration: str
    start_system: str
    end_system: str
    systems_visited: str

    def as_dict(self) -> dict:
        """Return the header as a plain dict in contract key order."""
        return {
            "commander": self.commander,
            "ship": self.ship,
            "session_start": self.session_start,
            "session_end": self.session_end,
            "duration": self.duration,
            "start_system": self.start_system,
            "end_system": self.end_system,
            "systems_visited": self.systems_visited,
        }


@dataclass(frozen=True, slots=True)
class HeadlineItem:
    """One headline metric with its formatted value and optional delta."""

    label: str
    value_display: str
    delta_display: str | None
    delta_class: str

    def as_dict(self) -> dict:
        """Return the headline item as a plain dict."""
        return {
            "label": self.label,
            "value_display": self.value_display,
            "delta_display": self.delta_display,
            "delta_class": self.delta_class,
        }


@dataclass(frozen=True, slots=True)
class DomainStat:
    """One labelled statistic inside a domain section."""

    label: str
    value_display: str

    def as_dict(self) -> dict:
        """Return the stat as a plain dict."""
        return {"label": self.label, "value_display": self.value_display}


@dataclass(frozen=True, slots=True)
class DomainSection:
    """A domain block: its title, icon, stats and an optional note."""

    key: str
    title: str
    icon: str
    stats: tuple[DomainStat, ...]
    note: str | None

    def as_dict(self) -> dict:
        """Return the section as a plain dict with stats flattened."""
        return {
            "key": self.key,
            "title": self.title,
            "icon": self.icon,
            "stats": [stat.as_dict() for stat in self.stats],
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    """One chronological beat rendered for the timeline."""

    time_display: str
    mode: str
    mode_label: str
    mode_icon: str
    text: str
    system: str | None

    def as_dict(self) -> dict:
        """Return the timeline entry as a plain dict."""
        return {
            "time_display": self.time_display,
            "mode": self.mode,
            "mode_label": self.mode_label,
            "mode_icon": self.mode_icon,
            "text": self.text,
            "system": self.system,
        }


@dataclass(frozen=True, slots=True)
class TimelineCategory:
    """One activity-domain grouping of the timeline, time-ordered within."""

    key: str
    label: str
    icon: str
    count: int
    entries: tuple[TimelineEntry, ...]

    def as_dict(self) -> dict:
        """Return the category as a plain dict with its entries flattened."""
        return {
            "key": self.key,
            "label": self.label,
            "icon": self.icon,
            "count": self.count,
            "entries": [entry.as_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class RankChange:
    """A single ladder's standing rendered for the report.

    ``promoted`` is True when the tier rose this period; ``note`` carries the
    label shown for a steady ladder (for example "(no change)") and is empty
    for a promoted one. ``progress_pct`` is the percentage earned toward the
    next tier (0 to 100).
    """

    ladder_title: str
    from_tier_name: str
    to_tier_name: str
    promoted: bool
    note: str
    progress_pct: int

    def as_dict(self) -> dict:
        """Return the rank change as a plain dict."""
        return {
            "ladder_title": self.ladder_title,
            "from_tier_name": self.from_tier_name,
            "to_tier_name": self.to_tier_name,
            "promoted": self.promoted,
            "note": self.note,
            "progress_pct": self.progress_pct,
        }


@dataclass(frozen=True, slots=True)
class Milestone:
    """A notable highlight with its icon and text."""

    icon: str
    text: str

    def as_dict(self) -> dict:
        """Return the milestone as a plain dict."""
        return {"icon": self.icon, "text": self.text}


@dataclass(frozen=True, slots=True)
class FooterView:
    """The report footer: app identity and journal span."""

    app_name: str
    app_version: str
    license: str
    generated: str
    journal_first: str
    journal_last: str

    def as_dict(self) -> dict:
        """Return the footer as a plain dict in contract key order."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "license": self.license,
            "generated": self.generated,
            "journal_first": self.journal_first,
            "journal_last": self.journal_last,
        }


@dataclass(frozen=True, slots=True)
class DebriefView:
    """The complete formatted render contract for one session debrief."""

    header: HeaderView
    headline: tuple[HeadlineItem, ...]
    domains: tuple[DomainSection, ...]
    timeline: tuple[TimelineEntry, ...]
    ranks: tuple[RankChange, ...]
    milestones: tuple[Milestone, ...]
    footer: FooterView
    timeline_categories: tuple[TimelineCategory, ...] = ()

    def to_context(self) -> dict:
        """Return the view as plain dicts/lists in the renderer contract shape.

        Only changed ranks appear in ``ranks``; the presenter has already
        filtered them. Every value is a display-ready string (or a bool for
        ``promoted``), so renderers perform no formatting of their own.
        """
        return {
            "header": self.header.as_dict(),
            "headline": [item.as_dict() for item in self.headline],
            "domains": [section.as_dict() for section in self.domains],
            "timeline": [entry.as_dict() for entry in self.timeline],
            "timeline_categories": [
                category.as_dict() for category in self.timeline_categories
            ],
            "ranks": [change.as_dict() for change in self.ranks],
            "milestones": [milestone.as_dict() for milestone in self.milestones],
            "footer": self.footer.as_dict(),
        }
