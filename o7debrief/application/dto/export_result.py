"""ExportResult DTO: the paths produced by an export run.

Returned by the export and one-shot services so the caller knows exactly
which files were written, in the order they were rendered.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ExportResult"]


@dataclass(frozen=True, slots=True)
class ExportResult:
    """The set of file paths written during a single export."""

    paths: tuple[str, ...]
