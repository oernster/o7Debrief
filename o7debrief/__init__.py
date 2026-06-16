"""o7Debrief: Elite Dangerous Commander Mission Debrief generator.

The application version is sourced from the ``VERSION`` file in the project
root, the single source of truth for versioning across the runtime, the build
scripts and the packaging metadata. It is read once here so that
``o7debrief.__version__`` always reflects that file.
"""

from __future__ import annotations

from pathlib import Path

# The VERSION file lives at the project root, one level above this package.
_VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"
# Fallback used only when the VERSION file cannot be found. It is deliberately
# not a real version, so a missing file is obvious rather than silently wrong.
_VERSION_FALLBACK = "0.0.0-dev"

__version__ = (
    _VERSION_FILE.read_text(encoding="utf-8").strip()
    if _VERSION_FILE.exists()
    else _VERSION_FALLBACK
)
__all__ = ["__version__"]
