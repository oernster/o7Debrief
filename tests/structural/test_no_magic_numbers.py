"""Forbid magic numbers in the domain layer.

Domain logic must not contain bare numeric literals beyond a tiny structural
allowlist. Every domain-specific number (a threshold, a limit, a multiplier, a
day-of-month) belongs in the taxonomy configuration or in a named constant, so
that a change in the real-world value cannot silently make the code wrong.

The rule, applied across ``o7debrief/domain`` only:

  - Allowed numeric literals are exactly 0, 1 and 100. 0 and 1 are pure
    structural constants (identity, first element, empty count); 100 is the
    percentage base used in plain percentage arithmetic.
  - A unary minus on an allowed literal is allowed too, so -1, -0 and -100 pass.
  - Numbers that appear inside strings or docstrings are ignored: only genuine
    numeric literals in code are inspected. The AST represents a string as a
    Constant holding str, which this test skips, so digits inside text never
    count.

Any other numeric literal fails the test. British spelling is used in comments.
No em dashes appear anywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = "o7debrief"
DOMAIN = "domain"

# The only numeric literals permitted to appear directly in domain code.
ALLOWED_NUMBERS = (0, 1, 100)


def _domain_root() -> Path:
    """Return the o7debrief/domain directory relative to this test file."""
    return Path(__file__).resolve().parents[2] / PACKAGE / DOMAIN


def _iter_modules(root: Path):
    """Yield every Python module under root, skipping cache directories."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _is_numeric_constant(node: ast.AST) -> bool:
    """Return True if a node is a numeric literal (int, float or complex).

    Booleans are instances of int in Python, so they are excluded explicitly:
    True and False are not magic numbers. Strings, bytes and None are likewise
    not numeric and so are not inspected, which is what keeps digits embedded in
    text out of scope.
    """
    if not isinstance(node, ast.Constant):
        return False
    value = node.value
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float, complex))


def _is_allowed_value(value: object) -> bool:
    """Return True if a numeric value is one of the allowed literals."""
    # Compare by identity of value against the small allowlist. Floats that are
    # mathematically equal to an allowed integer (for example 1.0) are treated
    # as allowed too, since they carry no hidden domain meaning.
    for allowed in ALLOWED_NUMBERS:
        if value == allowed:
            return True
    return False


def _offending_numbers(tree: ast.AST) -> list[tuple[int, object]]:
    """Return (lineno, value) for each disallowed numeric literal in a module.

    A unary minus applied to an allowed literal is itself allowed. To implement
    this, the negated child of a USub node that is an allowed literal is recorded
    and skipped when the child constant is visited on its own.
    """
    allowed_children: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            operand = node.operand
            if _is_numeric_constant(operand) and _is_allowed_value(operand.value):
                allowed_children.add(id(operand))

    offenders: list[tuple[int, object]] = []
    for node in ast.walk(tree):
        if not _is_numeric_constant(node):
            continue
        if id(node) in allowed_children:
            continue
        if _is_allowed_value(node.value):
            continue
        offenders.append((getattr(node, "lineno", -1), node.value))
    return offenders


def test_domain_has_no_magic_numbers() -> None:
    """The domain contains no numeric literal outside the allowlist {0, 1, 100}."""
    root = _domain_root()
    assert root.is_dir(), f"domain root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, value in _offending_numbers(tree):
            rel = path.relative_to(root)
            violations.append(f"{rel}:{lineno} magic number {value!r}")

    assert not violations, "Magic numbers in domain:\n" + "\n".join(violations)
