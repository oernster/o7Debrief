"""ReleaseInfo DTOs: a published release as the update check sees it.

Returned by the ``ReleaseSource`` port. ``version`` carries the release tag
with any leading "v" stripped, ``page_url`` is the human releases page and
``assets`` holds each downloadable file's name and direct URL, so the ui can
offer the platform's own installer and fall back to the page when no asset
matches. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReleaseAsset", "ReleaseInfo"]


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One downloadable file attached to a published release."""

    name: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """A published release: its version, page and downloadable assets."""

    version: str
    page_url: str
    assets: tuple[ReleaseAsset, ...] = ()
