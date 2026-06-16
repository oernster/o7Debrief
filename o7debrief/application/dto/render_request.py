"""RenderRequest DTO: what formats to render and where to write them.

The export service reads the requested ``formats`` (matched against each
exporter's extension) and the ``output_dir`` the sink should target.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RenderRequest"]


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """A request to render a debrief into one or more formats."""

    formats: tuple[str, ...]
    output_dir: str
