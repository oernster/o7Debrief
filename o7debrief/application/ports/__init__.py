"""Ports: the structural interfaces the application depends on.

Every port is a ``typing.Protocol`` so concrete implementations in the
infrastructure layer satisfy them by shape, without importing this layer.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
