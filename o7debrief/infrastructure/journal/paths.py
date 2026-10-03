"""Journal directory and file discovery for Elite Dangerous.

Lifted from the author's EDColonisationAsst (``utils/journal.py``) and adapted
to o7Debrief. It locates the journal directory for the current OS (Windows
Saved Games or a Linux Steam Proton / Wine prefix) and lists the
``Journal.*.log`` files oldest to newest. It only ever reads paths; it never
writes to the journal directory.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

__all__ = [
    "JournalDirectoryNotFoundError",
    "find_journal_directory",
    "get_journal_directory",
    "get_journal_files",
    "get_latest_journal_file",
]

# Elite journals live under ".../Saved Games/Frontier Developments/Elite Dangerous".
_FRONTIER_DIR = "Frontier Developments"
_ELITE_DIR = "Elite Dangerous"
_JOURNAL_SUBPATH = Path("Saved Games") / _FRONTIER_DIR / _ELITE_DIR

# Steam App ID for Elite Dangerous, used to build the Proton compatdata path.
_STEAM_APP_ID_ELITE_DANGEROUS = "359320"

# Glob and naming for journal files.
_JOURNAL_GLOB = "Journal.*.log"
# The names the game itself writes: the moment the run began, then the part
# number of the file within that run. The stamp has two forms: the current
# one ("2026-01-02T100000") and the one written before 2021 ("260102100000").
_STAMP_GROUP = "stamp"
_PART_GROUP = "part"
_GAME_NAME = re.compile(
    r"^Journal\.(?P<stamp>\d{4}-\d{2}-\d{2}T\d{6}|\d{12})\.(?P<part>\d+)\.log$"
)
_CURRENT_STAMP = "%Y-%m-%dT%H%M%S"
_CURRENT_STAMP_MARK = "T"
_LEGACY_STAMP = "%y%m%d%H%M%S"

# Index of the most recent file once the list is sorted oldest to newest.
_LATEST = -1

# Environment variable names probed during discovery.
_ENV_HOME = "HOME"
_ENV_USERPROFILE = "USERPROFILE"
_ENV_USER = "USER"
_ENV_USERNAME = "USERNAME"
_ENV_STEAM_COMPAT = "STEAM_COMPAT_DATA_PATH"
_ENV_WINEPREFIX = "WINEPREFIX"

# Default user name used when none can be read from the environment.
_DEFAULT_USER = "user"
# Deterministic non-existent path used only when ``os`` is a test stub.
_NONEXISTENT = "/nonexistent"
# The value of ``os.name`` on Windows.
_OS_NT = "nt"
# The ``__name__`` of the real stdlib ``os`` module; used to tell a test stub
# apart from the genuine module before probing the real machine via Path.home.
_REAL_OS_MODULE_NAME = "os"


class JournalDirectoryNotFoundError(FileNotFoundError):
    """Raised when no Elite Dangerous journal directory can be located."""


def _get_home_dir() -> Path:
    """Resolve a home directory for candidate generation.

    Prefers ``HOME`` or ``USERPROFILE``. When neither is set, ``Path.home()``
    is used only if ``os`` is the real stdlib module; a deterministic fallback
    keeps tests that stub ``os`` from probing the real machine.
    """
    try:
        home_env = os.environ.get(_ENV_HOME) or os.environ.get(_ENV_USERPROFILE)
    except Exception:  # noqa: BLE001 - a stubbed environ may misbehave.
        home_env = None
    if home_env:
        return Path(home_env)

    if getattr(os, "__name__", "") == _REAL_OS_MODULE_NAME:
        return Path.home()

    return Path(_NONEXISTENT)


def _current_user() -> str:
    """Return the current user name from the environment or a default."""
    return os.environ.get(_ENV_USER) or os.environ.get(_ENV_USERNAME) or _DEFAULT_USER


def _proton_compat_candidates(user: str) -> Iterable[Path]:
    """Yield Proton compatdata journal directories from common Steam roots."""
    home = _get_home_dir()

    compat = os.environ.get(_ENV_STEAM_COMPAT)
    if compat:
        compat_path = Path(compat)
        yield compat_path / "pfx" / "drive_c" / "users" / "steamuser" / _JOURNAL_SUBPATH
        yield compat_path / "pfx" / "drive_c" / "users" / user / _JOURNAL_SUBPATH

    steam_roots = [
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / ".local" / "share" / "Steam",
        home
        / ".var"
        / "app"
        / "com.valvesoftware.Steam"
        / ".local"
        / "share"
        / "Steam",
    ]
    for root in steam_roots:
        base = root / "steamapps" / "compatdata" / _STEAM_APP_ID_ELITE_DANGEROUS
        prefix = base / "pfx" / "drive_c" / "users"
        yield prefix / "steamuser" / _JOURNAL_SUBPATH
        yield prefix / user / _JOURNAL_SUBPATH


def _wine_candidates(user: str) -> Iterable[Path]:
    """Yield Wine prefix journal directories (explicit prefix then default)."""
    home = _get_home_dir()
    prefixes: list[Path] = []
    wineprefix = os.environ.get(_ENV_WINEPREFIX)
    if wineprefix:
        prefixes.append(Path(wineprefix))
    prefixes.append(home / ".wine")

    for prefix in prefixes:
        drive_users = prefix / "drive_c" / "users"
        yield drive_users / user / _JOURNAL_SUBPATH
        yield drive_users / "steamuser" / _JOURNAL_SUBPATH


def _iter_linux_journal_candidates() -> Iterable[Path]:
    """Yield likely Elite journal directories on Linux (Proton and Wine)."""
    user = _current_user()
    yield from _proton_compat_candidates(user)
    yield from _wine_candidates(user)


def find_journal_directory() -> Path | None:
    """Best-effort auto-detection of the journal directory for the current OS.

    Returns the directory if it exists, otherwise None.
    """
    if os.name == _OS_NT:
        # Import only on Windows so the ctypes path stays platform-isolated.
        from o7debrief.infrastructure.journal.windows_paths import (
            get_saved_games_path,
        )

        saved_games_path = get_saved_games_path()
        if not saved_games_path:
            return None
        journal_path = saved_games_path / _FRONTIER_DIR / _ELITE_DIR
        return journal_path if journal_path.is_dir() else None

    for candidate in _iter_linux_journal_candidates():
        if candidate.is_dir():
            return candidate
    return None


def get_journal_directory() -> Path:
    """Return the journal directory, raising when none can be found.

    Raises ``JournalDirectoryNotFoundError`` (a ``FileNotFoundError``) listing
    the locations tried on Linux.
    """
    journal_dir = find_journal_directory()
    if journal_dir and journal_dir.is_dir():
        return journal_dir

    if os.name == _OS_NT:
        raise JournalDirectoryNotFoundError(
            "Could not find the Saved Games journal directory on Windows."
        )

    tried = "\n".join(str(path) for path in _iter_linux_journal_candidates())
    raise JournalDirectoryNotFoundError(
        "Could not auto-detect the Elite Dangerous journal directory on Linux.\n"
        "Tried the following locations:\n"
        f"{tried}"
    )


def _game_order(path: Path) -> tuple[datetime, int] | None:
    """Return the (run start, part) a game-written file name states, else None.

    None means the game did not write this name: a copy beside the original,
    a renamed file or a stamp that is not a real moment.
    """
    match = _GAME_NAME.match(path.name)
    if match is None:
        return None
    stamp = match.group(_STAMP_GROUP)
    stamp_format = _CURRENT_STAMP if _CURRENT_STAMP_MARK in stamp else _LEGACY_STAMP
    try:
        # Naive on purpose: the name states no zone and the moment is only
        # compared with other names the same game wrote into the same folder.
        started = datetime.strptime(stamp, stamp_format)  # noqa: DTZ007
    except ValueError:
        return None
    return started, int(match.group(_PART_GROUP))


def get_journal_files(journal_dir: Path) -> list[Path]:
    """Return the journal files to read, oldest to newest.

    The game names each file for the moment its run began, so where any file
    carries such a name only those files are read, ordered by that moment and
    the part number, with the modification time breaking a tie. A
    modification time alone would make a restored or copied old journal the
    newest; a copy read beside its original would count every event twice.
    A folder holding no game-written name at all is still read, oldest first
    by modification time, rather than reported as empty.
    """
    files = list(journal_dir.glob(_JOURNAL_GLOB))
    named = [(order, path) for path in files if (order := _game_order(path))]
    if named:
        named.sort(key=lambda item: (item[0], item[1].stat().st_mtime))
        return [path for _, path in named]
    return sorted(files, key=lambda path: path.stat().st_mtime)


def get_latest_journal_file(journal_dir: Path) -> Path | None:
    """Return the most recent journal file in the directory or None."""
    files = get_journal_files(journal_dir)
    return files[_LATEST] if files else None
