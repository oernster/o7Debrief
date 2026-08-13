"""Enforce the two house prose rules as tests rather than as habits.

The rules, applied to every file in the repository that carries prose (which
includes docstrings, comments, Markdown, the taxonomy's own commentary and the
site):

  - No em dash anywhere. A comma, colon, semicolon or a restructure instead.
  - No comma directly before or after a coordinating conjunction (``and``,
    ``or``, ``but``). This rules out the Oxford comma: "a, b and c", never
    "a, b, and c".

Both drifted for as long as nothing checked them, which is why they are here.
A remembered habit is not a rule; every other invariant in this project is a
test and these are no different.

**The detector must span a line break.** The common breach is a comma ending
one line with the conjunction opening the next, so a per-line search misses the
majority of them and then reports a clean tree, which is worse than no check at
all. The patterns below match across newlines and a test pins that property
directly, because it is the one thing about this suite that could silently stop
working.

A genuine false positive is restructured rather than suppressed. There is no
marker to add: these are prose rules, the constructs they catch are prose
constructs and a line of code that trips one reads better rewritten anyway.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import re
from pathlib import Path

# The em dash, built from its codepoint rather than written out, so the ban can
# be stated here without this file becoming the first thing to break it.
EM_DASH = chr(0x2014)

# A comma before a coordinating conjunction and one after it. ``\s`` matches a
# newline, which is what lets both span a line break.
COMMA_BEFORE = re.compile(r",\s+(?:and|or|but)\b")
COMMA_AFTER = re.compile(r"\b(?:and|or|but)\s*,")

# The file types that carry prose. Binary and generated formats are not here.
PROSE_SUFFIXES = frozenset(
    {".py", ".md", ".toml", ".sh", ".html", ".css", ".txt", ".json"}
)

# This suite is the one file exempt from its own scan, because it necessarily
# holds specimens of both breaches: the detector tests below are what prove the
# rules are enforced, and they cannot demonstrate a breach without containing
# one. Its own prose is held to the rules by review, as the LOC test's named
# exemptions are.
SELF = Path(__file__).name

# Directories that hold dependencies, caches or build output rather than the
# project's own prose. ``installer/payload`` is a staged copy of the app.
SKIPPED_DIRECTORIES = frozenset(
    {
        ".flatpak-build",
        ".flatpak-builder",
        ".flatpak-repo",
        ".flatpak-wheels",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        "dist-installer",
        "node_modules",
        "packaging",
        "payload",
        "venv",
    }
)

# The scan must visit a substantial part of the tree. A guard that quietly
# looks at nothing reports a clean tree exactly as a guard that looks at
# everything does, so the floor is asserted rather than assumed. It is set well
# below the real count so ordinary growth never trips it.
MINIMUM_FILES_SCANNED = 100


def _repository_root() -> Path:
    """Return the repository root, two levels above this test file."""
    return Path(__file__).resolve().parents[2]


def _prose_files(root: Path):
    """Yield every file under root that carries the project's own prose."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in PROSE_SUFFIXES:
            continue
        if SKIPPED_DIRECTORIES & set(path.parts) or path.name == SELF:
            continue
        yield path


def _breaches(text: str) -> int:
    """Return how many comma-beside-conjunction breaches a text holds."""
    return len(COMMA_BEFORE.findall(text)) + len(COMMA_AFTER.findall(text))


def _reported(root: Path) -> tuple[list[str], list[str], int]:
    """Return the em-dash files, the comma breaches and the files scanned."""
    em_dashes: list[str] = []
    commas: list[str] = []
    scanned = 0
    for path in _prose_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        scanned += 1
        relative = path.relative_to(root)
        if EM_DASH in text:
            em_dashes.append(str(relative))
        found = _breaches(text)
        if found:
            commas.append(f"{relative}: {found}")
    return em_dashes, commas, scanned


def test_the_scan_actually_covers_the_tree() -> None:
    """A guard that visits nothing looks exactly like a tree that is clean."""
    _em, _commas, scanned = _reported(_repository_root())

    assert scanned >= MINIMUM_FILES_SCANNED, f"only {scanned} files scanned"


def test_no_em_dash_appears_anywhere() -> None:
    """The em-dash ban is absolute and covers scratch files too."""
    em_dashes, _commas, _scanned = _reported(_repository_root())

    assert not em_dashes, "Em dashes in:\n" + "\n".join(em_dashes)


def test_no_comma_sits_beside_a_coordinating_conjunction() -> None:
    """No Oxford comma; no comma before a clause-joining conjunction either."""
    _em, commas, _scanned = _reported(_repository_root())

    assert not commas, "Comma breaches in:\n" + "\n".join(commas)


def test_the_detector_spans_a_line_break() -> None:
    """The property this whole suite depends on, pinned directly.

    The common breach is a comma ending one line with the conjunction opening
    the next. A per-line search misses every one of those and then reports a
    clean tree, which is the failure this test exists to prevent.
    """
    assert _breaches("first item,\n    and the second") == 1
    assert _breaches("a decision,\n\n    or the other one") == 1


def test_the_detector_catches_a_comma_on_either_side() -> None:
    """Both orderings are breaches: before the conjunction and after it."""
    assert _breaches("a, b, and c") == 1
    assert _breaches("it worked, but it was slow") == 1
    assert _breaches("and, as it turned out, it did") == 1


def test_the_detector_leaves_innocent_prose_alone() -> None:
    """A correctly written list passes, as does a word merely containing one."""
    assert _breaches("a, b and c") == 0
    assert _breaches("the command ran and then stopped") == 0
    # "and" inside another word is not a conjunction.
    assert _breaches("a bandage, a random value, an orange") == 0


def test_a_planted_breach_is_reported(tmp_path) -> None:
    """The guard is proved by failing, not by having never failed.

    The plant is made in a temporary tree rather than in the repository, so a
    crash mid-test cannot leave a breach behind for the next run to trip on.
    """
    clean = tmp_path / "clean.md"
    clean.write_text("One, two and three.\n", encoding="utf-8")
    em_dashes, commas, scanned = _reported(tmp_path)
    assert (em_dashes, commas, scanned) == ([], [], 1)

    (tmp_path / "planted.md").write_text(
        "One, two, and three.\nA line ending in a comma,\nand the rest of it.\n",
        encoding="utf-8",
    )
    (tmp_path / "dashed.md").write_text(f"A sentence {EM_DASH} broken.\n", "utf-8")

    em_dashes, commas, scanned = _reported(tmp_path)

    assert em_dashes == ["dashed.md"]
    assert commas == ["planted.md: 2"]
    assert scanned == 3


def test_a_skipped_directory_is_not_scanned(tmp_path) -> None:
    """Dependencies and build output are not the project's own prose."""
    vendored = tmp_path / "venv" / "lib"
    vendored.mkdir(parents=True)
    (vendored / "other.py").write_text("a, b, and c\n", encoding="utf-8")

    em_dashes, commas, scanned = _reported(tmp_path)

    assert (em_dashes, commas, scanned) == ([], [], 0)
