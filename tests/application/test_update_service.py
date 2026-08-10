"""Tests for the UpdateService against a fake release source."""

from __future__ import annotations

import pytest

from o7debrief.application.dto.release_info import ReleaseAsset, ReleaseInfo
from o7debrief.application.services.update_service import (
    PLATFORM_KEY_LINUX,
    PLATFORM_KEY_MACOS,
    PLATFORM_KEY_WINDOWS,
    UpdateService,
    platform_key_for,
    select_asset_url,
)
from tests.application.fakes import FakeReleaseSource

# The running version the service compares the latest release against.
_CURRENT = "1.2.0"


def _release(
    version: str = "1.3.0", assets: tuple[ReleaseAsset, ...] | None = None
) -> ReleaseInfo:
    if assets is None:
        assets = (
            ReleaseAsset("o7DebriefSetup.exe", "https://example.test/win"),
            ReleaseAsset("o7debrief.dmg", "https://example.test/mac"),
            ReleaseAsset("o7debrief.flatpak", "https://example.test/linux"),
        )
    return ReleaseInfo(
        version=version, page_url="https://example.test/rel", assets=assets
    )


def test_reports_an_update_when_the_latest_is_newer() -> None:
    service = UpdateService(
        FakeReleaseSource(_release()), _CURRENT, PLATFORM_KEY_WINDOWS
    )

    status = service.check()

    assert status.update_available is True
    assert status.latest == "1.3.0"
    assert status.current == _CURRENT
    assert status.download_url == "https://example.test/win"
    assert status.page_url == "https://example.test/rel"


def test_reports_no_update_when_the_latest_is_not_newer() -> None:
    service = UpdateService(
        FakeReleaseSource(_release("1.1.0")), _CURRENT, PLATFORM_KEY_WINDOWS
    )

    status = service.check()

    assert status.update_available is False
    assert status.latest == "1.1.0"


def test_reports_no_update_when_the_source_is_unreachable() -> None:
    service = UpdateService(FakeReleaseSource(None), _CURRENT, PLATFORM_KEY_WINDOWS)

    status = service.check()

    assert status.update_available is False
    assert status.latest is None
    assert status.current == _CURRENT
    assert status.download_url is None
    assert status.page_url is None


def test_a_skipped_version_is_seen_but_not_available() -> None:
    service = UpdateService(
        FakeReleaseSource(_release()), _CURRENT, PLATFORM_KEY_WINDOWS
    )

    status = service.check(skipped_version="1.3.0")

    assert status.update_available is False
    assert status.latest == "1.3.0"


def test_a_different_skipped_version_still_reports_the_update() -> None:
    service = UpdateService(
        FakeReleaseSource(_release()), _CURRENT, PLATFORM_KEY_WINDOWS
    )

    status = service.check(skipped_version="1.2.5")

    assert status.update_available is True


def test_a_release_without_assets_offers_no_download_url() -> None:
    service = UpdateService(
        FakeReleaseSource(_release(assets=())), _CURRENT, PLATFORM_KEY_WINDOWS
    )

    status = service.check()

    assert status.download_url is None
    assert status.page_url == "https://example.test/rel"


@pytest.mark.parametrize(
    ("sys_platform", "expected"),
    [
        ("win32", PLATFORM_KEY_WINDOWS),
        ("darwin", PLATFORM_KEY_MACOS),
        ("linux", PLATFORM_KEY_LINUX),
        ("freebsd14", PLATFORM_KEY_LINUX),
    ],
)
def test_platform_key_mapping(sys_platform: str, expected: str) -> None:
    assert platform_key_for(sys_platform) == expected


def test_select_asset_url_matches_suffix_case_insensitively() -> None:
    assets = (ReleaseAsset("Setup.EXE", "https://example.test/w"),)

    assert select_asset_url(assets, PLATFORM_KEY_WINDOWS) == "https://example.test/w"
    assert select_asset_url(assets, PLATFORM_KEY_MACOS) is None
    assert select_asset_url((), PLATFORM_KEY_WINDOWS) is None
    assert select_asset_url(assets, "beos") is None
