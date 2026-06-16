"""Clock adapter: the single source of wall-clock time in the system.

The public adapter is ``SystemClock`` (see ``system_clock``), the one module
permitted to read the wall clock. Everything else receives time through the
application ``Clock`` port.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
