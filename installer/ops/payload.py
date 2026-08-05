"""The application bundle the setup program carries, and putting it on disk.

The bundle ships as a single zip because Nuitka's onefile build drops loose
executables and DLLs from an included data directory, so the installer extracts
the archive on deploy. Extraction is member by member rather than a single
``extractall``: it lets the operation report real progress, and it lets every
entry be checked before it is written. British spelling is used in comments. No
em dashes appear anywhere.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from installer.constants import (
    APP_NAME,
    ICON_SUBPATH,
    LICENSE_FILE_NAME,
    PAYLOAD_ARCHIVE_NAME,
    PAYLOAD_DIR_NAME,
    SHORTCUT_ICON_SUBPATH,
    VERSION_FILE_NAME,
)
from installer.ops.errors import PayloadError, UnsafePayloadEntryError
from installer.ops.paths import installed_exe
from installer.ops.progress import (
    EXTRACT_END_PCT,
    EXTRACT_MESSAGE,
    EXTRACT_START_PCT,
    ProgressCallback,
    report,
    scaled,
)
from installer.shared.resource_path import installer_root, program_root

LICENCE_FALLBACK = "The licence text was not bundled with this installer."


def payload_dir() -> Path:
    """Return the directory holding the staged payload."""
    return installer_root() / PAYLOAD_DIR_NAME


def payload_app_dir() -> Path:
    """Return the bundled application directory inside the payload."""
    return payload_dir() / APP_NAME


def payload_archive() -> Path:
    """Return the zipped application bundle inside the payload."""
    return payload_dir() / PAYLOAD_ARCHIVE_NAME


def _first_readable(candidates: tuple[Path, ...]) -> str | None:
    """Return the stripped text of the first candidate that can be read."""
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        return text
    return None


def licence_text() -> str:
    """Return the bundled licence text, or a fallback when it is absent."""
    text = _first_readable(
        (
            payload_dir() / LICENSE_FILE_NAME,
            program_root() / LICENSE_FILE_NAME,
        )
    )
    return text if text else LICENCE_FALLBACK


def app_version() -> str:
    """Return the bundled application version, or an empty string if absent."""
    candidates = (
        payload_app_dir() / VERSION_FILE_NAME,
        payload_dir() / VERSION_FILE_NAME,
        program_root() / VERSION_FILE_NAME,
    )
    for candidate in candidates:
        text = _first_readable((candidate,))
        if text and text.strip():
            return text.strip()
    return ""


def icon_file() -> Path | None:
    """Return the bundled application PNG icon, or None when it is absent."""
    path = payload_app_dir().joinpath(*ICON_SUBPATH)
    return path if path.is_file() else None


def shortcut_icon_file(install_dir: Path) -> Path | None:
    """Return the installed multi-size .ico, or None when it is absent."""
    path = install_dir.joinpath(*SHORTCUT_ICON_SUBPATH)
    return path if path.is_file() else None


def _safe_destination(root: Path, name: str) -> Path:
    """Return the path an archive member writes to, refusing to escape ``root``.

    The payload is produced by this project's own build tooling, so a hostile
    entry is not the expected case. Extraction runs with the user's full
    privileges, though, so the guarantee is enforced rather than assumed.
    """
    destination = (root / name).resolve()
    anchor = root.resolve()
    if destination != anchor and anchor not in destination.parents:
        raise UnsafePayloadEntryError(
            f"Payload entry {name!r} would be written outside {anchor}."
        )
    return destination


def extract_archive(
    archive: Path,
    target: Path,
    *,
    progress: ProgressCallback | None = None,
) -> None:
    """Extract ``archive`` into ``target``, replacing anything already there.

    Any previous install at the target is removed first, so the result is a
    clean deployment rather than a merge of two versions.
    """
    if not archive.is_file():
        raise PayloadError(f"Bundled application not found at {archive}.")
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        total = sum(member.file_size for member in members)
        written = 0
        report(progress, EXTRACT_START_PCT, EXTRACT_MESSAGE)
        for member in members:
            destination = _safe_destination(target, member.filename)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            written += member.file_size
            pct = scaled(written, total, EXTRACT_START_PCT, EXTRACT_END_PCT)
            report(progress, pct, EXTRACT_MESSAGE)


def deploy(
    target: Path,
    *,
    progress: ProgressCallback | None = None,
) -> Path:
    """Extract the bundled application to ``target`` and return its executable."""
    extract_archive(payload_archive(), target, progress=progress)
    return installed_exe(target)
