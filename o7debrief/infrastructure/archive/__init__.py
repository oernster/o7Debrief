"""Archive adapter: list debriefs already written to the output directory.

The public adapter is ``FilesystemDebriefArchive`` (see
``filesystem_debrief_archive``), which globs the directory the sink writes to for
generated debrief files and returns them newest first, in pages.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
