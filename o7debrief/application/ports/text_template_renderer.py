"""TextTemplateRenderer port: render a taxonomy row template to display text.

The taxonomy states the wording of every timeline row as a template rendered
against the raw journal payload (``"Applied {{ BlueprintName }} grade
{{ Level }} to {{ Module }}."``). Rendering one needs a template engine, which
is a third-party concern and so belongs in infrastructure; the application
depends only on this port and never imports the engine.

The contract is deliberately narrow; its ``None`` return is the important
part. A template that names a field the payload does not carry must NOT render
a sentence with a hole in it ("Applied grade 4 to ."), because a reader cannot
tell a hole from a thing that did not happen. An implementation returns ``None``
for any template it cannot fully satisfy and the caller falls back to the
moment's label, which states the kind and nothing it cannot support.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

__all__ = ["TextTemplateRenderer"]


class TextTemplateRenderer(Protocol):
    """Renders a row template against an event payload."""

    def render(self, template: str, values: Mapping[str, object]) -> str | None:
        """Return the rendered text; ``None`` if it cannot be fully rendered.

        ``None`` covers every way rendering can fall short: a malformed
        template, a field the payload never carried and any engine error. The
        caller treats all of them the same way, by falling back to the label.
        """
        ...
