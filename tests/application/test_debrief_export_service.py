"""Tests for the DebriefExportService rendering and writing."""

from __future__ import annotations

from o7debrief.application.dto.render_request import RenderRequest
from o7debrief.application.ports.debrief_bundle_sink import BundleWriteResult
from o7debrief.application.services.debrief_export_service import (
    BundleWriting,
    DebriefExportService,
)
from o7debrief.infrastructure.render.html_bundle_exporter import HtmlBundleExporter
from o7debrief.infrastructure.render.html_renderer import HtmlDebriefExporter
from tests.application.fakes import (
    FakeExporter,
    FakeSink,
    FixedClock,
)
from tests.application.history_builders import history_options, spread, view_of
from tests.application.test_dto_and_errors import _sample_view

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


# ------------------------------------------------ history versus one session


def _bundle_service(sink, bundle_sink, options):
    """Build a service wired for both single documents and bundles."""
    return DebriefExportService(
        (HtmlDebriefExporter(),),
        sink,
        FixedClock(_CLOCK_ISO),
        BundleWriting((HtmlBundleExporter(),), bundle_sink, options),
    )


class _RecordingBundleSink:
    """A bundle sink that records what it was asked to write."""

    def __init__(self) -> None:
        self.bundles: list = []

    def write_bundle(self, bundle, output_dir: str = ""):
        self.bundles.append(bundle)
        return BundleWriteResult(
            entry_path=f"{output_dir}/{bundle.directory_name}/{bundle.entry_point}",
            written=(),
            skipped=(),
            removed=(),
        )


def test_a_session_request_never_takes_the_bundle_path() -> None:
    """A session report stays one file: handing it to somebody is the point."""
    sink = FakeSink()
    bundles = _RecordingBundleSink()
    service = _bundle_service(sink, bundles, history_options())

    service.export(view_of(spread(300)), RenderRequest(("html",), "/out"))

    assert bundles.bundles == []
    assert len(sink.writes) == 1


def test_a_history_request_is_written_as_a_bundle() -> None:
    """A report that grows on every quit is paged rather than accumulated."""
    sink = FakeSink()
    bundles = _RecordingBundleSink()
    service = _bundle_service(sink, bundles, history_options())

    result = service.export(
        view_of(spread(300)), RenderRequest(("html",), "/out", history=True)
    )

    assert len(bundles.bundles) == 1
    assert sink.writes == []
    assert result.paths[0].endswith("debrief_history/index.html")


def test_single_file_mode_sends_a_history_down_the_one_document_path() -> None:
    """The setting for producing one shareable file overrides the bundle."""
    sink = FakeSink()
    bundles = _RecordingBundleSink()
    service = _bundle_service(sink, bundles, history_options(single_file=True))

    service.export(view_of(spread(300)), RenderRequest(("html",), "/out", history=True))

    assert bundles.bundles == []
    assert len(sink.writes) == 1


def test_a_service_wired_without_bundles_still_writes_a_history() -> None:
    """Bundle support is optional wiring, not a precondition for a report."""
    sink = FakeSink()
    service = DebriefExportService(
        (HtmlDebriefExporter(),), sink, FixedClock(_CLOCK_ISO)
    )

    result = service.export(
        view_of(spread(50)), RenderRequest(("html",), "/out", history=True)
    )

    assert len(result.paths) == 1
    assert len(sink.writes) == 1
