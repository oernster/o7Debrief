"""Tests for GitHubReleaseSource using an injected fake HTTP opener.

The adapter takes its ``urlopen`` as a seam, so these tests cover the success,
missing-field, wrong-shape and failure paths without touching the network.
"""

from __future__ import annotations

import urllib.error

from o7debrief.infrastructure.update.github_release_source import GitHubReleaseSource

_API_URL = "https://api.github.com/repos/o/o7Debrief/releases/latest"


class _FakeResponse:
    """A minimal context-manager response exposing ``read``."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
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


def test_returns_the_tag_name_from_a_valid_payload() -> None:
    source = GitHubReleaseSource(
        _API_URL, opener=_opener_returning(b'{"tag_name": "v1.2.0"}')
    )

    assert source.latest_version() == "v1.2.0"


def test_returns_none_when_the_tag_is_missing() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(b"{}"))

    assert source.latest_version() is None


def test_returns_none_when_the_payload_is_not_an_object() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(b"[1, 2, 3]"))

    assert source.latest_version() is None


def test_returns_none_when_the_body_is_not_json() -> None:
    source = GitHubReleaseSource(_API_URL, opener=_opener_returning(b"not json"))

    assert source.latest_version() is None


def test_returns_none_when_the_request_fails() -> None:
    def failing_opener(request: object, timeout: float) -> object:
        raise urllib.error.URLError("no network")

    source = GitHubReleaseSource(_API_URL, opener=failing_opener)

    assert source.latest_version() is None
