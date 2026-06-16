"""Tests for the DebriefExportService rendering and writing."""

from __future__ import annotations

from tests.application.fakes import (
    FakeExporter,
    FakeSink,
    FixedClock,
)
from tests.application.test_dto_and_errors import _sample_view

from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.services.debrief_export_service import (
    DebriefExportService,
)

# A clock time containing colons, to exercise filename sanitisation.
_CLOCK_ISO = "2026-06-15T10:00:00Z"


def _service(*exporters: FakeExporter) -> tuple[DebriefExportService, FakeSink]:
    sink = FakeSink()
    service = DebriefExportService(
        exporters=tuple(exporters),
        sink=sink,
        clock=FixedClock(_CLOCK_ISO),
    )
    return service, sink


def test_export_renders_each_requested_format() -> None:
    md = FakeExporter("md", b"# markdown")
    html = FakeExporter("html", b"<h1>html</h1>")
    service, sink = _service(md, html)
    request = RenderRequest(formats=("md", "html"), output_dir="/out")

    result = service.export(_sample_view(), request)

    assert len(result.paths) == 2
    assert len(md.rendered) == 1
    assert len(html.rendered) == 1
    assert [write[2] for write in sink.writes] == ["md", "html"]
    # The request's output directory is threaded through to the sink.
    assert [write[3] for write in sink.writes] == ["/out", "/out"]


def test_export_skips_formats_without_a_matching_exporter() -> None:
    md = FakeExporter("md", b"# markdown")
    service, sink = _service(md)
    request = RenderRequest(formats=("md", "pdf"), output_dir="/out")

    result = service.export(_sample_view(), request)

    # The pdf format has no exporter, so only the md path is produced.
    assert len(result.paths) == 1
    assert sink.writes[0][2] == "md"


def test_export_uses_a_simple_filename_timestamp() -> None:
    md = FakeExporter("md", b"# markdown")
    service, sink = _service(md)
    request = RenderRequest(formats=("md",), output_dir="/out")

    service.export(_sample_view(), request)

    name = sink.writes[0][0]
    # A short, readable, filesystem-safe stamp: no colons, no T, no timezone.
    assert name == "debrief_2026-06-15_10-00-00"
    assert ":" not in name


def test_export_with_no_formats_writes_nothing() -> None:
    md = FakeExporter("md", b"# markdown")
    service, sink = _service(md)
    request = RenderRequest(formats=(), output_dir="/out")

    result = service.export(_sample_view(), request)

    assert result.paths == ()
    assert sink.writes == []
