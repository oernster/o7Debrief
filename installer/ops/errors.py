"""The installer's typed exception hierarchy.

Every failure the setup program reports to the user is one of these, so the UI
can render a message without inspecting exception text. British spelling is used
in comments. No em dashes appear anywhere.
"""

from __future__ import annotations


class InstallerError(Exception):
    """Base class for every failure raised by the installer operations."""


class PayloadError(InstallerError):
    """The bundled application payload is missing or cannot be read."""


class UnsafePayloadEntryError(PayloadError):
    """A payload archive entry would write outside the install directory.

    The payload is built by this project's own tooling, so this should never
    fire; it is the guard that makes that guarantee enforced rather than
    assumed, since extraction runs with the user's full privileges.
    """


class AppRunningError(InstallerError):
    """The application is running, so its files cannot be replaced or removed."""


class AppStillRunningError(AppRunningError):
    """The application was asked to close but was still running afterwards."""
