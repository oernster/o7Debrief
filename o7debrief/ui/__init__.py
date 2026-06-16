"""UI layer: the PySide6 client of the application for o7Debrief.

This layer owns the system-tray icon and menu, the small view models that
adapt application services for display, the single-instance guard and the
debrief preview. It is a strict client of the application layer: ui modules
import ``o7debrief.application`` and the standard library only, never the
domain and never infrastructure. Concrete collaborators are injected from
the composition root (``main.py``) through constructors; nothing here is a
module-level singleton.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
