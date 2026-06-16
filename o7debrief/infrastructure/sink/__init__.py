"""Sink adapter: persist rendered debrief bytes to the filesystem.

The public adapter is ``FilesystemSink`` (see ``filesystem_sink``), which writes
each rendered debrief atomically to a configured output directory and returns
the path it wrote.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
