"""DebriefPresenter: format a SessionDebrief into a DebriefView.

This is the single home of presentation in the application: it turns the
pure domain debrief into display-ready strings (digit-grouped credits,
formatted durations and times, resolved labels and icons) and assembles
them into the ``DebriefView`` the exporters and ui consume. It reads its
formatting from a ``NumberFormat`` and its wording from the spec; it never
reads a wall clock.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.services.label_resolver import LabelResolver
from o7debrief.application.services.presenter_domains import (
    build_domain_sections,
    build_milestones,
)
from o7debrief.application.services.presenter_sections import (
    build_footer,
    build_header,
    build_headline,
    build_ranks,
    build_timeline,
    build_timeline_categories,
)
from o7debrief.application.services.value_formatter import (
    NumberFormat,
    ValueFormatter,
)

if TYPE_CHECKING:
    from o7debrief.domain.model.session_debrief import SessionDebrief
    from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["NumberFormat", "DebriefPresenter"]


class DebriefPresenter:
    """Formats a domain SessionDebrief into a presentation DebriefView.

    The ``spec`` and the debrief it presents are domain objects, referred to
    here only as forward references so this module imports just the
    application layer. Their attributes are read by duck typing.
    """

    def __init__(self, spec: RollupSpec, number_format: NumberFormat) -> None:
        self._spec = spec
        self._formatter = ValueFormatter(number_format)
        self._resolver = LabelResolver(spec)

    def present(self, debrief: SessionDebrief) -> DebriefView:
        """Build the fully formatted view for a session debrief."""
        fmt = self._formatter
        resolver = self._resolver
        return DebriefView(
            header=build_header(debrief, fmt, resolver),
            headline=build_headline(debrief, fmt, resolver),
            domains=build_domain_sections(debrief.activity, fmt, resolver),
            timeline=build_timeline(debrief, fmt, resolver),
            timeline_categories=build_timeline_categories(debrief, fmt, resolver),
            ranks=build_ranks(debrief, resolver),
            milestones=build_milestones(debrief.moments, self._spec, resolver),
            footer=build_footer(debrief, fmt, resolver),
        )
