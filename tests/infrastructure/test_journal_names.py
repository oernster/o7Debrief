"""Tests for NameHumaniser, which decodes journal tokens into report English.

The journal states no readable name for a module, so the English is decoded
from the token. That makes two properties matter more than any individual
translation.

First, nothing is invented. Every word out is a transliterated part of the
token, a substitution the taxonomy names or a rating letter from the taxonomy's
own table.

Second, nothing is lost. A part the vocabulary does not cover is title-cased and
kept, so an unrecognised module reads as itself and a vocabulary gap is visible
in the report rather than silently swallowed. The tokens used here are real ones
taken from a live journal.
"""

from __future__ import annotations

from o7debrief.infrastructure.render.journal_names import (
    HumaniseVocabulary,
    NameHumaniser,
)

_VOCABULARY = HumaniseVocabulary(
    drop_prefixes=("int", "hpt"),
    ratings=("E", "D", "C", "B", "A"),
    words={
        "multicannon": "Multi-Cannon",
        "powerplant": "Power Plant",
        "hyperdrive": "Frame Shift Drive",
        "shieldgenerator": "Shield Generator",
        "overcharge": "Overcharged",
        "ruthenium": "Ruthenium",
    },
    mounts={"gimbal": "Gimballed", "turret": "Turreted"},
    sizes={"small": "Small", "medium": "Medium", "large": "Large"},
)


def _humaniser() -> NameHumaniser:
    return NameHumaniser(_VOCABULARY)


def test_size_and_class_become_the_games_own_rating() -> None:
    # The journal says size5_class2; the game and every Commander say 5D.
    assert _humaniser().module("int_sensors_size5_class2") == "5D Sensors"


def test_top_rated_module_reads_as_a() -> None:
    assert _humaniser().module("int_powerplant_size7_class5") == "7A Power Plant"


def test_mount_and_size_move_in_front_of_the_module() -> None:
    assert (
        _humaniser().module("hpt_multicannon_gimbal_medium")
        == "Medium Gimballed Multi-Cannon"
    )


def test_a_graded_module_keeps_its_grade() -> None:
    assert _humaniser().module("mandalay_armour_grade1") == "Mandalay Armour (grade 1)"


def test_extra_descriptors_are_kept_in_the_order_stated() -> None:
    assert (
        _humaniser().module("int_hyperdrive_overcharge_size4_class5")
        == "4A Frame Shift Drive Overcharged"
    )


def test_an_unknown_part_is_kept_title_cased_rather_than_dropped() -> None:
    """A vocabulary gap must be visible, never silent.

    Nothing in the taxonomy covers "slugshot" here, so it reads as Slugshot: odd
    but recognisable and obviously worth a vocabulary entry. Dropping it would
    leave a report naming a weapon that is not the one that was engineered.
    """
    assert _humaniser().module("hpt_slugshot_turret_medium") == (
        "Medium Turreted Slugshot"
    )


def test_a_class_outside_the_ratings_table_states_size_and_class_outright() -> None:
    """No letter is invented; the size that was stated is not thrown away either.

    Falling back to the bare name would hide the gap by discarding real data,
    which is the failure this whole module exists to avoid.
    """
    assert _humaniser().module("int_sensors_size5_class9") == (
        "Sensors (size 5, class 9)"
    )


def test_only_a_leading_prefix_is_dropped() -> None:
    # "int" later in a token is part of the module, not a placement marker.
    assert _humaniser().module("hpt_int_thing_size1_class1") == "1E Int Thing"


def test_a_token_with_no_separator_is_title_cased() -> None:
    assert _humaniser().module("sensors") == "Sensors"


def test_a_missing_module_yields_nothing_rather_than_a_placeholder() -> None:
    assert _humaniser().module(None) == ""
    assert _humaniser().module("") == ""


def test_a_blueprint_reads_effect_first_as_english_wants() -> None:
    assert _humaniser().blueprint("Sensor_LongRange") == "Long Range Sensor"


def test_a_blueprint_acronym_survives_the_split() -> None:
    # Naive PascalCase splitting would render this "F S D".
    assert _humaniser().blueprint("FSD_LongRange") == "Long Range FSD"


def test_a_multi_word_blueprint_effect_keeps_every_word() -> None:
    assert (
        _humaniser().blueprint("PowerDistributor_HighFrequency")
        == "High Frequency Power Distributor"
    )


def test_a_blueprint_with_no_effect_is_just_its_category() -> None:
    assert _humaniser().blueprint("Armour") == "Armour"


def test_a_missing_blueprint_yields_nothing() -> None:
    assert _humaniser().blueprint(None) == ""


def test_a_raw_material_is_title_cased() -> None:
    assert _humaniser().material("ruthenium") == "Ruthenium"


def test_a_material_the_vocabulary_does_not_list_is_still_readable() -> None:
    assert _humaniser().material("technetium") == "Technetium"


def test_a_name_the_journal_already_localised_is_left_exactly_as_stated() -> None:
    """The game's own wording is never rewritten, capitalisation included."""
    assert (
        _humaniser().material("Military Supercapacitors") == "Military Supercapacitors"
    )


def test_a_missing_material_yields_nothing() -> None:
    assert _humaniser().material(None) == ""


def test_an_empty_vocabulary_still_produces_readable_english() -> None:
    """A taxonomy with no [humanise] table degrades to title-casing, not to junk."""
    bare = NameHumaniser(HumaniseVocabulary())
    # No ratings table means no rating letter, so the size and class are stated
    # rather than folded away; the "int" marker likewise has no entry to drop it.
    assert bare.module("int_sensors_size5_class2") == "Int Sensors (size 5, class 2)"
    assert bare.blueprint("Sensor_LongRange") == "Long Range Sensor"


def test_a_dropped_category_leaves_only_the_effect() -> None:
    """The game's catch-all bucket describes its filing, not the Commander's work."""
    vocabulary = HumaniseVocabulary(drop_categories=("Misc",))

    assert NameHumaniser(vocabulary).blueprint("Misc_LightWeight") == "Light Weight"


def test_a_blueprint_of_one_part_states_that_part() -> None:
    """With no effect to lead with, the category stands on its own."""
    assert _humaniser().blueprint("Sensor") == "Sensor"


def test_a_numbered_part_the_vocabulary_does_not_name_is_kept() -> None:
    """A gap in the vocabulary shows up in the report rather than losing a word."""
    decoded = _humaniser().module("hpt_railgun_burst4_size2_class3")

    assert "Burst4" in decoded
