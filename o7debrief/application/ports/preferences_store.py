"""PreferencesStore port: load and save the user's application preferences.

The concrete store persists preferences locally. The application reads and
writes them only through this port, so it never touches the file system or a
serialisation format directly. ``Preferences`` appears only in annotations and
is named as a forward reference, so this port module imports no other layer at
runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from o7debrief.application.dto.preferences import Preferences

__all__ = ["PreferencesStore"]


class PreferencesStore(Protocol):
    """A store of the user's application preferences."""

    def load(self) -> Preferences:
        """Return the saved preferences, or sensible defaults when absent."""
        ...

    def save(self, preferences: Preferences) -> None:
        """Persist the given preferences."""
        ...
