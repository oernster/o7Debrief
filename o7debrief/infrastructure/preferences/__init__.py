"""Preferences infrastructure: persist the user's preferences as JSON.

The public adapter is ``JsonPreferencesStore`` (see ``json_preferences_store``),
which stores the user's chosen export format under the per-user state directory.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
