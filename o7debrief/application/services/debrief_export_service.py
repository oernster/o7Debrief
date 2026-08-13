"""DebriefExportService: render a view to each format and write it out.

For every requested format the service finds the exporter that produces that
extension, renders the formatted view to bytes and hands them to the sink. The
injected clock stamps a generation time into the filename so successive
exports do not collide. A format with no matching exporter is skipped, so an
unknown request never aborts the others.

A whole-history request takes a different path, because a history report grows
on every session and one document eventually stops being openable. Where a
bundle exporter exists for the format it is used: the log is split into pages
here, in the application and the exporter is handed the split already made.
The bundle goes to one stable directory rewritten in place, so the sink can
compare and leave the pages that did not move alone.

Two things still produce one document. A session report always does, because
it is small and handing somebody the whole file is the point of it. So does a
history report when single-file mode is on or the format has no bundle
exporter and then the log is capped and the footer says how much was left
out, rather than a truncated report passing for a complete one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.application.dto.export_result import ExportResult
from o7debrief.application.dto.history_options import HistoryOptions
from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.ports.clock import Clock
from o7debrief.application.ports.debrief_bundle_exporter import DebriefBundleExporter
from o7debrief.application.ports.debrief_bundle_sink import DebriefBundleSink
from o7debrief.application.ports.debrief_exporter import DebriefExporter
from o7debrief.application.ports.debrief_sink import DebriefSink
from o7debrief.application.services.debrief_naming import NAME_SEPARATOR, NAME_STEM
from o7debrief.application.services.history_capping import capped
from o7debrief.application.services.history_paging import paginate

__all__ = ["BundleWriting", "DebriefExportService"]

# strftime pattern for the filename timestamp: a short, readable, filesystem-
# safe form with no colons, sub-seconds or timezone, e.g. 2026-06-15_10-30-00.
_STAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


@dataclass(frozen=True, slots=True)
class BundleWriting:
    """The bundle half of the service: its exporters, its sink and its limits.

    Grouped into one object because the three are only ever meaningful
    together and because a service constructor taking six positional
    collaborators is a constructor nobody reads.
    """

    exporters: tuple[DebriefBundleExporter, ...]
    sink: DebriefBundleSink
    options: HistoryOptions


class DebriefExportService:
    """Renders a DebriefView into each requested format and persists it."""

    def __init__(
        self,
        exporters: tuple[DebriefExporter, ...],
        sink: DebriefSink,
        clock: Clock,
        bundles: BundleWriting | None = None,
    ) -> None:
        self._exporters = exporters
        self._sink = sink
        self._clock = clock
        self._bundles = bundles

    def _safe_stamp(self) -> str:
        """Return the generation time as a short, filename-safe stamp.

        The clock yields a full ISO-8601 instant; parsing it and reformatting
        drops the sub-second and timezone detail and the colons, giving a name
        like ``2026-06-15_10-30-00`` that is valid on every filesystem.
        """
        moment = datetime.fromisoformat(self._clock.now_utc())
        return moment.strftime(_STAMP_FORMAT)

    def _exporter_for(self, fmt: str) -> DebriefExporter | None:
        """Return the exporter whose extension matches ``fmt`` or None."""
        for exporter in self._exporters:
            if exporter.extension == fmt:
                return exporter
        return None

    def _bundle_exporter_for(self, fmt: str) -> DebriefBundleExporter | None:
        """Return the bundle exporter for ``fmt`` or None if there is none.

        None is the answer for every format in a build wired without bundle
        support and for a format that has no bundle form, such as Markdown.
        Both then fall through to the single-document path.
        """
        if self._bundles is None or self._bundles.options.single_file:
            return None
        for exporter in self._bundles.exporters:
            if exporter.extension == fmt:
                return exporter
        return None

    def _write_bundle(
        self, exporter: DebriefBundleExporter, view: DebriefView, request: RenderRequest
    ) -> str:
        """Split the log, render the bundle and write only what changed."""
        options = self._bundles.options
        pages = paginate(view, options, dict(view.month_titles))
        bundle = exporter.render_bundle(view, pages)
        return self._bundles.sink.write_bundle(bundle, request.output_dir).entry_path

    def _document_view(self, view: DebriefView, request: RenderRequest) -> DebriefView:
        """Return the view to render as one document, capped where it must be."""
        if not request.history or self._bundles is None:
            return view
        return capped(view, self._bundles.options)

    def export(self, view: DebriefView, request: RenderRequest) -> ExportResult:
        """Render and write each requested format; return the paths written."""
        stamp = self._safe_stamp()
        name = f"{NAME_STEM}{NAME_SEPARATOR}{stamp}"
        paths: list[str] = []
        for fmt in request.formats:
            if request.history:
                bundler = self._bundle_exporter_for(fmt)
                if bundler is not None:
                    paths.append(self._write_bundle(bundler, view, request))
                    continue
            exporter = self._exporter_for(fmt)
            if exporter is None:
                continue
            content = exporter.render(self._document_view(view, request))
            written = self._sink.write(
                name, content, exporter.extension, request.output_dir
            )
            paths.append(written)
        return ExportResult(paths=tuple(paths))
