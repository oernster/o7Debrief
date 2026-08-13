"""The bundled payload: reading it and putting it on disk safely.

The payload is anchored on the installer package directory, so these tests point
that anchor at a temporary tree and stage a small bundle inside it rather than
touching the real one staged by the build. British spelling is used in comments.
No em dashes appear anywhere.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from installer.constants import (
    APP_NAME,
    EXE_NAME,
    LICENSE_FILE_NAME,
    PAYLOAD_ARCHIVE_NAME,
    PAYLOAD_DIR_NAME,
    VERSION_FILE_NAME,
)
from installer.ops.errors import PayloadError, UnsafePayloadEntryError
from installer.ops.payload import (
    LICENCE_FALLBACK,
    app_version,
    deploy,
    extract_archive,
    icon_file,
    licence_text,
    payload_app_dir,
    payload_archive,
    payload_dir,
    shortcut_icon_file,
)
from installer.ops.progress import EXTRACT_END_PCT, EXTRACT_START_PCT
from tests.installer.fakes import RecordingProgress

_ENTRY_TEXT = "bundled"
_ESCAPING_ENTRY = "../escaped.txt"


@pytest.fixture()
def staged_root(staged_payload: Path) -> Path:
    """Name the shared staged payload for the tests in this module."""
    return staged_payload


def _write_archive(path: Path, names: dict[str, str]) -> None:
    """Write a small zip holding the given name to text mapping."""
    with zipfile.ZipFile(path, "w") as bundle:
        for name, text in names.items():
            bundle.writestr(name, text)


def test_the_payload_paths_hang_off_the_installer_package(staged_root: Path) -> None:
    assert payload_dir() == staged_root / PAYLOAD_DIR_NAME
    assert payload_app_dir() == staged_root / PAYLOAD_DIR_NAME / APP_NAME
    assert payload_archive() == staged_root / PAYLOAD_DIR_NAME / PAYLOAD_ARCHIVE_NAME


def test_licence_text_reads_the_bundled_licence(staged_root: Path) -> None:
    (staged_root / PAYLOAD_DIR_NAME / LICENSE_FILE_NAME).write_text(
        "LGPL", encoding="utf-8"
    )

    assert licence_text() == "LGPL"


def test_licence_text_falls_back_when_nothing_is_bundled(staged_root: Path) -> None:
    assert licence_text() == LICENCE_FALLBACK


def test_app_version_reads_the_bundled_version(staged_root: Path) -> None:
    (staged_root / PAYLOAD_DIR_NAME / APP_NAME / VERSION_FILE_NAME).write_text(
        "1.6.0\n", encoding="utf-8"
    )

    assert app_version() == "1.6.0"


def test_app_version_skips_an_empty_version_file(staged_root: Path) -> None:
    (staged_root / PAYLOAD_DIR_NAME / APP_NAME / VERSION_FILE_NAME).write_text(
        "  \n", encoding="utf-8"
    )
    (staged_root / PAYLOAD_DIR_NAME / VERSION_FILE_NAME).write_text(
        "1.6.0", encoding="utf-8"
    )

    assert app_version() == "1.6.0"


def test_app_version_is_empty_when_nothing_is_bundled(staged_root: Path) -> None:
    assert app_version() == ""


def test_icon_file_is_found_when_bundled(staged_root: Path) -> None:
    assets = staged_root / PAYLOAD_DIR_NAME / APP_NAME / "assets"
    assets.mkdir()
    icon = assets / "o7Debrief.png"
    icon.write_bytes(b"png")

    assert icon_file() == icon


def test_icon_file_is_none_when_absent(staged_root: Path) -> None:
    assert icon_file() is None


def test_shortcut_icon_file_is_found_in_an_install(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    icon = assets / "o7debrief.ico"
    icon.write_bytes(b"ico")

    assert shortcut_icon_file(tmp_path) == icon


def test_shortcut_icon_file_is_none_when_absent(tmp_path: Path) -> None:
    assert shortcut_icon_file(tmp_path) is None


def test_extract_archive_writes_every_member(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    _write_archive(archive, {"a.txt": _ENTRY_TEXT, "nested/b.txt": _ENTRY_TEXT})
    target = tmp_path / "install"

    extract_archive(archive, target)

    assert (target / "a.txt").read_text(encoding="utf-8") == _ENTRY_TEXT
    assert (target / "nested" / "b.txt").read_text(encoding="utf-8") == _ENTRY_TEXT


def test_extract_archive_recreates_bundled_directories(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("empty/", "")
    target = tmp_path / "install"

    extract_archive(archive, target)

    assert (target / "empty").is_dir()


def test_extract_archive_replaces_a_previous_install(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    _write_archive(archive, {"a.txt": _ENTRY_TEXT})
    target = tmp_path / "install"
    target.mkdir()
    stale = target / "stale.txt"
    stale.write_text("old", encoding="utf-8")

    extract_archive(archive, target)

    assert not stale.exists()


def test_extract_archive_reports_progress_across_the_phase(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    _write_archive(archive, {"a.txt": _ENTRY_TEXT, "b.txt": _ENTRY_TEXT})
    progress = RecordingProgress()

    extract_archive(archive, tmp_path / "install", progress=progress)

    assert progress.percentages[0] == EXTRACT_START_PCT
    assert progress.percentages[-1] == EXTRACT_END_PCT


def test_extract_archive_reports_the_phase_end_for_an_empty_bundle(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "bundle.zip"
    _write_archive(archive, {"a.txt": ""})
    progress = RecordingProgress()

    extract_archive(archive, tmp_path / "install", progress=progress)

    assert progress.percentages[-1] == EXTRACT_END_PCT


def test_extract_archive_refuses_an_entry_that_escapes_the_target(
    tmp_path: Path,
) -> None:
    """The payload is first party, so this guard is enforced, not assumed."""
    archive = tmp_path / "bundle.zip"
    _write_archive(archive, {_ESCAPING_ENTRY: _ENTRY_TEXT})
    target = tmp_path / "install"

    with pytest.raises(UnsafePayloadEntryError):
        extract_archive(archive, target)

    assert not (tmp_path / "escaped.txt").exists()


def test_extract_archive_reports_a_missing_bundle(tmp_path: Path) -> None:
    with pytest.raises(PayloadError):
        extract_archive(tmp_path / "absent.zip", tmp_path / "install")


def test_deploy_returns_the_installed_executable(staged_root: Path) -> None:
    archive = staged_root / PAYLOAD_DIR_NAME / PAYLOAD_ARCHIVE_NAME
    _write_archive(archive, {EXE_NAME: _ENTRY_TEXT})
    target = staged_root.parent / "install"

    exe_path = deploy(target)

    assert exe_path == target / EXE_NAME
    assert exe_path.is_file()
