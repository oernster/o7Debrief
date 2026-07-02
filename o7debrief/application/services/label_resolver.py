"""LabelResolver: resolve display labels and icons from the rollup spec.

The domain stays free of presentation strings, so every title, icon and
rank-tier name the report shows is looked up through the spec's flat label
map under a stable key convention. When a key is absent the resolver falls
back to a readable default derived structurally from the key, never to a
hardcoded domain value. The infrastructure config provider is responsible
for populating the label map richly from the taxonomy.

The resolver keys off plain string identifiers (domain keys, mode strings
and ladder keys) rather than domain enums, so the presenter passes values
read from the domain objects without this module importing the domain. The
``spec`` argument is type-only and is referenced as a forward reference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["LabelResolver", "mode_string_from_name"]

# Key-convention templates for the spec label map. Keeping them here means the
# convention is declared once and shared by every lookup.
_DOMAIN_TITLE_KEY = "domain.{key}.title"
_DOMAIN_ICON_KEY = "domain.{key}.icon"
_DOMAIN_NOTE_KEY = "domain.{key}.note"
_MODE_LABEL_KEY = "mode.{mode}.label"
_MODE_ICON_KEY = "mode.{mode}.icon"
_MODE_TAG_KEY = "mode.{mode}.tag"
_LADDER_TITLE_KEY = "rank.{key}.title"
_TIER_NAME_KEY = "rank.{key}.tier.{index}"
_HEADLINE_LABEL_KEY = "headline.{key}.label"
_MILESTONE_ICON_KEY = "milestone.{key}.icon"
_GENERIC_LABEL_KEY = "label.{key}"

# Canonical mode strings exposed in the view contract, keyed by the upper-case
# ActivityMode member name. Keying by name (not the enum) keeps this module
# free of any domain import while still mapping every mode.
_MODE_STRINGS: dict[str, str] = {
    "SHIP": "ship",
    "SRV": "srv",
    "SLV": "slv",
    "SLF": "slf",
    "ON_FOOT": "foot",
}

# Tokens for building a readable default title from a key or enum-style name.
_KEY_DELIM = "_"
_SPACE = " "
# Sentinel meaning "no note configured" so an absent note stays None.
_NO_NOTE = ""


def mode_string_from_name(mode_name: str) -> str:
    """Return the canonical view mode string for an ActivityMode name."""
    return _MODE_STRINGS[mode_name]


def _titleise(token: str) -> str:
    """Return a readable title built from a key or enum-style token."""
    return token.replace(_KEY_DELIM, _SPACE).title()


class LabelResolver:
    """Resolves titles, icons and tier names via the spec's label map."""

    def __init__(self, spec: RollupSpec) -> None:
        self._spec = spec

    def _lookup(self, key: str, default: str) -> str:
        """Return the configured label for ``key`` or the given default."""
        return self._spec.label_for(key, default)

    def domain_title(self, key: str) -> str:
        """Return the display title for a domain key."""
        return self._lookup(_DOMAIN_TITLE_KEY.format(key=key), _titleise(key))

    def domain_icon(self, key: str) -> str:
        """Return the icon token for a domain key (key default when unset)."""
        return self._lookup(_DOMAIN_ICON_KEY.format(key=key), key)

    def domain_note(self, key: str) -> str | None:
        """Return a domain note, or None when none is configured."""
        note = self._lookup(_DOMAIN_NOTE_KEY.format(key=key), _NO_NOTE)
        return note if note != _NO_NOTE else None

    def mode_label(self, mode: str) -> str:
        """Return the display label for a control-mode string."""
        return self._lookup(_MODE_LABEL_KEY.format(mode=mode), _titleise(mode))

    def mode_icon(self, mode: str) -> str:
        """Return the icon token for a control-mode string."""
        return self._lookup(_MODE_ICON_KEY.format(mode=mode), mode)

    def mode_tag(self, mode: str) -> str:
        """Return the compact control-context tag for a mode string."""
        return self._lookup(_MODE_TAG_KEY.format(mode=mode), mode)

    def ladder_title(self, key: str) -> str:
        """Return the display title for a rank-ladder key."""
        return self._lookup(_LADDER_TITLE_KEY.format(key=key), _titleise(key))

    def tier_name(self, key: str, index: int) -> str:
        """Return the tier name at an index on a ladder key."""
        return self._lookup(_TIER_NAME_KEY.format(key=key, index=index), str(index))

    def headline_label(self, key: str, default: str) -> str:
        """Return the label for a headline metric."""
        return self._lookup(_HEADLINE_LABEL_KEY.format(key=key), default)

    def milestone_icon(self, key: str, default: str) -> str:
        """Return the icon token for a milestone kind."""
        return self._lookup(_MILESTONE_ICON_KEY.format(key=key), default)

    def generic(self, key: str, default: str) -> str:
        """Return a generic configured label by key, else the default."""
        return self._lookup(_GENERIC_LABEL_KEY.format(key=key), default)
