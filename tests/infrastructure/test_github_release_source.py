"""Tests for GitHubReleaseSource using an injected fake HTTP opener.

The adapter takes its ``urlopen`` as a seam, so these tests cover the success,
missing-field, wrong-shape and failure paths without touching the network.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any, Self

from o7debrief.infrastructure.update.github_release_source import GitHubReleaseSource

_API_URL = "https://api.github.com/repos/o/o7Debrief/releases/latest"


class _FakeResponse:
    """A minimal context-manager response exposing ``read``."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _opener_returning(payload: bytes):
    """Return a fake urlopen that yields a response with the given body."""

    def opener(request: object, timeout: float) -> _FakeResponse:
        return _FakeResponse(payload)

    return opener


def _payload(**overrides: Any) -> bytes:
    """Return a valid latest-release payload with the given overrides."""
    data: dict[str, Any] = {
        "tag_name": "v1.2.0",
        "html_url": "https://example.test/rel",
        "assets": [
            {
                "name": "o7DebriefSetup.exe",
                "browser_download_url": "https://example.test/win",
            }
        ],
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


def test_returns_the_release_from_a_valid_payload() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(_payload()))

    release = source.latest_release()

    assert release is not None
    assert release.version == "1.2.0"
    assert release.page_url == "https://example.test/rel"
    assert release.assets[0].name == "o7DebriefSetup.exe"
    assert release.assets[0].download_url == "https://example.test/win"


def test_keeps_a_tag_without_the_v_prefix_as_written() -> None:
    source = GitHubReleaseSource(
        _API_URL, opener=_opener_returning(_payload(tag_name="1.2.0"))
    )

    release = source.latest_release()

    assert release is not None
    assert release.version == "1.2.0"


def test_returns_none_when_the_tag_is_missing_empty_or_wrongly_typed() -> None:
    for override in ({"tag_name": None}, {"tag_name": ""}, {"tag_name": 7}):
        source = GitHubReleaseSource(
            _API_URL, opener=_opener_returning(_payload(**override))
        )

        assert source.latest_release() is None, override


def test_returns_none_when_the_page_url_is_missing_empty_or_wrongly_typed() -> None:
    for override in ({"html_url": None}, {"html_url": ""}, {"html_url": 7}):
        source = GitHubReleaseSource(
            _API_URL, opener=_opener_returning(_payload(**override))
        )

        assert source.latest_release() is None, override


def test_drops_malformed_assets_and_keeps_the_rest() -> None:
    body = _payload(
        assets=[
            "not a dict",
            {"name": "", "browser_download_url": "https://example.test/x"},
            {"name": "no-url.exe"},
            {"name": 7, "browser_download_url": "https://example.test/y"},
            {"name": "good.exe", "browser_download_url": "https://example.test/g"},
            {"name": "bad-url.exe", "browser_download_url": 7},
            {"name": "empty-url.exe", "browser_download_url": ""},
        ]
    )
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(body))

    release = source.latest_release()

    assert release is not None
    assert [asset.name for asset in release.assets] == ["good.exe"]


def test_reads_absent_or_non_list_assets_as_empty() -> None:
    for override in ({"assets": None}, {"assets": "nope"}):
        source = GitHubReleaseSource(
            _API_URL, opener=_opener_returning(_payload(**override))
        )

        release = source.latest_release()

        assert release is not None
        assert release.assets == ()


def test_returns_none_when_the_payload_is_not_an_object() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(b"[1, 2, 3]"))

    assert source.latest_release() is None


def test_returns_none_when_the_body_is_not_json() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(b"not json"))

    assert source.latest_release() is None


def test_returns_none_when_the_request_fails() -> None:
    def failing_opener(request: object, timeout: float) -> object:
        raise urllib.error.URLError("no network")

    source = GitHubReleaseSource(_API_URL, opener=failing_opener)

    assert source.latest_release() is None
