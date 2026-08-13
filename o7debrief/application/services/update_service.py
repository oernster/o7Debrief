"""UpdateService: decide whether a newer release is available.

The service asks the injected ``ReleaseSource`` for the latest published
release and compares it against the running version. The one network call the
otherwise offline-first app makes happens indirectly through the source and
the service never raises for an unreachable source: the source returns None
and the service reports no update available. The result is a plain
``UpdateStatus`` carrying the platform's own installer asset when the release
has one.

A release version equal to the caller-supplied skipped version is reported as
seen but not available, which is what keeps a version the user chose to skip
from prompting again on the automatic checks; the manual check simply passes
no skipped version in.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.application.dto.update_status import UpdateStatus
from o7debrief.application.services.version_compare import is_newer

if TYPE_CHECKING:
    from o7debrief.application.dto.release_info import ReleaseAsset
    from o7debrief.application.ports.release_source import ReleaseSource

__all__ = ["UpdateService", "platform_key_for", "select_asset_url"]

# Platform keys naming which release asset suits the running platform.
PLATFORM_KEY_WINDOWS = "windows"
PLATFORM_KEY_MACOS = "macos"
PLATFORM_KEY_LINUX = "linux"

# ``sys.platform`` values with a dedicated key; anything else reads as Linux.
_SYS_PLATFORM_KEYS = {
    "win32": PLATFORM_KEY_WINDOWS,
    "darwin": PLATFORM_KEY_MACOS,
}

# Asset filename suffix per platform key, compared case-insensitively.
_ASSET_SUFFIXES = {
    PLATFORM_KEY_WINDOWS: ".exe",
    PLATFORM_KEY_MACOS: ".dmg",
    PLATFORM_KEY_LINUX: ".flatpak",
}


def platform_key_for(sys_platform: str) -> str:
    """Map a ``sys.platform`` value onto an asset platform key."""
    return _SYS_PLATFORM_KEYS.get(sys_platform, PLATFORM_KEY_LINUX)


def select_asset_url(assets: tuple[ReleaseAsset, ...], platform_key: str) -> str | None:
    """Return the download URL of the asset matching ``platform_key``."""
    suffix = _ASSET_SUFFIXES.get(platform_key)
    if suffix is None:
        return None
    for asset in assets:
        if asset.name.lower().endswith(suffix):
            return asset.download_url
    return None


class UpdateService:
    """Compares the running version against the latest available release."""

    def __init__(
        self, source: ReleaseSource, current_version: str, platform_key: str
    ) -> None:
        self._source = source
        self._current_version = current_version
        self._platform_key = platform_key

    def check(self, skipped_version: str | None = None) -> UpdateStatus:
        """Return the update status for the running version.

        A source that cannot be reached yields a None latest version and so a
        status reporting no update, keeping the check silent on failure.
        """
        release = self._source.latest_release()
        if release is None:
            return UpdateStatus(
                current=self._current_version, latest=None, update_available=False
            )
        newer = is_newer(release.version, self._current_version)
        skipped = skipped_version is not None and release.version == skipped_version
        return UpdateStatus(
            current=self._current_version,
            latest=release.version,
            update_available=newer and not skipped,
            download_url=select_asset_url(release.assets, self._platform_key),
            page_url=release.page_url,
        )
