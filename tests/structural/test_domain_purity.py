"""Enforce purity of the domain layer.

The domain must be pure: stdlib data structures only, no I/O, no framework and
no reading of the wall clock. This test scans only ``o7debrief/domain`` and
fails on two classes of impurity:

1. Forbidden CALLS that read real time: ``datetime.now``, ``datetime.today``,
   ``datetime.utcnow`` and ``time.time``. The domain receives event-time from
   the journal instead, so it must never read the clock itself.
2. Forbidden IMPORTS of modules that imply I/O, concurrency, randomness,
   serialisation or a UI framework: os, pathlib, logging, threading, random,
   json, PySide6, jinja2, tomllib.

Importantly, ``from datetime import ...`` is allowed: the domain may use
datetime types for event-time. Only the forbidden time-reading calls are
rejected, detected structurally rather than by import. British spelling is used
in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = "o7debrief"
DOMAIN = "domain"

# Modules the domain must never import.
FORBIDDEN_IMPORTS = frozenset(
    {
        "os",
        "pathlib",
        "logging",
        "threading",
        "random",
        "json",
        "PySide6",
        "jinja2",
        "tomllib",
    }
)

# Wall-clock reads expressed as (object, attribute) call shapes. These match,
# for example, datetime.now(...) and time.time(...).
FORBIDDEN_CALLS = frozenset(
    {
        ("datetime", "now"),
        ("datetime", "today"),
        ("datetime", "utcnow"),
        ("time", "time"),
    }
)


def _domain_root() -> Path:
    """Return the o7debrief/domain directory relative to this test file."""
    return Path(__file__).resolve().parents[2] / PACKAGE / DOMAIN


def _iter_modules(root: Path):
    """Yield every Python module under root, skipping cache directories."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _top_level_name(dotted: str) -> str:
    """Return the first component of a dotted module path."""
    return dotted.split(".")[0]


def _forbidden_imports_in(tree: ast.AST) -> set[str]:
    """Return the set of forbidden modules imported anywhere in a module."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _top_level_name(alias.name) in FORBIDDEN_IMPORTS:
                    found.add(_top_level_name(alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _top_level_name(module) in FORBIDDEN_IMPORTS:
                found.add(_top_level_name(module))
    return found


def _forbidden_calls_in(tree: ast.AST) -> set[tuple[str, str]]:
    """Return the set of forbidden wall-clock call shapes found in a module.

    A call such as ``datetime.now()`` parses as a Call whose func is an
    Attribute (attr ``now``) on a Name (id ``datetime``). Matching this shape
    catches the clock read without forbidding the datetime import itself.
    """
    found: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            shape = (func.value.id, func.attr)
            if shape in FORBIDDEN_CALLS:
                found.add(shape)
    return found


def test_domain_has_no_impure_imports() -> None:
    """The domain imports none of the forbidden I/O or framework modules."""
    root = _domain_root()
    assert root.is_dir(), f"domain root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _forbidden_imports_in(tree)
        if bad:
            rel = path.relative_to(root)
            for name in sorted(bad):
                violations.append(f"{rel} imports forbidden module {name}")

    assert not violations, "Domain purity (imports):\n" + "\n".join(violations)


def test_domain_never_reads_the_clock() -> None:
    """The domain makes no wall-clock call (now/today/utcnow/time.time)."""
    root = _domain_root()
    assert root.is_dir(), f"domain root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _forbidden_calls_in(tree)
        if bad:
            rel = path.relative_to(root)
            for obj, attr in sorted(bad):
                violations.append(f"{rel} calls forbidden {obj}.{attr}()")

    assert not violations, "Domain purity (clock):\n" + "\n".join(violations)
