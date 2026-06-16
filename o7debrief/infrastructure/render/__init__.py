"""Render adapters: turn a formatted DebriefView into output bytes.

The public adapters are ``HtmlDebriefExporter`` (see ``html_renderer``), which
renders one self-contained dark-dossier HTML page, and
``MarkdownDebriefExporter`` (see ``markdown_renderer``), which renders compact
Discord/Reddit Markdown. Both consume only the renderer contract returned by
``DebriefView.to_context()``; the shared ``icons`` module maps taxonomy icon
tokens to display emoji.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
