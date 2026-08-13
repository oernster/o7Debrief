"""DebriefBundleExporter port: renders a debrief as a multi-file bundle.

A bundle exporter is the counterpart of ``DebriefExporter`` for a report too
large to be one document. It declares the file ``extension`` it produces, so
the export service can match it against a requested format exactly as it does
a single-file exporter, and turns a formatted view into the whole set of files
that make up the report.

The view and the bundle are referenced only as forward-referenced annotations,
so this port module imports no other layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # pragma: no cover - type-only imports, no runtime dependency
    from o7debrief.application.dto.bundle import DebriefBundle
    from o7debrief.application.dto.debrief_view import DebriefView
    from o7debrief.application.dto.log_page import LogPage

__all__ = ["DebriefBundleExporter"]


class DebriefBundleExporter(Protocol):
    """A renderer that turns a DebriefView into a set of related files."""

    extension: str

    def render_bundle(
        self, view: DebriefView, pages: tuple[LogPage, ...]
    ) -> DebriefBundle:
        """Render the view and its already-split pages into the bundle's files.

        Splitting the log is the application's decision and arrives done, so
        an exporter chooses markup and nothing else.
        """
        ...
