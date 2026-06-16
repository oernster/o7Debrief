"""TomlConfigProvider: build a domain RollupSpec from the taxonomy TOML.

This adapter implements the application ``ConfigProvider`` port. It reads the
``debrief_taxonomy.toml`` file with the standard-library ``tomllib`` and maps it
into a domain ``RollupSpec``: a ``BeatRule`` per ``[[beat]]``, a ``ThresholdSet``
from ``[thresholds]`` and a flat label map assembled from the domain, mode and
rank tables. The label keys produced here match exactly the key convention the
application ``LabelResolver`` looks up, so titles, icons and rank-tier names
resolve from the taxonomy with no display string hardcoded in code.

The TOML uses lower-case keys (for example ``on_foot``) while the domain enums
use upper-case member names (``ON_FOOT``); the mappings below bridge the two.
Beat labels are derived from each beat's ``kind`` (titleised) so the timeline
shows a readable, brace-free label rather than the raw Jinja text template.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from o7debrief.domain.rules.rollup_spec import BeatRule, RollupSpec, ThresholdSet
from o7debrief.domain.value_objects.enums import (
    ActivityDomain,
    ActivityMode,
    BeatKind,
)

__all__ = ["TomlConfigProvider"]

# Top-level taxonomy tables and array-of-tables names.
_META = "meta"
_DOMAIN = "domain"
_MODES = "modes"
_BEAT = "beat"
_THRESHOLDS = "thresholds"
_RANK = "rank"

# Keys within tables.
_KEY = "key"
_TITLE = "title"
_ICON = "icon"
_LABEL = "label"
_TIERS = "tiers"
_EVENT = "event"
_KIND = "kind"
_DOMAIN_FIELD = "domain"
_MODE_FIELD = "mode"
_MAGNITUDE_FIELD = "magnitude_field"
_CREDITS_FIELD = "credits_field"
_CREDITS_ARRAY_FIELD = "credits_array_field"
_CREDITS_ITEM_FIELDS = "credits_item_fields"
_SCHEMA_VERSION = "schema_version"
_APP_NAME = "app_name"
_LICENSE = "license"

# Threshold keys, matching the ThresholdSet fields.
_LONG_JUMP_LY = "long_jump_ly"
_BIG_PAYOUT_CREDITS = "big_payout_credits"
_HIGH_VALUE_EXOBIO_CREDITS = "high_value_exobio_credits"

# Label-key templates. These mirror the application LabelResolver convention
# exactly so what we write here is what the resolver reads back.
_DOMAIN_TITLE_KEY = "domain.{key}.title"
_DOMAIN_ICON_KEY = "domain.{key}.icon"
_MODE_LABEL_KEY = "mode.{mode}.label"
_MODE_ICON_KEY = "mode.{mode}.icon"
_LADDER_TITLE_KEY = "rank.{key}.title"
_TIER_NAME_KEY = "rank.{key}.tier.{index}"
# Footer values are read by the presenter via the generic label namespace.
_FOOTER_APP_NAME_KEY = "label.footer.app_name"
_FOOTER_LICENSE_KEY = "label.footer.license"

# Mapping from a taxonomy mode key to its ActivityMode member name. The "foot"
# key maps to ON_FOOT, which an upper-casing rule alone would not produce.
_MODE_TO_ENUM_NAME = {
    "ship": "SHIP",
    "srv": "SRV",
    "foot": "ON_FOOT",
}

# Tokens for deriving a readable beat label from a kind name.
_KEY_DELIM = "_"
_SPACE = " "

# Schema version is exposed as a string by the port.
_SCHEMA_VERSION_FALLBACK = ""


def _titleise(token: str) -> str:
    """Return a readable title from an enum-style token (snake to Title Case)."""
    return token.replace(_KEY_DELIM, _SPACE).title()


def _domain_from(name: str) -> ActivityDomain:
    """Return the ActivityDomain for a lower-case taxonomy domain key."""
    return ActivityDomain[name.upper()]


def _kind_from(name: str) -> BeatKind:
    """Return the BeatKind for a lower-case taxonomy kind key."""
    return BeatKind[name.upper()]


def _mode_from(name: str) -> ActivityMode:
    """Return the ActivityMode for a lower-case taxonomy mode key."""
    return ActivityMode[_MODE_TO_ENUM_NAME[name]]


class TomlConfigProvider:
    """A ``ConfigProvider`` that parses the taxonomy TOML into a RollupSpec.

    The configuration path is injected (a string or Path). The file is read
    lazily on each ``load``/``schema_version`` call so a freshly edited taxonomy
    is always reflected; there is no module-level state and no caching that
    could serve a stale spec.
    """

    def __init__(self, config_path: Path | str) -> None:
        self._config_path = Path(config_path)

    def _read(self) -> dict[str, Any]:
        """Read and parse the taxonomy file into a plain dict."""
        with self._config_path.open("rb") as handle:
            return tomllib.load(handle)

    def schema_version(self) -> str:
        """Return the schema version declared in the taxonomy ``[meta]``."""
        data = self._read()
        meta = data.get(_META, {})
        return str(meta.get(_SCHEMA_VERSION, _SCHEMA_VERSION_FALLBACK))

    def load(self) -> RollupSpec:
        """Build the full RollupSpec from the parsed taxonomy."""
        data = self._read()
        meta = data.get(_META, {})
        return RollupSpec(
            schema_version=str(meta.get(_SCHEMA_VERSION, _SCHEMA_VERSION_FALLBACK)),
            rules=_build_rules(data),
            thresholds=_build_thresholds(data),
            labels=_build_labels(data),
        )


def _build_rules(data: dict[str, Any]) -> tuple[BeatRule, ...]:
    """Build a BeatRule for each ``[[beat]]`` entry in the taxonomy."""
    rules: list[BeatRule] = []
    for beat in data.get(_BEAT, []):
        rules.append(
            BeatRule(
                event_type=beat[_EVENT],
                kind=_kind_from(beat[_KIND]),
                domain=_domain_from(beat[_DOMAIN_FIELD]),
                mode=_mode_from(beat[_MODE_FIELD]),
                magnitude_field=beat.get(_MAGNITUDE_FIELD),
                credits_field=beat.get(_CREDITS_FIELD),
                credits_array_field=beat.get(_CREDITS_ARRAY_FIELD),
                credits_item_fields=tuple(beat.get(_CREDITS_ITEM_FIELDS, ())),
            )
        )
    return tuple(rules)


def _build_thresholds(data: dict[str, Any]) -> ThresholdSet:
    """Build the ThresholdSet from the ``[thresholds]`` table."""
    table = data.get(_THRESHOLDS, {})
    return ThresholdSet(
        long_jump_ly=table[_LONG_JUMP_LY],
        big_payout_credits=table[_BIG_PAYOUT_CREDITS],
        high_value_exobio_credits=table[_HIGH_VALUE_EXOBIO_CREDITS],
    )


def _domain_labels(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return title and icon label pairs for every ``[[domain]]`` entry."""
    pairs: list[tuple[str, str]] = []
    for domain in data.get(_DOMAIN, []):
        key = domain[_KEY]
        pairs.append((_DOMAIN_TITLE_KEY.format(key=key), domain[_TITLE]))
        pairs.append((_DOMAIN_ICON_KEY.format(key=key), domain[_ICON]))
    return pairs


def _mode_labels(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return label and icon pairs for every ``[modes.*]`` table."""
    pairs: list[tuple[str, str]] = []
    modes = data.get(_MODES, {})
    for mode_key, mode in modes.items():
        pairs.append((_MODE_LABEL_KEY.format(mode=mode_key), mode[_LABEL]))
        pairs.append((_MODE_ICON_KEY.format(mode=mode_key), mode[_ICON]))
    return pairs


def _rank_labels(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return title and per-tier name pairs for every ``[[rank]]`` ladder."""
    pairs: list[tuple[str, str]] = []
    for rank in data.get(_RANK, []):
        key = rank[_KEY]
        pairs.append((_LADDER_TITLE_KEY.format(key=key), rank[_TITLE]))
        for index, tier_name in enumerate(rank[_TIERS]):
            pairs.append(
                (_TIER_NAME_KEY.format(key=key, index=index), tier_name)
            )
    return pairs


def _beat_labels(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return an event-type to readable-label pair for every ``[[beat]]``.

    The label is the beat's ``kind`` titleised (for example ``scan_body`` to
    "Scan Body"), giving the timeline a clean, brace-free label derived from
    taxonomy data rather than the raw Jinja text template.
    """
    pairs: list[tuple[str, str]] = []
    for beat in data.get(_BEAT, []):
        pairs.append((beat[_EVENT], _titleise(beat[_KIND])))
    return pairs


def _meta_labels(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return footer label pairs (app name and licence) from ``[meta]``."""
    meta = data.get(_META, {})
    pairs: list[tuple[str, str]] = []
    app_name = meta.get(_APP_NAME)
    if app_name is not None:
        pairs.append((_FOOTER_APP_NAME_KEY, str(app_name)))
    licence = meta.get(_LICENSE)
    if licence is not None:
        pairs.append((_FOOTER_LICENSE_KEY, str(licence)))
    return pairs


def _build_labels(data: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Assemble the full flat label map from every contributing table."""
    pairs: list[tuple[str, str]] = []
    pairs.extend(_domain_labels(data))
    pairs.extend(_mode_labels(data))
    pairs.extend(_rank_labels(data))
    pairs.extend(_beat_labels(data))
    pairs.extend(_meta_labels(data))
    return tuple(pairs)
