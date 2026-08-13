"""Tests for LinuxAutostart, the XDG autostart entry adapter.

The adapter is the Linux half of the "start when I sign in" setting and it
matters more here than on Windows: o7 Debrief's Linux proposition is that it is
already watching when the Commander quits the game, so an entry that silently
fails to be written costs the whole feature.

Every test writes into a temporary directory, so the developer's own session
configuration is never touched.
"""

from __future__ import annotations

from pathlib import Path

from o7debrief.infrastructure.autostart.linux_autostart import LinuxAutostart

_COMMAND = "flatpak run uk.co.oernster.o7Debrief"


def _autostart(tmp_path: Path) -> LinuxAutostart:
    return LinuxAutostart(autostart_dir=tmp_path / "autostart")


def test_nothing_is_enabled_before_anything_is_written(tmp_path: Path) -> None:
    assert _autostart(tmp_path).is_enabled() is False


def test_enabling_writes_an_entry_that_runs_the_command(tmp_path: Path) -> None:
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)

    text = autostart.entry_path.read_text(encoding="utf-8")
    assert f"Exec={_COMMAND}" in text
    assert autostart.is_enabled() is True


def test_the_entry_is_a_desktop_application_the_session_will_launch(
    tmp_path: Path,
) -> None:
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)

    text = autostart.entry_path.read_text(encoding="utf-8")
    assert text.startswith("[Desktop Entry]")
    assert "Type=Application" in text
    # Written explicitly: GNOME honours a false value in preference to the file
    # merely being present, so an entry from an earlier version could otherwise
    # exist and never run.
    assert "X-GNOME-Autostart-enabled=true" in text


def test_the_autostart_directory_is_created_when_absent(tmp_path: Path) -> None:
    # The ordinary case on a desktop where nothing has registered one before.
    autostart = _autostart(tmp_path)
    assert not autostart.entry_path.parent.exists()

    autostart.enable(_COMMAND)

    assert autostart.entry_path.is_file()


def test_enabling_twice_rewrites_rather_than_duplicating(tmp_path: Path) -> None:
    autostart = _autostart(tmp_path)
    autostart.enable("first")
    autostart.enable(_COMMAND)

    text = autostart.entry_path.read_text(encoding="utf-8")
    assert "first" not in text
    assert f"Exec={_COMMAND}" in text


def test_disabling_removes_the_entry_entirely(tmp_path: Path) -> None:
    # Removal rather than a Hidden marker, so nothing is left for a later
    # version to misread.
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)

    autostart.disable()

    assert autostart.entry_path.exists() is False
    assert autostart.is_enabled() is False


def test_disabling_when_nothing_is_enabled_is_harmless(tmp_path: Path) -> None:
    _autostart(tmp_path).disable()


def test_an_entry_marked_hidden_reads_as_disabled(tmp_path: Path) -> None:
    """The checkbox must show what the desktop will actually act on."""
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)
    path = autostart.entry_path
    path.write_text(
        path.read_text(encoding="utf-8") + "Hidden=true\n", encoding="utf-8"
    )

    assert autostart.is_enabled() is False


def test_an_entry_gnome_has_switched_off_reads_as_disabled(tmp_path: Path) -> None:
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)
    autostart.entry_path.write_text(
        "[Desktop Entry]\nX-GNOME-Autostart-enabled=false\n", encoding="utf-8"
    )

    assert autostart.is_enabled() is False


def test_a_directory_where_the_entry_should_be_reads_as_disabled(
    tmp_path: Path,
) -> None:
    autostart = _autostart(tmp_path)
    autostart.entry_path.parent.mkdir(parents=True, exist_ok=True)
    autostart.entry_path.mkdir()

    assert autostart.is_enabled() is False


def test_an_entry_that_cannot_be_read_reads_as_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    """A permission error must not raise out into the Settings dialog.

    The entry exists and is a file, so the read is genuinely attempted and
    genuinely fails, which is the case a directory in its place does not reach:
    that one is turned away by the is_file check before any read happens.
    """
    autostart = _autostart(tmp_path)
    autostart.enable(_COMMAND)

    def refuse(*_args, **_kwargs) -> str:
        raise PermissionError("entry is not readable by this user")

    monkeypatch.setattr(Path, "read_text", refuse)

    assert autostart.is_enabled() is False


def test_the_default_directory_follows_xdg_config_home(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/cfg")

    assert LinuxAutostart().entry_path == Path(
        "/tmp/cfg/autostart/uk.co.oernster.o7Debrief.desktop"
    )


def test_the_default_directory_falls_back_to_dot_config(monkeypatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/cmdr")))

    assert LinuxAutostart().entry_path == Path(
        "/home/cmdr/.config/autostart/uk.co.oernster.o7Debrief.desktop"
    )
