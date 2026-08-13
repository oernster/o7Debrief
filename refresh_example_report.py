"""Regenerate the example report published on the site.

``docs/example-report.html`` is the sample debrief the site links to. It is not
hand-written and it is not stamped: it is a real report, rendered by the real
exporter from a fixed sample session, so it carries whatever the renderers and
``VERSION`` said at the moment somebody last ran the generator by hand.

That made it a remembered step and the step was not remembered. The published
example stated ``v0`` for the entire life of the project, because the footer
version was defaulted rather than injected and nothing regenerated the file
afterwards. Fixing the footer fixed every future report and left the published
one still saying v0 until it was regenerated.

So regeneration is a build rule now, exactly as version stamping is: both build
scripts call :func:`main` immediately after stamping, so a packaged release can
no longer ship a site whose example disagrees with the binary beside it.

The generator runs as a separate process on purpose. It puts the project root on
``sys.path`` and imports the whole application to render a report; a build
process must not inherit that import state part-way through its own work.

Usage, from the repository root::

    python refresh_example_report.py

The render is deterministic (the sample session is fixed and the footer time
comes from the taxonomy rather than a clock), so a second run rewrites nothing
and says so.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
GENERATOR = PROJECT_ROOT / "tools" / "generate_example_report.py"
EXAMPLE_REPORT = PROJECT_ROOT / "docs" / "example-report.html"

_PREFIX = "[refresh-example]"


def _read(path: Path) -> bytes:
    """Return the file's bytes; empty when it does not exist yet."""
    return path.read_bytes() if path.exists() else b""


def main(argv: list[str] | None = None) -> int:
    """Regenerate the published example report. Returns a process exit code."""
    if argv:
        print(f"{_PREFIX} ERROR: this script takes no arguments.", file=sys.stderr)
        return 2

    if not GENERATOR.is_file():
        print(f"{_PREFIX} ERROR: generator not found at {GENERATOR}.", file=sys.stderr)
        return 1

    before = _read(EXAMPLE_REPORT)
    completed = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    if completed.returncode != 0:
        print(f"{_PREFIX} ERROR: the generator failed.", file=sys.stderr)
        return completed.returncode

    after = _read(EXAMPLE_REPORT)
    if not after:
        print(f"{_PREFIX} ERROR: {EXAMPLE_REPORT} was not written.", file=sys.stderr)
        return 1

    changed = "updated" if after != before else "already current"
    print(f"{_PREFIX} {EXAMPLE_REPORT.name}: {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
