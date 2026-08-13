"""GitHubReleaseSource: read the latest release from the GitHub API.

This adapter implements the application ``ReleaseSource`` port. It performs a
single short, best-effort HTTPS GET against the GitHub releases API using only
the standard library (``urllib``), so the otherwise offline-first app gains no
third-party runtime dependency for one network call. Any failure (no network,
a timeout, a non-2xx status or an unparseable body) yields None, so the
update check is non-blocking and silent on failure.

The endpoint returns only a published, non-draft, non-prerelease release, so
a tag pushed mid-development can never surface here. The release tag's
optional leading "v" is stripped, the human releases page URL is carried
through and each well-formed asset's name and direct URL is kept so the ui
can offer the platform's own installer.

The HTTP opener is injected (defaulting to ``urllib.request.urlopen``) so the
adapter can be tested without touching the network.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from o7debrief.application.dto.release_info import ReleaseAsset, ReleaseInfo

__all__ = ["GitHubReleaseSource"]

# Fields in the GitHub "latest release" payload.
_TAG_NAME_FIELD = "tag_name"
_PAGE_URL_FIELD = "html_url"
_ASSETS_FIELD = "assets"
_ASSET_NAME_FIELD = "name"
_ASSET_URL_FIELD = "browser_download_url"
# Header advertising a JSON client to the GitHub API.
_ACCEPT_HEADER = "Accept"
_ACCEPT_JSON = "application/vnd.github+json"
# A short timeout (seconds): the check must never block the app for long.
_TIMEOUT_S = 5.0
# Response encoding for the JSON body.
_ENCODING = "utf-8"
# Optional release-tag prefix stripped from the reported version.
_TAG_PREFIX = "v"


def _version_from(tag: str) -> str:
    """Return the tag with any leading "v" stripped."""
    return tag[1:] if tag[:1].lower() == _TAG_PREFIX else tag


def _assets_from(raw: object) -> tuple[ReleaseAsset, ...]:
    """Return the well-formed assets, silently dropping malformed entries."""
    if not isinstance(raw, list):
        return ()
    assets = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get(_ASSET_NAME_FIELD)
        url = entry.get(_ASSET_URL_FIELD)
        if isinstance(name, str) and name and isinstance(url, str) and url:
            assets.append(ReleaseAsset(name=name, download_url=url))
    return tuple(assets)


class GitHubReleaseSource:
    """A ``ReleaseSource`` backed by the GitHub latest-release endpoint."""

    def __init__(
        self,
        api_url: str,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout_s: float = _TIMEOUT_S,
    ) -> None:
        self._api_url = api_url
        self._opener = opener
        self._timeout_s = timeout_s

    def latest_release(self) -> ReleaseInfo | None:
        """Return the latest published release or None when it cannot be read."""
        request = urllib.request.Request(
            self._api_url, headers={_ACCEPT_HEADER: _ACCEPT_JSON}
        )
        try:
            with self._opener(request, timeout=self._timeout_s) as response:
                payload = response.read()
            data = json.loads(payload.decode(_ENCODING))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        tag = data.get(_TAG_NAME_FIELD)
        page_url = data.get(_PAGE_URL_FIELD)
        if not isinstance(tag, str) or not tag:
            return None
        if not isinstance(page_url, str) or not page_url:
            return None
        return ReleaseInfo(
            version=_version_from(tag),
            page_url=page_url,
            assets=_assets_from(data.get(_ASSETS_FIELD)),
        )
