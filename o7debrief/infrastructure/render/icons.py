"""Map taxonomy icon tokens to display emoji for the renderers.

The taxonomy stores icons as neutral word tokens (for example "rocket") so the
domain and config carry no presentation glyphs. The renderers turn those tokens
into emoji here, in one shared place, falling back to a neutral bullet for any
token without a mapping. Glyphs are written as escapes so the source stays plain
ASCII.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["emoji_for"]

# Neutral glyph used when a token has no specific emoji (a bullet).
_FALLBACK = "•"

# Token to emoji mapping for every icon the taxonomy currently uses, plus the
# milestone icon defaults (medal, star, money) the presenter falls back to.
_EMOJI_BY_TOKEN: dict[str, str] = {
    "rocket": "\U0001f680",
    "telescope": "\U0001f52d",
    "swords": "⚔️",
    "exchange": "\U0001f4b1",
    "pickaxe": "⛏️",
    "clipboard": "\U0001f4cb",
    "wrench": "\U0001f527",
    "anchor": "⚓",
    "buggy": "\U0001f699",
    "boot": "\U0001f97e",
    "leaf": "\U0001f343",
    "ship": "\U0001f6f8",
    "shipyard": "\U0001f3d7️",
    "medal": "\U0001f3c5",
    "star": "⭐",
    "money": "\U0001f4b0",
}


def emoji_for(token: str) -> str:
    """Return the emoji for an icon token, or a neutral bullet if unmapped."""
    return _EMOJI_BY_TOKEN.get(token, _FALLBACK)
