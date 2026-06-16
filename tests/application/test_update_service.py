"""Tests for the UpdateService against a fake release source."""

from __future__ import annotations

from tests.application.fakes import FakeReleaseSource

from o7debrief.application.services.update_service import UpdateService

# The running version the service compares the latest release against.
_CURRENT = "1.2.0"


def test_reports_an_update_when_the_latest_is_newer() -> None:
    service = UpdateService(FakeReleaseSource("1.3.0"), _CURRENT)

    status = service.check()

    assert status.update_available is True
    assert status.latest == "1.3.0"
    assert status.current == _CURRENT


def test_reports_no_update_when_the_latest_is_not_newer() -> None:
    service = UpdateService(FakeReleaseSource("1.1.0"), _CURRENT)

    status = service.check()

    assert status.update_available is False
    assert status.latest == "1.1.0"


def test_reports_no_update_when_the_source_is_unreachable() -> None:
    service = UpdateService(FakeReleaseSource(None), _CURRENT)

    status = service.check()

    assert status.update_available is False
    assert status.latest is None
    assert status.current == _CURRENT
