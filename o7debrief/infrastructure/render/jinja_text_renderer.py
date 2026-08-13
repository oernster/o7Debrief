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

from collections.abc import Mapping

from jinja2 import Environment, StrictUndefined, Template, TemplateError

__all__ = ["JinjaTextTemplateRenderer"]


class JinjaTextTemplateRenderer:
    """A ``TextTemplateRenderer`` backed by a strict Jinja2 environment.

    Compiled templates are cached on the instance. A session applies the same
    handful of templates once per moment, so a report of several hundred rows
    compiles a dozen templates rather than one per row. The cache is per
    instance rather than module level, so there is no shared mutable state and
    the renderer stays an ordinary injected collaborator.
    """

    def __init__(self) -> None:
        self._environment = Environment(undefined=StrictUndefined, autoescape=False)
        self._compiled: dict[str, Template | None] = {}

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
