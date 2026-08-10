"""Tests for JsonPreferencesStore: round-trip, defaults and normalisation."""

from __future__ import annotations

from pathlib import Path

from o7debrief.application.dto.preferences import (
    DEFAULT_EXPORT_FORMAT,
    FORMAT_MARKDOWN,
    Preferences,
)
from o7debrief.infrastructure.preferences.json_preferences_store import (
    JsonPreferencesStore,
)


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    store = JsonPreferencesStore(tmp_path)
    store.save(Preferences(export_format=FORMAT_MARKDOWN))

    assert store.load().export_format == FORMAT_MARKDOWN


def test_load_defaults_to_html_when_absent(tmp_path: Path) -> None:
    assert JsonPreferencesStore(tmp_path).load().export_format == DEFAULT_EXPORT_FORMAT


def test_load_defaults_on_corrupt_file(tmp_path: Path) -> None:
    (tmp_path / "preferences.json").write_text("{not valid", encoding="utf-8")

    assert JsonPreferencesStore(tmp_path).load().export_format == DEFAULT_EXPORT_FORMAT


def test_load_normalises_an_unknown_format(tmp_path: Path) -> None:
    (tmp_path / "preferences.json").write_text(
        '{"export_format": "pdf"}', encoding="utf-8"
    )

    assert JsonPreferencesStore(tmp_path).load().export_format == DEFAULT_EXPORT_FORMAT


def test_save_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "state"
    JsonPreferencesStore(target).save(Preferences())

    assert (target / "preferences.json").exists()


def test_save_then_load_roundtrips_the_output_dir(tmp_path: Path) -> None:
    store = JsonPreferencesStore(tmp_path)
    store.save(Preferences(export_format=FORMAT_MARKDOWN, output_dir="D:/Debriefs"))

    loaded = store.load()

    assert loaded.export_format == FORMAT_MARKDOWN
    assert loaded.output_dir == "D:/Debriefs"


def test_load_defaults_output_dir_to_empty_when_absent(tmp_path: Path) -> None:
    assert JsonPreferencesStore(tmp_path).load().output_dir == ""


def test_save_then_load_roundtrips_the_skipped_update_version(tmp_path: Path) -> None:
    store = JsonPreferencesStore(tmp_path)
    store.save(Preferences(skipped_update_version="1.3.0"))

    assert store.load().skipped_update_version == "1.3.0"


def test_load_defaults_skipped_update_version_to_empty(tmp_path: Path) -> None:
    assert JsonPreferencesStore(tmp_path).load().skipped_update_version == ""


def test_load_defaults_a_wrongly_typed_skipped_update_version(tmp_path: Path) -> None:
    (tmp_path / "preferences.json").write_text(
        '{"skipped_update_version": 7}', encoding="utf-8"
    )

    assert JsonPreferencesStore(tmp_path).load().skipped_update_version == ""


def test_load_defaults_every_field_on_a_non_object_payload(tmp_path: Path) -> None:
    (tmp_path / "preferences.json").write_text("[1, 2]", encoding="utf-8")

    loaded = JsonPreferencesStore(tmp_path).load()

    assert loaded == Preferences()
