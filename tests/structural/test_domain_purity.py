"""Enforce purity of the domain layer.

The domain must be pure: stdlib data structures only, no I/O, no framework and
no reading of the wall clock. This test scans only ``o7debrief/domain`` and
fails on two classes of impurity:

1. IMPORTS outside an allowlist. The domain may import only the pure parts of
   the standard library named in ``ALLOWED_IMPORTS`` and its own package.
   An allowlist rather than a list of known offenders, because a denylist let
   ``time``, ``socket`` and ``subprocess`` through simply by not naming them.
2. CALLS that do I/O or read the clock: a builtin that reaches outside the
   process (``open``, ``print``, ``input``, ``__import__``, ``eval`` and the
   like) and any ``now``, ``today`` or ``utcnow`` call, whatever it is called
   on, so an alias or a qualified ``datetime.datetime.now()`` is caught too.

``datetime`` is allowed: the domain uses its types for event-time. Only the
clock-reading calls are rejected. Imports under ``if TYPE_CHECKING:`` get no
exemption here; the domain has none. What this cannot see is a call reached
indirectly (through ``getattr`` or an object handed in), which is why the
domain's purity also rests on review. British spelling is used in comments.
No em dashes appear anywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = "o7debrief"
DOMAIN = "domain"

# The only modules the domain may import, by top-level name: the pure parts of
# the standard library. Anything else, including a module added to the
# standard library later, fails until it is reviewed and listed here.
ALLOWED_IMPORTS = frozenset(
    {
        "__future__",
        "abc",
        "collections",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "fractions",
        "functools",
        "itertools",
        "math",
        "numbers",
        "operator",
        "re",
        "string",
        "types",
        "typing",
    }
)
# The domain may import itself and no other part of its own package.
OWN_PACKAGE = f"{PACKAGE}.{DOMAIN}"

# Builtins that reach outside the process or around the import checks above.
FORBIDDEN_BUILTINS = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
        "print",
    }
)
# Method names that read the wall clock, rejected on any receiver.
CLOCK_READS = frozenset({"now", "today", "utcnow"})


def _domain_root() -> Path:
    """Return the o7debrief/domain directory relative to this test file."""
    return Path(__file__).resolve().parents[2] / PACKAGE / DOMAIN


def _iter_modules(root: Path):
    """Yield every Python module under root, skipping cache directories."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _allowed(dotted: str) -> bool:
    """Return whether the domain may import the module at ``dotted``."""
    if dotted == OWN_PACKAGE or dotted.startswith(OWN_PACKAGE + "."):
        return True
    return dotted.split(".")[0] in ALLOWED_IMPORTS


def _forbidden_imports_in(tree: ast.AST) -> set[str]:
    """Return every module imported anywhere in a module that is not allowed.

    A relative import stays inside the domain package and is allowed.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names = [node.module or ""]
        else:
            continue
        found.update(name for name in names if not _allowed(name))
    return found


def _forbidden_calls_in(tree: ast.AST) -> set[str]:
    """Return the impure calls found in a module, named as written.

    A builtin is matched by its bare name; a clock read by its attribute,
    whatever it is called on, so ``datetime.datetime.now()`` and an aliased
    ``day.today()`` are both caught.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_BUILTINS:
            found.add(f"{func.id}()")
        elif isinstance(func, ast.Attribute) and func.attr in CLOCK_READS:
            found.add(f"{ast.unparse(func)}()")
    return found


def test_domain_has_no_impure_imports() -> None:
    """The domain imports nothing outside the allowlist."""
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
    """The domain makes no wall-clock read and no I/O call."""
    root = _domain_root()
    assert root.is_dir(), f"domain root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _forbidden_calls_in(tree)
        if bad:
            rel = path.relative_to(root)
            for call in sorted(bad):
                violations.append(f"{rel} calls forbidden {call}")

    assert not violations, "Domain purity (calls):\n" + "\n".join(violations)


# The bypasses a denylist let through, each planted as source and parsed. A
# guard that has never been seen to fail is not yet a guard.
_PLANTED_IMPURE_IMPORTS = (
    "from time import time as wall",
    "import socket",
    "import subprocess",
    "import importlib",
    "from o7debrief.infrastructure import journal",
)
_PLANTED_IMPURE_CALLS = (
    "import datetime\ndatetime.datetime.now()",
    "from datetime import date as day\nday.today()",
    'open("x").read()',
    '__import__("os")',
    'print("x")',
)
_PURE_SOURCE = (
    "from __future__ import annotations\n"
    "import math\n"
    "from datetime import datetime\n"
    "from o7debrief.domain.errors import X\n"
    "from . import sibling\n"
    "moment = datetime.fromisoformat(stamp).time()\n"
)


def test_a_planted_impure_import_is_caught() -> None:
    for source in _PLANTED_IMPURE_IMPORTS:
        assert _forbidden_imports_in(ast.parse(source)), source


def test_a_planted_impure_call_is_caught() -> None:
    for source in _PLANTED_IMPURE_CALLS:
        assert _forbidden_calls_in(ast.parse(source)), source


def test_the_pure_stdlib_the_domain_uses_passes() -> None:
    tree = ast.parse(_PURE_SOURCE)
    assert not _forbidden_imports_in(tree)
    assert not _forbidden_calls_in(tree)
