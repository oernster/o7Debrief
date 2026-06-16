"""Journal adapters: locate, tail, parse and map Elite Dangerous journals.

The modules here turn raw ``Journal.*.log`` files into domain ``RawEvent``
tuples without the rest of the system depending on the file format. The public
adapter is ``FileJournalSource`` (see ``file_journal_source``); the other
modules are reusable building blocks (path discovery, an incremental tail
reader, a tolerant line parser and an event mapper).

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
