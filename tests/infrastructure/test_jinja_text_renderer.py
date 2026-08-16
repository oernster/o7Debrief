"""Tests for JinjaTextTemplateRenderer, the taxonomy row-wording renderer.

The behaviour that matters is not that it renders, it is what it refuses to
render. A row must never state a half-fact: a template naming a field the
journal payload does not carry yields nothing at all, so the caller shows the
moment's label rather than a sentence with a hole in it.

The payloads here are shaped exactly as the real journal writes them, including
the raw/manufactured asymmetry at the material trader (a raw material states
only its internal name; a manufactured one also states a readable one).
"""

from __future__ import annotations

from o7debrief.infrastructure.render.jinja_text_renderer import (
    JinjaTextTemplateRenderer,
)
from o7debrief.infrastructure.render.journal_names import (
    HumaniseVocabulary,
    NameHumaniser,
)

# The shipped wording for the two rules this change exists to fix.
_CRAFT_TEMPLATE = (
    "Applied {{ BlueprintName }} grade {{ Level }} to {{ Module }} at {{ Engineer }}."
)
_TRADE_TEMPLATE = (
    "Traded {{ Paid.Quantity }} "
    "{{ Paid.Material_Localised | default(Paid.Material, true) }} for "
    "{{ Received.Quantity }} "
    "{{ Received.Material_Localised | default(Received.Material, true) }} "
    "at the {{ TraderType }} trader."
)


def _renderer() -> JinjaTextTemplateRenderer:
    return JinjaTextTemplateRenderer()


def test_renders_an_engineering_roll_in_full() -> None:
    payload = {
        "BlueprintName": "Weapon_Overcharged",
        "Level": 5,
        "Module": "hpt_multicannon_gimbal_medium",
        "Engineer": "Tod 'The Blaster' McQuinn",
    }
    assert _renderer().render(_CRAFT_TEMPLATE, payload) == (
        "Applied Weapon_Overcharged grade 5 to hpt_multicannon_gimbal_medium "
        "at Tod 'The Blaster' McQuinn."
    )


def test_renders_a_raw_material_trade_from_internal_names() -> None:
    # A raw material carries no localised name, so the default filter falls
    # back to the internal one rather than rendering a blank.
    payload = {
        "TraderType": "raw",
        "Paid": {"Material": "ruthenium", "Category": "Raw", "Quantity": 90},
        "Received": {"Material": "technetium", "Category": "Raw", "Quantity": 15},
    }
    assert _renderer().render(_TRADE_TEMPLATE, payload) == (
        "Traded 90 ruthenium for 15 technetium at the raw trader."
    )


def test_renders_a_manufactured_trade_from_localised_names() -> None:
    payload = {
        "TraderType": "manufactured",
        "Paid": {
            "Material": "militarysupercapacitors",
            "Material_Localised": "Military Supercapacitors",
            "Quantity": 7,
        },
        "Received": {
            "Material": "electrochemicalarrays",
            "Material_Localised": "Electrochemical Arrays",
            "Quantity": 63,
        },
    }
    assert _renderer().render(_TRADE_TEMPLATE, payload) == (
        "Traded 7 Military Supercapacitors for 63 Electrochemical Arrays "
        "at the manufactured trader."
    )


def test_a_field_the_payload_never_carried_renders_nothing() -> None:
    """The defining refusal: no field, no sentence.

    Jinja's default Undefined would render this as "Applied Weapon_Overcharged
    grade 5 to  at ." which reads to a commander as a fact about a module with
    no name. Strict undefined turns it into no text at all instead.
    """
    payload = {"BlueprintName": "Weapon_Overcharged", "Level": 5}
    assert _renderer().render(_CRAFT_TEMPLATE, payload) is None


def test_an_empty_payload_renders_nothing() -> None:
    assert _renderer().render(_CRAFT_TEMPLATE, {}) is None


def test_a_template_that_will_not_compile_renders_nothing() -> None:
    assert _renderer().render("Applied {{ unclosed ", {"unclosed": "x"}) is None


def test_a_template_with_no_placeholders_renders_verbatim() -> None:
    assert _renderer().render("Deployed the SRV.", {}) == "Deployed the SRV."


def test_output_is_not_escaped_for_the_exporters_to_escape() -> None:
    """Escaping here would double-escape: the HTML exporter autoescapes already."""
    rendered = _renderer().render("At {{ Station }}.", {"Station": "Jones & Sons"})
    assert rendered == "At Jones & Sons."


def test_compiled_templates_are_reused_across_renders() -> None:
    """A report of hundreds of rows compiles a handful of templates, not hundreds."""
    renderer = _renderer()
    first = renderer.render("Grade {{ Level }}.", {"Level": 1})
    second = renderer.render("Grade {{ Level }}.", {"Level": 5})
    assert (first, second) == ("Grade 1.", "Grade 5.")
    assert len(renderer._compiled) == 1


def test_a_broken_template_is_diagnosed_once_and_cached() -> None:
    renderer = _renderer()
    assert renderer.render("{{ broken ", {}) is None
    assert renderer.render("{{ broken ", {}) is None
    assert renderer._compiled == {"{{ broken ": None}


def test_a_humaniser_supplies_the_token_decoding_filters() -> None:
    """With a humaniser wired in, a template can state English, not tokens."""
    humaniser = NameHumaniser(
        HumaniseVocabulary(
            drop_prefixes=("int",),
            ratings=("E", "D", "C", "B", "A"),
            words={"sensors": "Sensors"},
        )
    )
    renderer = JinjaTextTemplateRenderer(humaniser)

    rendered = renderer.render(
        "Fitted {{ Module | module }} ({{ Blueprint | blueprint }}, "
        "{{ Material | material }}).",
        {
            "Module": "int_sensors_size5_class2",
            "Blueprint": "Sensor_LongRange",
            "Material": "Military Supercapacitors",
        },
    )

    assert rendered == (
        "Fitted 5D Sensors (Long Range Sensor, Military Supercapacitors)."
    )


def test_without_a_humaniser_those_filters_do_not_exist() -> None:
    """An undefined filter yields nothing, so the row falls back to its label."""
    assert (
        _renderer().render("{{ Module | module }}", {"Module": "int_sensors"}) is None
    )


def test_a_credits_filter_writes_a_price_the_way_the_report_does() -> None:
    """A row stating a price must group it as the section totals group theirs.

    Without the filter a template printed the payload's raw digits, so one
    document wrote "5374463 Cr" in a row and "5,374,463 Cr" in the total above
    it for the same money.
    """
    renderer = JinjaTextTemplateRenderer(credits_filter=lambda v: f"{v:,} Cr")

    rendered = renderer.render("Paid {{ Price | credits }}.", {"Price": 5374463})

    assert rendered == "Paid 5,374,463 Cr."


def test_without_a_credits_filter_that_filter_does_not_exist() -> None:
    """The row falls back to its label rather than printing unbroken digits."""
    assert _renderer().render("{{ Price | credits }}", {"Price": 1}) is None
