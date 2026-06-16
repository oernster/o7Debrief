"""Application layer: orchestration over the pure domain for o7Debrief.

The application layer depends on the domain and the standard library only.
It never imports infrastructure or ui. Collaborators (journal source,
config provider, exporters, sink, rank store and clock) are defined here
as ``typing.Protocol`` ports and injected through constructors; the outer
layers supply concrete implementations at the composition root.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
