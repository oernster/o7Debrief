"""The footer states the running version, injected rather than configured.

The version was once resolved from the taxonomy like every other display
string, with "0" as the default for an absent key. No taxonomy ever carried
the key, so every report ever written stated v0 and nothing failed, because
nothing had pinned the footer version at all. These tests pin it: the version
comes from the caller and a taxonomy cannot state one the build is not.
"""

from __future__ import annotations

import pytest

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

_VERSION = "4.7.2"
# A taxonomy override attempting to state the version itself. It must be
# ignored: a config file is not the source of truth for what is running.
_OVERRIDE_LABELS = (("label.footer.app_version", "9.9.9"),)


def _footer(labels=()):
    """Return the footer view built for an empty debrief."""
    presenter = DebriefPresenter(spec(labels), number_format(), app_version=_VERSION)
    return presenter.present(
        build.debrief(moments=(), activity=ActivityRollup(modes_used=()))
    ).footer


def test_the_footer_reports_the_injected_version() -> None:
    """The version the caller supplied is the version the footer states."""
    assert _footer().app_version == _VERSION


def test_the_footer_version_is_never_a_bare_zero() -> None:
    """The old default is gone, so the regression cannot return quietly."""
    assert _footer().app_version != "0"


def test_a_taxonomy_cannot_state_the_version() -> None:
    """A label override is ignored: VERSION is the only source of truth."""
    assert _footer(_OVERRIDE_LABELS).app_version == _VERSION


def test_a_presenter_cannot_be_built_without_a_version() -> None:
    """The argument is required, so no call site can omit it and read v0."""
    with pytest.raises(TypeError):
        DebriefPresenter(spec(), number_format())


def test_the_version_reaches_the_rendered_context() -> None:
    """The renderers read the footer from the context, so pin it there too."""
    presenter = DebriefPresenter(spec(), number_format(), app_version=_VERSION)
    context = presenter.present(
        build.debrief(moments=(), activity=ActivityRollup(modes_used=()))
    ).to_context()

    assert context["footer"]["app_version"] == _VERSION
