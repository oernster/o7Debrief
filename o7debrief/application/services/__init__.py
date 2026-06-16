"""Services: constructor-injected orchestration over the domain.

Each service holds its injected collaborators and coordinates domain
functions to perform one job (load config, record a session, build a
debrief, present it, export it, or run the whole one-shot flow). Services
never read the wall clock except through the injected Clock port, and the
domain they call never sees a clock at all.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()
