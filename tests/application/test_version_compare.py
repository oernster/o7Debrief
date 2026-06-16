"""Tests for the pure semantic-version comparison used by the update check."""

from __future__ import annotations

from o7debrief.application.services.version_compare import is_newer


def test_a_higher_version_is_newer() -> None:
    assert is_newer("1.3.0", "1.2.0") is True


def test_an_equal_version_is_not_newer() -> None:
    assert is_newer("1.2.0", "1.2.0") is False


def test_a_lower_version_is_not_newer() -> None:
    assert is_newer("1.1.0", "1.2.0") is False


def test_a_leading_v_prefix_is_ignored() -> None:
    assert is_newer("v1.2.1", "1.2.0") is True
    assert is_newer("V1.2.0", "v1.2.0") is False


def test_a_malformed_latest_is_never_newer() -> None:
    assert is_newer("not-a-version", "1.2.0") is False


def test_a_malformed_current_is_never_newer() -> None:
    assert is_newer("1.2.0", "x.y.z") is False
