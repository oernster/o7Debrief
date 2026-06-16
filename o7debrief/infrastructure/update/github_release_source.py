"""GitHubReleaseSource: read the latest release tag from the GitHub API.

This adapter implements the application ``ReleaseSource`` port. It performs a
single short, best-effort HTTPS GET against the GitHub releases API using only
the standard library (``urllib``), so the otherwise offline-first app gains no
third-party runtime dependency for one network call. Any failure (no network, a
timeout, a non-2xx status, or an unparseable body) yields None, so the update
check is non-blocking and silent on failure.

The HTTP opener is injected (defaulting to ``urllib.request.urlopen``) so the
adapter can be tested without touching the network.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable

__all__ = ["GitHubReleaseSource"]

# Field in the GitHub "latest release" payload naming the release tag.
_TAG_NAME_FIELD = "tag_name"
# Header advertising a JSON client to the GitHub API.
_ACCEPT_HEADER = "Accept"
_ACCEPT_JSON = "application/vnd.github+json"
# A short timeout (seconds): the check must never block the app for long.
_TIMEOUT_S = 5.0
# Response encoding for the JSON body.
_ENCODING = "utf-8"


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

    def latest_version(self) -> str | None:
        """Return the latest release tag, or None when it cannot be read."""
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
        return tag if isinstance(tag, str) and tag else None
