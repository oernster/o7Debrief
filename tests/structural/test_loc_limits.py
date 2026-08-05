"""Enforce the per-module line-count limit.

Every Python module under ``o7debrief/``, ``installer/`` and ``tests/``, plus
every module at the repository root, must be at most 400 lines long. A module
that grows past this is a signal to decompose it into helper modules or
capability mixins, which keeps each unit small enough to hold in the head and
to review in one pass.

The setup program is in scope deliberately. It was one module of over a thousand
lines that no rule could see, which is exactly the state this limit exists to
prevent. The root was in exactly that state until this rule reached it: the
composition root sat outside every scanned tree and was the largest module in
the project, exempt by accident of location rather than by decision. Two kinds
of root module are exempt now, each named below with its reason, so an exemption
is a stated choice that has to be argued for rather than a gap.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

# The maximum permitted number of lines in any single module.
MAX_LINES = 400

# The trees this rule covers, named relative to the repository root. The staged
# installer payload is build output rather than source, so it is skipped.
SCANNED_TREES = ("o7debrief", "installer", "tests")
SKIPPED_PARTS = ("__pycache__", "payload")

# Root modules exempt from the limit, each with the reason it is exempt.
#
# The composition root is long because it is honest: it is the one place
# permitted to import infrastructure, it constructs every adapter explicitly and
# it deliberately holds no module-level singletons or hidden container. Wiring a
# dozen ports plainly takes the space it takes. The alternative, hiding the
# wiring behind auto-assembly, is banned here for better reasons than length.
#
# The delivery scripts are linear recipes read top to bottom. Splitting a
# sequence of build flags across modules costs more than it buys.
EXEMPT_ROOT_MODULES = {
    "main.py": "composition root: explicit wiring, no container, no singletons",
    "buildexe.py": "delivery script: a linear build recipe",
    "buildinstaller.py": "delivery script: a linear build recipe",
    "stamp_version.py": "delivery script: a linear stamping recipe",
}


def _repo_root() -> Path:
    """Return the repository root relative to this test file.

    The test lives at ``<repo>/tests/structural/`` so the root is two parents
    above this file.
    """
    return Path(__file__).resolve().parents[2]


def _iter_modules(root: Path):
    """Yield every module under the scanned trees and at the root.

    Root modules are yielded too, minus the named exemptions, so nothing sits
    outside the rule merely because of where it lives.
    """
    for tree in SCANNED_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if any(part in SKIPPED_PARTS for part in path.parts):
                continue
            yield path
    for path in sorted(root.glob("*.py")):
        if path.name not in EXEMPT_ROOT_MODULES:
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


def test_every_exempt_root_module_exists_and_carries_a_reason() -> None:
    """The exemption list names real files and states why each is exempt.

    An exemption that outlives its file is how a rule quietly stops applying,
    so the list has to justify itself on every run.
    """
    root = _repo_root()

    missing = [name for name in EXEMPT_ROOT_MODULES if not (root / name).is_file()]
    unexplained = [
        name for name, reason in EXEMPT_ROOT_MODULES.items() if not reason.strip()
    ]

    assert not missing, "Exempt root modules that no longer exist: " + ", ".join(
        missing
    )
    assert not unexplained, "Exempt root modules with no reason: " + ", ".join(
        unexplained
    )
