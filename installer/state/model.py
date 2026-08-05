"""What the setup program should offer, given what is already installed.

The snapshot is the single input the UI reads to decide its mode, its primary
action and the state of its options, so no widget queries the registry itself.
State is detected from the bundled version passed in rather than read here,
which keeps this package free of any dependency on the payload. British spelling
is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from installer.constants import FALLBACK_VERSION
from installer.state.registry import (
    DEFAULT_KEYS,
    RegistryKeys,
    installed_location,
    installed_version,
    is_autostart_enabled,
)
from installer.state.versioning import NEWER, OLDER, compare_versions


class InstallState:
    """The installed-versus-bundled relationship, driving the primary action."""

    NOT_INSTALLED = "not_installed"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"
    DOWNGRADE = "downgrade"


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """Everything the UI needs to decide what to show, read once at a time."""

    state: str
    bundled_version: str
    installed_version: str
    install_dir: Path
    autostart: bool

    @property
    def installed(self) -> bool:
        """Return True when the application is currently installed."""
        return self.state != InstallState.NOT_INSTALLED


def classify(bundled_version: str, installed: str | None) -> str:
    """Return the install state for a bundled version against an installed one."""
    if installed is None:
        return InstallState.NOT_INSTALLED
    comparison = compare_versions(bundled_version, installed)
    if comparison == NEWER:
        return InstallState.UPGRADE
    if comparison == OLDER:
        return InstallState.DOWNGRADE
    return InstallState.REINSTALL


def detect(
    bundled_version: str,
    default_dir: Path,
    *,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> StateSnapshot:
    """Inspect the machine and return the state the setup program should offer.

    A registration whose recorded location no longer exists is treated as not
    installed: the entry is stale, so offering Repair or Uninstall against a
    directory that has gone would fail rather than help.
    """
    recorded_version = installed_version(keys)
    location = installed_location(keys)
    present = (
        recorded_version is not None and location is not None and location.exists()
    )
    state = classify(bundled_version, recorded_version if present else None)
    return StateSnapshot(
        state=state,
        bundled_version=bundled_version or FALLBACK_VERSION,
        installed_version=recorded_version or "",
        install_dir=location if present and location is not None else default_dir,
        autostart=is_autostart_enabled(keys),
    )
