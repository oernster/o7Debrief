"""Tests for the icon-token to emoji mapping used by the renderers."""

from __future__ import annotations

from o7debrief.infrastructure.render.icons import emoji_for


def test_known_tokens_map_to_their_emoji() -> None:
    # The activity glyphs reworked in 1.2.0 plus a stable one for contrast.
    assert emoji_for("swords") == "⚔️"
    assert emoji_for("exchange") == "\U0001f4b1"
    assert emoji_for("shipyard") == "\U0001f3d7️"
    assert emoji_for("rocket") == "\U0001f680"


def test_unknown_token_falls_back_to_a_bullet() -> None:
    assert emoji_for("not-a-token") == "•"
