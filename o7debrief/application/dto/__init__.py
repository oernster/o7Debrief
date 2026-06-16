"""DTOs: immutable data carried across the application's boundaries.

Every DTO is a frozen, slotted dataclass holding plain data (no behaviour
beyond shaping that data for the layers that consume it). Collections are
tuples so the objects stay hashable and unambiguously immutable.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
