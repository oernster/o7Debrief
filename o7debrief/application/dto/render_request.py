"""RenderRequest DTO: what formats to render and where to write them.

The export service reads the requested ``formats`` (matched against each
exporter's extension) and the ``output_dir`` the sink should target.

``history`` says the view covers the whole journal rather than one session.
The two are indistinguishable by the time they reach the export service and
they are written differently: a session report is always one small
self-contained file, while a history report is paged into a bundle or capped
with a truncation notice when one document is asked for anyway.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RenderRequest"]


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """A request to render a debrief into one or more formats."""

    formats: tuple[str, ...]
    output_dir: str
    history: bool = False
