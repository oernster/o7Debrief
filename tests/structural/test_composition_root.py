"""Enforce a single explicit composition root and forbid service singletons.

Two structural properties are checked.

1. Composition-root wiring. Concrete infrastructure adapters are wired into the
   rest of the system in exactly one place, the composition root ``main.py``.
   So only ``main.py`` (which lives at the repository root, outside this
   package) and modules within the infrastructure layer itself may import
   ``o7debrief.infrastructure``. The domain, application and ui layers never
   reach into concrete infrastructure; they depend on it only through the
   application ports, with the implementations injected from the composition
   root. The permitted dependency directions between layers (application on
   domain, infrastructure on domain and application, ui on application) are a
   separate concern checked by the layering test; this test guards only the
   infrastructure wiring boundary.

2. No module-level service singletons. Dependencies are injected through
   constructors from the composition root, never grabbed from a module-level
   global. This test uses a deliberately conservative heuristic: it forbids any
   module-level assignment whose value is a direct call to a name ending in one
   of the role suffixes Service, Controller, Repository or Store (for example
   ``store = JournalStore()`` at module scope).

The heuristic is intentionally narrow to avoid false positives:
  - Only module-level (top-level) assignments are considered; locals inside
    functions and methods are ignored, since those are not singletons.
  - Only assignments whose right-hand side is a Call are considered, so type
    aliases and plain references do not trip it.
  - Only the simple-call forms ``Name(...)`` and ``module.Name(...)`` are
    inspected, and the constructed name must end in a role suffix.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = "o7debrief"
LAYERS = ("domain", "application", "infrastructure", "ui")
INFRASTRUCTURE = "infrastructure"

# Class-name suffixes that denote an injectable collaborator. A module-level
# instance of one of these is treated as a forbidden singleton.
SERVICE_SUFFIXES = ("Service", "Controller", "Repository", "Store")


def _package_root() -> Path:
    """Return the o7debrief package directory relative to this test file."""
    return Path(__file__).resolve().parents[2] / PACKAGE


def _iter_modules(root: Path):
    """Yield every Python module under root, skipping cache directories."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _layer_from_dotted(dotted: str) -> str | None:
    """Return the layer named by a dotted module path, if it is an o7debrief one."""
    parts = dotted.split(".")
    if len(parts) >= 2 and parts[0] == PACKAGE and parts[1] in LAYERS:
        return parts[1]
    return None


def _imported_layers(tree: ast.AST) -> set[str]:
    """Return the set of o7debrief layers a module imports (all import forms)."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                layer = _layer_from_dotted(alias.name)
                if layer is not None:
                    found.add(layer)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            layer = _layer_from_dotted(module)
            if layer is not None:
                found.add(layer)
            elif module == PACKAGE:
                for alias in node.names:
                    if alias.name in LAYERS:
                        found.add(alias.name)
    return found


def _constructed_name(call: ast.Call) -> str | None:
    """Return the simple constructed name of a call, if it has the watched form.

    Recognises ``Name(...)`` and ``module.Name(...)`` and returns the trailing
    name (``Name``). Returns None for any other call shape.
    """
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _assignment_value(node: ast.stmt) -> ast.expr | None:
    """Return the right-hand side of a top-level assignment, else None."""
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _module_level_singletons(tree: ast.Module) -> set[str]:
    """Return constructed names of module-level service-like instantiations.

    Only top-level assignments whose value is a call constructing a name ending
    in a service suffix are reported. Annotated assignments are included so that
    ``store: JournalStore = JournalStore()`` is also caught.
    """
    found: set[str] = set()
    for node in tree.body:
        value = _assignment_value(node)
        if not isinstance(value, ast.Call):
            continue
        name = _constructed_name(value)
        if name is not None and name.endswith(SERVICE_SUFFIXES):
            found.add(name)
    return found


def _is_infrastructure_module(relative: Path) -> bool:
    """Return True when the module lives inside the infrastructure layer."""
    return bool(relative.parts) and relative.parts[0] == INFRASTRUCTURE


def test_only_main_wires_infrastructure() -> None:
    """Only the composition root and infrastructure itself may import infra.

    main.py lives at the repository root (outside this package) and so is never
    visited here, which is precisely the point: nothing inside domain,
    application or ui is allowed to import concrete infrastructure.
    """
    root = _package_root()
    assert root.is_dir(), f"package root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        relative = path.relative_to(root)
        if _is_infrastructure_module(relative):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if INFRASTRUCTURE in _imported_layers(tree):
            violations.append(f"{relative} imports o7debrief.infrastructure")

    assert not violations, (
        "Infrastructure wiring leaked outside the composition root:\n"
        + "\n".join(violations)
    )


def test_no_module_level_service_singletons() -> None:
    """No module instantiates a service-like collaborator at module scope."""
    root = _package_root()
    assert root.is_dir(), f"package root not found: {root}"

    violations: list[str] = []
    for path in _iter_modules(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        singletons = _module_level_singletons(tree)
        if singletons:
            relative = path.relative_to(root)
            for name in sorted(singletons):
                violations.append(f"{relative} instantiates {name} at module scope")

    assert not violations, "Module-level service singletons:\n" + "\n".join(violations)
