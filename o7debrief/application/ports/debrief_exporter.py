"""DebriefExporter port: renders a formatted debrief view into bytes.

Each concrete exporter targets one output format (for example Markdown or
HTML). It declares the file ``extension`` it produces and turns a fully
formatted ``DebriefView`` into the bytes for that format.

``DebriefView`` is referenced only as a forward-referenced annotation, so
this port module imports no other layer; concrete exporters in
infrastructure consume the real view by shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from o7debrief.application.dto.debrief_view import DebriefView

__all__ = ["DebriefExporter"]


class DebriefExporter(Protocol):
    """A renderer that turns a DebriefView into bytes for one format."""

    extension: str

    def render(self, view: DebriefView) -> bytes:
        """Render the view into the bytes of this exporter's format."""
        ...
