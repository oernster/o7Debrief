"""Enforce clean-architecture layer direction by static import analysis.

The dependency rule is::

    ui -> application -> domain <- infrastructure

with a STRICT ui that may import the application layer only. Concretely, for
imports of one o7debrief layer from another:

    domain         may import none of {application, infrastructure, ui}
    application     may import none of {infrastructure, ui}
    infrastructure  may import none of {ui}
    ui              may import none of {domain, infrastructure}

Imports nested under ``if TYPE_CHECKING:`` are ignored, since they carry no
runtime dependency. British spelling is used in comments. No em dashes appear.
"""

from __future__ import annotations

import ast
from pathlib import Path

# The four layer roots, as immediate subpackages of o7debrief.
LAYERS = ("domain", "application", "infrastructure", "ui")

# Forbidden target layers keyed by the importing layer. This table is the literal
# encoding of the dependency rule documented above.
FORBIDDEN: dict[str, frozenset[str]] = {
    "domain": frozenset({"application", "infrastructure", "ui"}),
    "application": frozenset({"infrastructure", "ui"}),
    "infrastructure": frozenset({"ui"}),
    "ui": frozenset({"domain", "infrastructure"}),
}

# The import root of the package under test.
PACKAGE = "o7debrief"


def _package_root() -> Path:
    """Return the o7debrief package directory relative to this test file.

    The test lives at ``<repo>/tests/structural/`` so the package sits two
    parents up, alongside ``tests``.
    """
    return Path(__file__).resolve().parents[2] / PACKAGE


def _iter_modules(root: Path):
    """Yield every Python module file under root, skipping cache directories."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _layer_of(path: Path, root: Path) -> str | None:
    """Return the layer a module belongs to, or None if it is top level.

    The layer is the first path segment beneath the package root. Modules that
    sit directly in the package root (for example main.py) have no layer.
    """
    relative = path.relative_to(root)
    head = relative.parts[0]
    if head in LAYERS:
        return head
    return None


def _imported_layers(tree: ast.AST) -> set[str]:
    """Collect the set of o7debrief layers referenced by runtime imports.

    Imports nested under ``if TYPE_CHECKING:`` are skipped. Both ``import
    o7debrief.<layer>...`` and ``from o7debrief.<layer> import ...`` forms are
    recognised, including ``from o7debrief import <layer>``.
    """
    found: set[str] = set()
    type_checking_nodes = _type_checking_bodies(tree)

    for node in ast.walk(tree):
        if node in type_checking_nodes:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                layer = _layer_from_dotted(alias.name)
                if layer is not None:
                    found.add(layer)
        elif isinstance(node, ast.ImportFrom):
            found |= _layers_from_importfrom(node)
    return found


def _layers_from_importfrom(node: ast.ImportFrom) -> set[str]:
    """Resolve the layers referenced by a single ``from ... import ...`` node."""
    result: set[str] = set()
    module = node.module or ""
    # Absolute import of the package: "from o7debrief.<layer> ..." or
    # "from o7debrief import <layer>".
    layer = _layer_from_dotted(module)
    if layer is not None:
        result.add(layer)
    elif module == PACKAGE:
        for alias in node.names:
            if alias.name in LAYERS:
                result.add(alias.name)
    return result


def _layer_from_dotted(dotted: str) -> str | None:
    """Return the layer named by a dotted module path, if it is an o7debrief one.

    For example ``o7debrief.domain.errors`` yields ``domain`` while
    ``o7debrief`` or ``json`` yields None.
    """
    parts = dotted.split(".")
    if len(parts) >= 2 and parts[0] == PACKAGE and parts[1] in LAYERS:
        return parts[1]
    return None


def _type_checking_bodies(tree: ast.AST) -> set[ast.AST]:
    """Return every node that lives inside an ``if TYPE_CHECKING:`` block.

    Such imports are type-only and impose no runtime dependency, so the layering
    rule does not apply to them.
    """
    guarded: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_test(node.test):
            for child in node.body:
                for descendant in ast.walk(child):
                    guarded.add(descendant)
    return guarded


def _is_type_checking_test(test: ast.expr) -> bool:
    """Return True if an if-test is the TYPE_CHECKING guard in either form."""
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def test_layer_dependencies_are_respected() -> None:
    """No module imports a layer forbidden to its own layer."""
    root = _package_root()
    assert root.is_dir(), f"package root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        layer = _layer_of(path, root)
        if layer is None:
            # Top-level modules (e.g. main.py) are governed by the composition
            # root test, not the per-layer dependency rule.
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _imported_layers(tree)
        # A layer importing itself is always fine.
        crossed = (imported & FORBIDDEN[layer]) - {layer}
        if crossed:
            rel = path.relative_to(root)
            for bad in sorted(crossed):
                violations.append(f"{layer}/{rel} imports forbidden layer {bad}")

    assert not violations, "Layer dependency violations:\n" + "\n".join(violations)
