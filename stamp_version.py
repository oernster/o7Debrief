"""Stamp the project version into the published site.

``VERSION`` at the repository root is the single source of truth for the version
and every consumer in the tree reads it at runtime or at build time. The site
under ``docs/`` cannot: it is static files served by GitHub Pages, with no build
step to read a file for it. So the site carries the version between delimiters
and this script refreshes it.

Only ``docs/`` is in scope. The tracked Markdown at the repository root
deliberately carries no version data at all and must never be stamped.

A stamped span looks like this. The whole thing including the delimiters is what
a page keeps, so the next run can find it again::

    <!--VERSION-->1.2.3<!--/VERSION-->

The script is idempotent. It rewrites a file only when the stamped value differs
from ``VERSION``, prints every file it changed and prints nothing but a summary
when there was nothing to do, so a second run reports no changes.

Usage, from the repository root::

    python stamp_version.py          # stamp docs/ from VERSION
    python stamp_version.py --check  # report drift without writing anything

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

# The only tree this script may write to. Root Markdown is deliberately excluded:
# it holds no version data and stamping it would introduce some.
SITE_DIR = PROJECT_ROOT / "docs"

# The file types the site is written in. Anything else under docs/ (images, the
# .nojekyll marker) is left alone.
SITE_SUFFIXES = (".html", ".md", ".txt", ".xml", ".json")

OPEN_DELIMITER = "<!--VERSION-->"
CLOSE_DELIMITER = "<!--/VERSION-->"

# Captures whatever currently sits between the delimiters, so a stamp can be
# replaced without disturbing the delimiters themselves.
STAMP_PATTERN = re.compile(
    re.escape(OPEN_DELIMITER) + r"(.*?)" + re.escape(CLOSE_DELIMITER),
    re.DOTALL,
)

ENCODING = "utf-8"

SUCCESS = 0
FAILURE = 1


def read_version() -> str:
    """Return the version from the VERSION file at the repository root."""
    return VERSION_FILE.read_text(encoding=ENCODING).strip()


def site_files() -> list[Path]:
    """Return every stampable file under the site directory, sorted."""
    if not SITE_DIR.is_dir():
        return []
    return sorted(
        path
        for path in SITE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SITE_SUFFIXES
    )


def stamp_text(text: str, version: str) -> tuple[str, int]:
    """Return the text with every stamp set to ``version``, plus how many changed."""
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        if match.group(1) != version:
            changed += 1
        return f"{OPEN_DELIMITER}{version}{CLOSE_DELIMITER}"

    return STAMP_PATTERN.sub(replace, text), changed


def read_site_file(path: Path) -> str:
    """Return a site file's text with its line endings left exactly as they are.

    Newline translation is disabled on both the read and the write so that
    stamping a page changes the stamp and nothing else. A run that silently
    rewrote every line ending would bury the one real change in a whole-file
    diff.
    """
    with open(path, encoding=ENCODING, newline="") as handle:
        return handle.read()


def write_site_file(path: Path, text: str) -> None:
    """Write a site file back, leaving its line endings exactly as they are."""
    with open(path, "w", encoding=ENCODING, newline="") as handle:
        handle.write(text)


def stamp_file(path: Path, version: str, write: bool) -> int:
    """Stamp one file, returning how many stamps were out of date.

    With ``write`` false the file is only inspected, which is what ``--check``
    needs: it must report drift without changing anything.
    """
    stamped, changed = stamp_text(read_site_file(path), version)
    if changed and write:
        write_site_file(path, stamped)
    return changed


def main(argv: list[str] | None = None) -> int:
    """Stamp the site from VERSION; under --check, report drift instead."""
    parser = argparse.ArgumentParser(description="Stamp VERSION into docs/.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report out-of-date stamps without writing anything",
    )
    args = parser.parse_args(argv)

    if not VERSION_FILE.is_file():
        print(f"No VERSION file at {VERSION_FILE}", file=sys.stderr)
        return FAILURE
    version = read_version()
    if not version:
        print(f"{VERSION_FILE} is empty", file=sys.stderr)
        return FAILURE

    files = site_files()
    if not files:
        print(f"No site files found under {SITE_DIR}")
        return SUCCESS

    total_stamps = 0
    updated: list[tuple[Path, int]] = []
    for path in files:
        total_stamps += len(STAMP_PATTERN.findall(read_site_file(path)))
        changed = stamp_file(path, version, write=not args.check)
        if changed:
            updated.append((path, changed))

    verb = "would update" if args.check else "updated"
    for path, changed in updated:
        plural = "" if changed == 1 else "s"
        print(f"{verb} {path.relative_to(PROJECT_ROOT)} ({changed} stamp{plural})")

    print(
        f"Version {version}: {total_stamps} stamp(s) across {len(files)} site file(s), "
        f"{len(updated)} file(s) {verb}."
    )
    if args.check and updated:
        return FAILURE
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
