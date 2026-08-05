"""The setup program's command line.

The only caller that passes arguments is Windows itself: the UninstallString
recorded in the registry re-invokes a copy of this program with --uninstall.
The quiet and remove-settings flags exist so that same entry point can run
headlessly. British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from installer.constants import UNINSTALL_FLAG

_QUIET_FLAG = "--quiet"
_REMOVE_SETTINGS_FLAG = "--remove-settings"
_STORE_TRUE = "store_true"


@dataclass(frozen=True, slots=True)
class Options:
    """The parsed command line."""

    uninstall: bool
    quiet: bool
    remove_settings: bool


def parse_args(argv: list[str]) -> Options:
    """Parse the installer command line into an immutable Options."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(UNINSTALL_FLAG, dest="uninstall", action=_STORE_TRUE)
    parser.add_argument(_QUIET_FLAG, action=_STORE_TRUE)
    parser.add_argument(_REMOVE_SETTINGS_FLAG, action=_STORE_TRUE)
    parsed = parser.parse_args(argv)
    return Options(
        uninstall=parsed.uninstall,
        quiet=parsed.quiet,
        remove_settings=parsed.remove_settings,
    )
