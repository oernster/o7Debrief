"""Preferences DTO: the user-chosen application preferences.

The only preference that matters to a user is the format a generated debrief is
saved as. It defaults to HTML (the canonical self-contained report); Markdown is
the alternative for pasting into Discord or Reddit. The format identifiers equal
the matching exporter extensions, so a preference maps straight onto an exporter.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Preferences",
    "FORMAT_HTML",
    "FORMAT_MARKDOWN",
    "VALID_EXPORT_FORMATS",
    "DEFAULT_EXPORT_FORMAT",
]

# Export-format identifiers, equal to the matching exporter extensions.
FORMAT_HTML = "html"
FORMAT_MARKDOWN = "md"
VALID_EXPORT_FORMATS = (FORMAT_HTML, FORMAT_MARKDOWN)
DEFAULT_EXPORT_FORMAT = FORMAT_HTML


@dataclass(frozen=True, slots=True)
class Preferences:
    """The user's chosen preferences.

    ``export_format`` defaults to HTML. ``output_dir`` is the directory the
    generated debrief files are written to; an empty string means the
    application's default location.
    """

    export_format: str = DEFAULT_EXPORT_FORMAT
    output_dir: str = ""
