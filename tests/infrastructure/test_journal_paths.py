"""Tests for journal directory discovery on Windows and Linux.

Discovery is the app's most user-visible failure mode: when it goes wrong the
report says there is no journal on a machine that plainly has one. Until now it
was the least tested module in the tree, because the candidate paths it builds
belong to an operating system the suite is not running on.

They do not have to. Candidate generation is ordinary logic over environment
variables and a home directory, so it is driven here through a hand-written
stand-in for ``os`` (a shape the module already anticipates, see its
``_REAL_OS_MODULE_NAME`` guard) and asserted as paths rather than probed on the
machine. Only the final ``is_dir`` check touches the filesystem, against real
temporary directories.

What is proved: which locations are searched, in what order, under every
combination of the environment variables that steer them. What is not proved is
that a real Proton prefix lives where Steam puts it, which no unit test on any
platform can settle.
"""

from __future__ import annotations

import pytest

from o7debrief.infrastructure.journal import paths, windows_paths

_HOME = "/home/cmdr"
_PROFILE = r"D:\Users\Commander"
_USER = "cmdr"
_COMPAT = "/mnt/games/compatdata/359320"
_WINE = "/home/cmdr/.wine-elite"
# The Steam roots the module walks, relative to the home directory.
_STEAM_ROOT_COUNT = 4
# Each Steam root yields a steamuser candidate and a real-user one.
_CANDIDATES_PER_ROOT = 2


class _StubOs:
    """Stands in for the stdlib ``os``, so no test reads the real machine.

    ``__name__`` deliberately differs from "os": the module uses that to tell a
    stub apart from the genuine article before falling back to ``Path.home()``.
    """

    __name__ = "stub-os"

    def __init__(self, environ: dict[str, str], name: str = "posix") -> None:
        self.environ = environ
        self.name = name


class _HostileEnviron(dict):
    """An environ whose reads raise, which the module defends against."""

    def get(self, key, default=None):
        raise RuntimeError("environ is unavailable")


def _use(monkeypatch, environ: dict[str, str], name: str = "posix") -> None:
    monkeypatch.setattr(paths, "os", _StubOs(environ, name))


def test_home_prefers_the_home_variable(monkeypatch) -> None:
    _use(monkeypatch, {paths._ENV_HOME: _HOME, paths._ENV_USERPROFILE: _PROFILE})

    assert str(paths._get_home_dir()) == str(paths.Path(_HOME))


def test_home_falls_back_to_the_windows_profile(monkeypatch) -> None:
    _use(monkeypatch, {paths._ENV_USERPROFILE: _PROFILE})

    assert str(paths._get_home_dir()) == str(paths.Path(_PROFILE))


def test_a_stubbed_environment_never_probes_the_real_machine(monkeypatch) -> None:
    """With no variables set and a stubbed os, discovery stays deterministic."""
    _use(monkeypatch, {})

    assert str(paths._get_home_dir()) == str(paths.Path(paths._NONEXISTENT))


def test_an_unreadable_environment_is_survived(monkeypatch) -> None:
    """A stubbed environ that raises must not take discovery down with it."""
    monkeypatch.setattr(paths, "os", _StubOs(_HostileEnviron()))

    assert str(paths._get_home_dir()) == str(paths.Path(paths._NONEXISTENT))


def test_the_real_os_reads_the_real_home(monkeypatch) -> None:
    """With the genuine os and no variables set, Path.home() is the answer."""
    monkeypatch.delenv(paths._ENV_HOME, raising=False)
    monkeypatch.delenv(paths._ENV_USERPROFILE, raising=False)

    assert paths._get_home_dir() == paths.Path.home()


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({paths._ENV_USER: _USER}, _USER),
        ({paths._ENV_USERNAME: _USER}, _USER),
        ({}, paths._DEFAULT_USER),
    ],
)
def test_the_user_name_comes_from_the_environment_or_a_default(
    monkeypatch, environ, expected
) -> None:
    _use(monkeypatch, environ)

    assert paths._current_user() == expected


def test_an_explicit_compat_path_is_searched_first(monkeypatch) -> None:
    """STEAM_COMPAT_DATA_PATH names the prefix outright, so it leads."""
    _use(monkeypatch, {paths._ENV_HOME: _HOME, paths._ENV_STEAM_COMPAT: _COMPAT})

    candidates = list(paths._proton_compat_candidates(_USER))

    assert str(candidates[0]).startswith(str(paths.Path(_COMPAT)))
    assert "steamuser" in str(candidates[0])
    assert _USER in str(candidates[1])


def test_every_steam_root_is_searched_for_both_user_names(monkeypatch) -> None:
    """Four roots, each tried as steamuser and as the real user."""
    _use(monkeypatch, {paths._ENV_HOME: _HOME})

    candidates = [str(path) for path in paths._proton_compat_candidates(_USER)]

    assert len(candidates) == _STEAM_ROOT_COUNT * _CANDIDATES_PER_ROOT
    assert any(".steam" in path for path in candidates)
    assert any("com.valvesoftware.Steam" in path for path in candidates)
    assert all(paths._STEAM_APP_ID_ELITE_DANGEROUS in path for path in candidates)


def test_the_flatpak_steam_location_is_covered(monkeypatch) -> None:
    """Steam installed as a Flatpak keeps its prefix under ~/.var/app."""
    _use(monkeypatch, {paths._ENV_HOME: _HOME})

    candidates = [str(path) for path in paths._proton_compat_candidates(_USER)]

    assert any(
        ".var" in path and "com.valvesoftware.Steam" in path for path in candidates
    )


def test_an_explicit_wineprefix_precedes_the_default(monkeypatch) -> None:
    _use(monkeypatch, {paths._ENV_HOME: _HOME, paths._ENV_WINEPREFIX: _WINE})

    candidates = [str(path) for path in paths._wine_candidates(_USER)]

    assert candidates[0].startswith(str(paths.Path(_WINE)))
    assert any(".wine" in path for path in candidates[_CANDIDATES_PER_ROOT:])


def test_the_default_wine_prefix_is_searched_without_the_variable(
    monkeypatch,
) -> None:
    _use(monkeypatch, {paths._ENV_HOME: _HOME})

    candidates = [str(path) for path in paths._wine_candidates(_USER)]

    assert len(candidates) == _CANDIDATES_PER_ROOT
    assert all(".wine" in path for path in candidates)


def test_linux_candidates_are_proton_then_wine(monkeypatch) -> None:
    """Order matters: the Steam route is the common one and comes first."""
    _use(monkeypatch, {paths._ENV_HOME: _HOME})

    candidates = [str(path) for path in paths._iter_linux_journal_candidates()]

    assert "compatdata" in candidates[0]
    assert ".wine" in candidates[-1]


def _journal_dir(root):
    """Create a real Saved Games journal directory under root and return it."""
    journal = root / paths._JOURNAL_SUBPATH
    journal.mkdir(parents=True)
    return journal


def test_windows_discovery_uses_the_saved_games_folder(monkeypatch, tmp_path) -> None:
    saved_games = tmp_path / "Saved Games"
    journal = saved_games / paths._FRONTIER_DIR / paths._ELITE_DIR
    journal.mkdir(parents=True)
    _use(monkeypatch, {}, name=paths._OS_NT)
    monkeypatch.setattr(windows_paths, "get_saved_games_path", lambda: saved_games)

    assert paths.find_journal_directory() == journal


def test_windows_discovery_without_a_saved_games_folder_finds_nothing(
    monkeypatch,
) -> None:
    _use(monkeypatch, {}, name=paths._OS_NT)
    monkeypatch.setattr(windows_paths, "get_saved_games_path", lambda: None)

    assert paths.find_journal_directory() is None


def test_windows_discovery_requires_the_elite_subfolder(monkeypatch, tmp_path) -> None:
    """A Saved Games folder without Elite in it is not a journal directory."""
    _use(monkeypatch, {}, name=paths._OS_NT)
    monkeypatch.setattr(windows_paths, "get_saved_games_path", lambda: tmp_path)

    assert paths.find_journal_directory() is None


def test_linux_discovery_returns_the_first_existing_candidate(
    monkeypatch, tmp_path
) -> None:
    """The Wine default is reached only when the Steam roots are absent."""
    home = tmp_path / "home"
    journal = _journal_dir(home / ".wine" / "drive_c" / "users" / _USER)
    _use(monkeypatch, {paths._ENV_HOME: str(home), paths._ENV_USER: _USER})

    assert paths.find_journal_directory() == journal


def test_linux_discovery_finds_nothing_when_no_prefix_exists(
    monkeypatch, tmp_path
) -> None:
    _use(monkeypatch, {paths._ENV_HOME: str(tmp_path), paths._ENV_USER: _USER})

    assert paths.find_journal_directory() is None


def test_the_directory_is_returned_when_discovery_succeeds(
    monkeypatch, tmp_path
) -> None:
    home = tmp_path / "home"
    journal = _journal_dir(home / ".wine" / "drive_c" / "users" / _USER)
    _use(monkeypatch, {paths._ENV_HOME: str(home), paths._ENV_USER: _USER})

    assert paths.get_journal_directory() == journal


def test_windows_failure_says_so_without_listing_linux_paths(monkeypatch) -> None:
    """The Windows message names the folder rather than a list of prefixes."""
    _use(monkeypatch, {}, name=paths._OS_NT)
    monkeypatch.setattr(windows_paths, "get_saved_games_path", lambda: None)

    with pytest.raises(paths.JournalDirectoryNotFoundError) as raised:
        paths.get_journal_directory()

    assert "Saved Games" in str(raised.value)
    assert "compatdata" not in str(raised.value)


def test_linux_failure_lists_every_location_it_tried(monkeypatch, tmp_path) -> None:
    """The message is the diagnostic, so it carries the whole search."""
    _use(monkeypatch, {paths._ENV_HOME: str(tmp_path), paths._ENV_USER: _USER})

    with pytest.raises(paths.JournalDirectoryNotFoundError) as raised:
        paths.get_journal_directory()

    message = str(raised.value)
    assert "compatdata" in message
    assert ".wine" in message
    # Every candidate is named, so the reader can see what was searched.
    listed = message.split("Tried the following locations:\n")[1].splitlines()
    expected = [str(path) for path in paths._iter_linux_journal_candidates()]
    assert listed == expected
