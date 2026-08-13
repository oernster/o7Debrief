"""Tests for timeline rows worded from the taxonomy's text templates.

This is the repair of the report's largest defect. Every [[moment]] in the
taxonomy declared a ``text`` template; nothing carried it as far as the
presenter, so every row fell back to its kind label. A session of 261
engineering rolls printed "Engineer Craft" 261 times and named no blueprint,
grade, module or engineer.

The tests cover both directions. A moment carrying a template it can satisfy is
worded from it. A moment that cannot (no renderer, no template, a field the
payload lacks, a template that renders to nothing) falls back to its label,
because a partly rendered sentence would read as a fact.

The renderer is a hand-written fake, in keeping with the suite's no-mock-library
rule. The real Jinja adapter is proven separately in the infrastructure tests.
"""

from __future__ import annotations

from collections.abc import Mapping

from o7debrief.application.services.debrief_presenter import DebriefPresenter
from o7debrief.domain.model.rollups import ActivityRollup
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from tests.application import domain_builders as build
from tests.application.fakes import number_format, spec

_CRAFT_TEMPLATE = "Applied {{ BlueprintName }} grade {{ Level }} to {{ Module }}."
_CRAFT_DETAIL = (
    ("BlueprintName", "ShieldBooster_HeavyDuty"),
    ("Level", 5),
    ("Module", "hpt_shieldbooster_size0_class3"),
)


class FormatRenderer:
    """A renderer that substitutes ``{{ Name }}`` placeholders from the payload.

    Deliberately simple and strict in the same way the real adapter is: a
    placeholder the payload cannot satisfy yields None rather than a gap. It
    records the calls it was given so a test can prove the payload reaching it
    is the moment's own detail.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def render(self, template: str, values: Mapping[str, object]) -> str | None:
        self.calls.append((template, dict(values)))
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace("{{ " + key + " }}", str(value))
        if "{{" in rendered:
            return None
        return rendered


class NullRenderer:
    """A renderer that can never word a row, however well-formed the template."""

    def render(self, template: str, values: Mapping[str, object]) -> str | None:
        return None


class BlankRenderer:
    """A renderer that returns whitespace, which is no more use than nothing."""

    def render(self, template: str, values: Mapping[str, object]) -> str | None:
        return "   "


def _row_text(moment, renderer=None) -> str:
    debrief = build.debrief(moments=(moment,), activity=ActivityRollup(modes_used=()))
    presenter = DebriefPresenter(spec(), number_format(), renderer, app_version="1.2.3")
    return presenter.present(debrief).to_context()["timeline"][0]["text"]


def _craft(template: str = _CRAFT_TEMPLATE, detail=_CRAFT_DETAIL):
    return build.moment(
        MomentKind.ENGINEER_CRAFT,
        ActivityDomain.ENGINEERING,
        1,
        detail=detail,
        text_template=template,
    )


def test_a_row_states_what_happened_rather_than_its_kind() -> None:
    assert _row_text(_craft(), FormatRenderer()) == (
        "Applied ShieldBooster_HeavyDuty grade 5 to hpt_shieldbooster_size0_class3."
    )


def test_the_renderer_is_given_the_moments_own_payload() -> None:
    renderer = FormatRenderer()
    _row_text(_craft(), renderer)
    template, values = renderer.calls[0]
    assert template == _CRAFT_TEMPLATE
    assert values["BlueprintName"] == "ShieldBooster_HeavyDuty"


def test_without_a_renderer_the_row_falls_back_to_its_label() -> None:
    # This is the behaviour every report had before the templates were read.
    assert _row_text(_craft()) == MomentKind.ENGINEER_CRAFT.name


def test_a_moment_with_no_template_falls_back_to_its_label() -> None:
    assert _row_text(_craft(template=""), FormatRenderer()) == (
        MomentKind.ENGINEER_CRAFT.name
    )


def test_a_payload_missing_a_named_field_falls_back_to_its_label() -> None:
    # Rather than "Applied ShieldBooster_HeavyDuty grade 5 to ."
    partial = (("BlueprintName", "ShieldBooster_HeavyDuty"), ("Level", 5))
    assert _row_text(_craft(detail=partial), FormatRenderer()) == (
        MomentKind.ENGINEER_CRAFT.name
    )


def test_a_renderer_that_yields_nothing_falls_back_to_its_label() -> None:
    assert _row_text(_craft(), NullRenderer()) == MomentKind.ENGINEER_CRAFT.name


def test_a_row_rendering_to_whitespace_falls_back_to_its_label() -> None:
    assert _row_text(_craft(), BlankRenderer()) == MomentKind.ENGINEER_CRAFT.name


def test_surrounding_whitespace_is_trimmed_from_a_rendered_row() -> None:
    moment = _craft(template="  Applied {{ Level }}.  ")
    assert _row_text(moment, FormatRenderer()) == "Applied 5."


def test_a_material_trade_row_names_both_sides() -> None:
    moment = build.moment(
        MomentKind.MATERIAL_TRADE,
        ActivityDomain.TRADE,
        1,
        detail=(("PaidText", "90 ruthenium"), ("GotText", "15 technetium")),
        text_template="Traded {{ PaidText }} for {{ GotText }}.",
    )
    assert _row_text(moment, FormatRenderer()) == (
        "Traded 90 ruthenium for 15 technetium."
    )


def test_a_death_row_is_still_assembled_in_code_not_from_a_template() -> None:
    """The four enriched kinds keep their conditional wording.

    A death names its cause, victim and rebuy through rules a flat template
    cannot express, so it must not be diverted through the renderer.
    """
    moment = build.moment(
        MomentKind.DEATH,
        ActivityDomain.COMBAT,
        1,
        detail=(("KillerName", "Kaeso Bellum"),),
        text_template="this template must not be used",
    )
    assert _row_text(moment, FormatRenderer()) == "Killed by Kaeso Bellum"
