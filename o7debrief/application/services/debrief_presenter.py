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
from o7debrief.application.ports.text_template_renderer import TextTemplateRenderer
from o7debrief.application.services.label_resolver import LabelResolver
from o7debrief.application.services.presenter_domains import (
    build_domain_sections,
    build_milestones,
)
from o7debrief.application.services.presenter_sections import (
    build_footer,
    build_header,
    build_headline,
    build_month_titles,
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

__all__ = ["DebriefPresenter", "NumberFormat"]

# Wording for a field a rule named but the event never carried. Resolved
# through the spec like every other display string, with the event and field
# substituted in so the reader knows exactly what was not read.
_MISSING_FIELD = (
    "diagnostic.missing_field",
    "{event} carried no {field}, so any amount it should hold reads as zero.",
)
_MISSING_EVENT_TOKEN = "{event}"
_MISSING_FIELD_TOKEN = "{field}"


class DebriefPresenter:
    """Formats a domain SessionDebrief into a presentation DebriefView.

    The ``spec`` and the debrief it presents are domain objects, referred to
    here only as forward references so this module imports just the
    application layer. Their attributes are read by duck typing.

    ``text_renderer`` words each timeline row from the taxonomy template the
    moment carries. It is optional because rendering is an enrichment rather
    than a requirement: without one, every row states its label, which is what
    the report did before the templates were read at all. The composition root
    supplies the real one; a caller that only wants figures need not.
    """

    def __init__(
        self,
        spec: RollupSpec,
        number_format: NumberFormat,
        text_renderer: TextTemplateRenderer | None = None,
    ) -> None:
        self._spec = spec
        self._formatter = ValueFormatter(number_format)
        self._resolver = LabelResolver(spec)
        self._text_renderer = text_renderer

    def _notices(self, missing_fields: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
        """Word each unread field as a notice, in the order they were found."""
        template = self._resolver.generic(*_MISSING_FIELD)
        return tuple(
            template.replace(_MISSING_EVENT_TOKEN, event).replace(
                _MISSING_FIELD_TOKEN, field
            )
            for event, field in missing_fields
        )

    def present(
        self,
        debrief: SessionDebrief,
        missing_fields: tuple[tuple[str, str], ...] = (),
    ) -> DebriefView:
        """Build the fully formatted view for a session debrief.

        ``missing_fields`` are the (event, field) pairs a rule named but the
        matching event never carried. They describe the reading rather than
        the session, so they become notices instead of figures.
        """
        fmt = self._formatter
        resolver = self._resolver
        return DebriefView(
            header=build_header(debrief, fmt, resolver),
            headline=build_headline(debrief, fmt, resolver),
            domains=build_domain_sections(debrief.activity, fmt, resolver),
            timeline=build_timeline(debrief, fmt, resolver, self._text_renderer),
            timeline_categories=build_timeline_categories(
                debrief, fmt, resolver, self._text_renderer
            ),
            month_titles=build_month_titles(debrief, fmt),
            ranks=build_ranks(debrief, fmt, resolver),
            milestones=build_milestones(debrief.moments, self._spec, resolver),
            footer=build_footer(debrief, fmt, resolver),
            notices=self._notices(missing_fields),
        )
