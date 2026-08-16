"""JinjaTextTemplateRenderer: render taxonomy row templates with Jinja2.

This adapter implements the application ``TextTemplateRenderer`` port. It turns
a taxonomy ``text`` template into the sentence a timeline row shows, rendered
against the raw journal payload the moment carries.

Two decisions carry the module.

Undefined names are STRICT. The point of a row is to state what the journal
actually recorded, so a template naming a field the payload never carried must
fail rather than quietly render a gap. Jinja's default ``Undefined`` renders as
the empty string, which would turn a missing module into "Applied
Weapon_Overcharged grade 5 to ." and read to a commander as a fact. With
``StrictUndefined`` the render raises, this returns ``None`` and the caller
shows the moment's label instead. A template that wants to tolerate an absent
field says so explicitly with Jinja's ``default`` filter, which is exactly how
the localised-name fallbacks in the taxonomy are written.

Output is NOT autoescaped. The rendered text is a plain string that the HTML
exporter escapes itself through its own autoescaping environment; the Markdown
exporter emits it verbatim. Escaping here as well would double-escape an
ampersand in a station or commander name.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from jinja2 import Environment, StrictUndefined, Template, TemplateError

from o7debrief.infrastructure.render.journal_names import NameHumaniser

__all__ = ["JinjaTextTemplateRenderer"]

# Filters a taxonomy template may apply to a journal value. Each turns one of
# the journal's internal tokens into English; the vocabulary behind them is
# taxonomy data, so the filter names are the only part of this that is code.
_MODULE_FILTER = "module"
_BLUEPRINT_FILTER = "blueprint"
_MATERIAL_FILTER = "material"
# Turns a raw journal amount into the report's own credit wording, grouped and
# suffixed. A row stating a price without it printed the digits unbroken
# ("5374463 Cr") beside section totals that were grouped, so the same amount
# was written two ways in one document.
_CREDITS_FILTER = "credits"


class JinjaTextTemplateRenderer:
    """A ``TextTemplateRenderer`` backed by a strict Jinja2 environment.

    Compiled templates are cached on the instance. A session applies the same
    handful of templates once per moment, so a report of several hundred rows
    compiles a dozen templates rather than one per row. The cache is per
    instance rather than module level, so there is no shared mutable state and
    the renderer stays an ordinary injected collaborator.

    An optional ``humaniser`` registers the filters a template uses to turn the
    journal's internal tokens into English (``module``, ``blueprint``,
    ``material``). Without one those filters are undefined, so a template that
    applies them renders nothing and its row falls back to its label: the row
    says less rather than printing ``int_sensors_size5_class2`` at a reader.
    """

    def __init__(
        self,
        humaniser: NameHumaniser | None = None,
        credits_filter: Callable[[int], str] | None = None,
    ) -> None:
        self._environment = Environment(undefined=StrictUndefined, autoescape=False)
        self._compiled: dict[str, Template | None] = {}
        if humaniser is not None:
            self._environment.filters[_MODULE_FILTER] = humaniser.module
            self._environment.filters[_BLUEPRINT_FILTER] = humaniser.blueprint
            self._environment.filters[_MATERIAL_FILTER] = humaniser.material
        if credits_filter is not None:
            self._environment.filters[_CREDITS_FILTER] = credits_filter

    def _template_for(self, template: str) -> Template | None:
        """Return the compiled template; ``None`` if it will not compile.

        A template that fails to compile is cached as ``None`` so a malformed
        taxonomy entry is diagnosed once rather than on every row that uses it.
        """
        if template not in self._compiled:
            try:
                self._compiled[template] = self._environment.from_string(template)
            except TemplateError:
                self._compiled[template] = None
        return self._compiled[template]

    def render(self, template: str, values: Mapping[str, object]) -> str | None:
        """Return the rendered text; ``None`` if it cannot be fully rendered.

        ``None`` means the row wording could not be supported by this payload,
        for either reason: the template would not compile; it named a field the
        event never carried. Both leave the caller showing the label, which
        claims only the kind of thing that happened.
        """
        compiled = self._template_for(template)
        if compiled is None:
            return None
        try:
            return compiled.render(values)
        except TemplateError:
            return None
