"""Enforce the per-module line-count limit.

Every Python module under ``o7debrief/`` and ``tests/`` must be at most 400
lines long. A module that grows past this is a signal to decompose it into
helper modules or capability mixins, which keeps each unit small enough to hold
in the head and to review in one pass. British spelling is used in comments. No
em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

# The maximum permitted number of lines in any single module.
MAX_LINES = 400

# The two trees this rule covers, named relative to the repository root.
SCANNED_TREES = ("o7debrief", "tests")


def _repo_root() -> Path:
    """Return the repository root relative to this test file.

    The test lives at ``<repo>/tests/structural/`` so the root is two parents
    above this file.
    """
    return Path(__file__).resolve().parents[2]


def _iter_modules(root: Path):
    """Yield every Python module under the scanned trees, skipping caches."""
    for tree in SCANNED_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


def _line_count(path: Path) -> int:
    """Return the number of lines in a file.

    Splitting on newlines counts every line including a final unterminated one,
    which is the intuitive notion of file length used by this limit.
    """
    text = path.read_text(encoding="utf-8")
    if text == "":
        return 0
    return len(text.splitlines())


def test_no_module_exceeds_the_line_limit() -> None:
    """No scanned module is longer than the permitted maximum."""
    root = _repo_root()

    offenders: list[str] = []
    for path in _iter_modules(root):
        count = _line_count(path)
        if count > MAX_LINES:
            rel = path.relative_to(root)
            offenders.append(f"{rel}: {count} lines (limit {MAX_LINES})")

    assert not offenders, "Modules over the line limit:\n" + "\n".join(offenders)
