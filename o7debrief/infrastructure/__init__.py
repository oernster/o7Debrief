"""Infrastructure layer: concrete adapters implementing the application ports.

This layer wires the outside world (the Elite Dangerous journal files, the TOML
taxonomy, the filesystem and the wall clock) to the application's ports. It may
import the domain and the application layers but never the ui layer, and nothing
inside the domain, application or ui layers may import it: the composition root
(``main.py``) is the only place that constructs these adapters.

The concrete adapters are re-exported here so the composition root can wire the
whole system from a single import. This package facade is the one place that
aggregates the adapters; the individual subpackages stay free of re-exports.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from o7debrief.infrastructure.archive.filesystem_debrief_archive import (
    FilesystemDebriefArchive,
)
from o7debrief.infrastructure.autostart.windows_autostart import WindowsAutostart
from o7debrief.infrastructure.clock.system_clock import SystemClock
from o7debrief.infrastructure.config.toml_config_provider import TomlConfigProvider
from o7debrief.infrastructure.journal.file_journal_source import FileJournalSource
from o7debrief.infrastructure.preferences.json_preferences_store import (
    JsonPreferencesStore,
)
from o7debrief.infrastructure.rank.json_rank_snapshot_store import (
    JsonRankSnapshotStore,
)
from o7debrief.infrastructure.render.html_renderer import HtmlDebriefExporter
from o7debrief.infrastructure.render.markdown_renderer import MarkdownDebriefExporter
from o7debrief.infrastructure.sink.filesystem_sink import FilesystemSink
from o7debrief.infrastructure.update.github_release_source import (
    GitHubReleaseSource,
)

__all__ = [
    "FileJournalSource",
    "FilesystemDebriefArchive",
    "FilesystemSink",
    "GitHubReleaseSource",
    "HtmlDebriefExporter",
    "JsonPreferencesStore",
    "JsonRankSnapshotStore",
    "MarkdownDebriefExporter",
    "SystemClock",
    "TomlConfigProvider",
    "WindowsAutostart",
]
