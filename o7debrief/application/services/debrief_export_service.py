"""DebriefExportService: render a view to each format and write it out.

For every requested format the service finds the exporter that produces
that extension, renders the formatted view to bytes and hands them to the
sink. The injected clock stamps a generation time into the filename so
successive exports do not collide. A format with no matching exporter is
skipped, so an unknown request never aborts the others.
"""

from __future__ import annotations

from datetime import datetime

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.dto.export_result import ExportResult
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.ports.clock import Clock
from o7debrief.application.ports.debrief_exporter import DebriefExporter
from o7debrief.application.ports.debrief_sink import DebriefSink
from o7debrief.application.services.debrief_naming import NAME_SEPARATOR, NAME_STEM

__all__ = ["DebriefExportService"]

# strftime pattern for the filename timestamp: a short, readable, filesystem-
# safe form with no colons, sub-seconds or timezone, e.g. 2026-06-15_10-30-00.
_STAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


class DebriefExportService:
    """Renders a DebriefView into each requested format and persists it."""

    def __init__(
        self,
        exporters: tuple[DebriefExporter, ...],
        sink: DebriefSink,
        clock: Clock,
    ) -> None:
        self._exporters = exporters
        self._sink = sink
        self._clock = clock

    def _safe_stamp(self) -> str:
        """Return the generation time as a short, filename-safe stamp.

        The clock yields a full ISO-8601 instant; parsing it and reformatting
        drops the sub-second and timezone detail and the colons, giving a name
        like ``2026-06-15_10-30-00`` that is valid on every filesystem.
        """
        moment = datetime.fromisoformat(self._clock.now_utc())
        return moment.strftime(_STAMP_FORMAT)

    def _exporter_for(self, fmt: str) -> DebriefExporter | None:
        """Return the exporter whose extension matches ``fmt``, or None."""
        for exporter in self._exporters:
            if exporter.extension == fmt:
                return exporter
        return None

    def export(self, view: DebriefView, request: RenderRequest) -> ExportResult:
        """Render and write each requested format; return the paths written."""
        stamp = self._safe_stamp()
        name = f"{NAME_STEM}{NAME_SEPARATOR}{stamp}"
        paths: list[str] = []
        for fmt in request.formats:
            exporter = self._exporter_for(fmt)
            if exporter is None:
                continue
            content = exporter.render(view)
            written = self._sink.write(
                name, content, exporter.extension, request.output_dir
            )
            paths.append(written)
        return ExportResult(paths=tuple(paths))
