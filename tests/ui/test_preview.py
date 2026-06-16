"""Tests for the debrief preview helper.

The stdlib ``webbrowser.open`` is replaced with a capture so the test asserts
the file is turned into an absolute ``file://`` URI and that the helper relays
the browser's success flag. No real browser is launched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from o7debrief.ui.windows import preview

# Scheme every local file URI must start with.
_FILE_SCHEME = "file://"


def test_open_debrief_passes_file_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The helper converts the path to a file URI before opening it."""
    report = tmp_path / "debrief.html"
    report.write_text("<html></html>", encoding="utf-8")
    captured: list[str] = []

    def fake_open(url: str) -> bool:
        captured.append(url)
        return True

    monkeypatch.setattr(preview.webbrowser, "open", fake_open)

    result = preview.open_debrief(str(report))

    assert result is True
    assert len(captured) == 1
    assert captured[0].startswith(_FILE_SCHEME)
    assert captured[0] == report.resolve().as_uri()


def test_open_debrief_relays_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A False from the browser is relayed back to the caller."""
    report = tmp_path / "debrief.html"
    report.write_text("x", encoding="utf-8")
    monkeypatch.setattr(preview.webbrowser, "open", lambda url: False)

    assert preview.open_debrief(str(report)) is False
