"""The o7Debrief setup program.

A self-contained PySide6 installer, compiled into a single executable by
buildinstaller.py. The package is split so the privileged work is measurable:

- ``ops`` and ``state`` hold every side effect (payload extraction, shortcuts,
  registry writes, process control) and import no Qt, so they are unit tested
  and held at 100% coverage.
- ``ui`` holds the themed window and dialogs and is the only Qt client.
- ``app`` is the composition root, wiring the two together.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Run the setup program. Defined here so the package is the entry point."""
    from installer.app import main as _main

    return _main(argv)
