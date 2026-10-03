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
# Wording for a field the event carried in a form no figure can hold (a
# negative balance), which is left out of the report rather than ending it.
_UNREADABLE_FIELD = (
    "diagnostic.unreadable_field",
    (
        "{event} stated a {field} that is not a usable amount, so that reading "
        "was left out."
    ),
)
# Wording for the journal lines that could not be read at all: a torn line or
# one with no usable timestamp. Whatever they recorded is absent from the report.
_UNREADABLE_LINES = (
    "diagnostic.unreadable_lines",
    (
        "Journal lines that could not be read were left out: {count}. Anything "
        "they recorded is missing from this report."
    ),
)
_COUNT_TOKEN = "{count}"


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

    ``app_version`` is required and keyword-only, so no caller can construct a
    presenter that does not know what version it is reporting. It was once a
    taxonomy lookup with a "0" default and the key existed in no taxonomy, so
    the footer of every report read v0.
    """

    def __init__(
        self,
        spec: RollupSpec,
        number_format: NumberFormat,
        text_renderer: TextTemplateRenderer | None = None,
        *,
        app_version: str,
    ) -> None:
        self._spec = spec
        self._formatter = ValueFormatter(number_format)
        self._resolver = LabelResolver(spec)
        self._text_renderer = text_renderer
        self._app_version = app_version

    def _field_notices(
        self, wording: tuple[str, str], fields: tuple[tuple[str, str], ...]
    ) -> tuple[str, ...]:
        """Word each (event, field) pair as a notice, in the order given."""
        template = self._resolver.generic(*wording)
        return tuple(
            template.replace(_MISSING_EVENT_TOKEN, event).replace(
                _MISSING_FIELD_TOKEN, field
            )
            for event, field in fields
        )

    def _notices(
        self,
        missing_fields: tuple[tuple[str, str], ...],
        unreadable_fields: tuple[tuple[str, str], ...],
        unreadable_lines: int,
    ) -> tuple[str, ...]:
        """Word every gap in the reading as a notice."""
        lines = ()
        if unreadable_lines:
            template = self._resolver.generic(*_UNREADABLE_LINES)
            lines = (template.replace(_COUNT_TOKEN, str(unreadable_lines)),)
        return (
            self._field_notices(_MISSING_FIELD, missing_fields)
            + self._field_notices(_UNREADABLE_FIELD, unreadable_fields)
            + lines
        )

    def present(
        self,
        debrief: SessionDebrief,
        missing_fields: tuple[tuple[str, str], ...] = (),
        *,
        unreadable_fields: tuple[tuple[str, str], ...] = (),
        unreadable_lines: int = 0,
    ) -> DebriefView:
        """Build the fully formatted view for a session debrief.

        ``missing_fields`` are the (event, field) pairs a rule named but the
        matching event never carried. They describe the reading rather than
        the session, so they become notices instead of figures. So do
        ``unreadable_fields`` (the pairs whose value no figure can hold) and
        ``unreadable_lines`` (how many journal lines could not be read at all).
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
            footer=build_footer(debrief, fmt, resolver, self._app_version),
            notices=self._notices(missing_fields, unreadable_fields, unreadable_lines),
        )
