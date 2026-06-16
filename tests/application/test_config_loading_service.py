"""Tests for the ConfigLoadingService schema-version guard."""

from __future__ import annotations

import pytest

from tests.application.fakes import FakeConfigProvider, spec

from o7debrief.application.errors import ConfigSchemaMismatchError
from o7debrief.application.services.config_loading_service import (
    ConfigLoadingService,
)


def test_load_spec_returns_spec_when_versions_match() -> None:
    the_spec = spec()
    provider = FakeConfigProvider(the_spec, expected_version=the_spec.schema_version)
    service = ConfigLoadingService(provider)

    loaded = service.load_spec()

    assert loaded is the_spec
    assert provider.load_calls == 1


def test_load_spec_raises_on_schema_mismatch() -> None:
    the_spec = spec()
    provider = FakeConfigProvider(the_spec, expected_version="999")
    service = ConfigLoadingService(provider)

    with pytest.raises(ConfigSchemaMismatchError) as caught:
        service.load_spec()

    assert caught.value.expected == "999"
    assert caught.value.actual == the_spec.schema_version
