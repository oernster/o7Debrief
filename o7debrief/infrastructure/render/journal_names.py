"""Turn the journal's internal tokens into English for the report.

The Elite Dangerous journal names a fitted module as ``int_sensors_size5_class2``
and a blueprint as ``Sensor_LongRange``. Those are programming identifiers;
printing them in a Commander's report is the same defect as printing the name of
a moment's kind, because the reader is shown the shape of the data rather than
the thing it describes.

There is nowhere to look the readable name up. The journal states one for some
values (a material's ``Name_Localised``, an experimental effect's
``ExperimentalEffect_Localised``) and never for a module: across 182 fitted
modules in a real journal, not one carried an ``Item_Localised``. So the English
has to be decoded from the token itself.

That decode is deliberately structural; the honesty rule shapes it. Every word
out is one of three things: a part of the token transliterated, a named
substitution the taxonomy records or a rating letter from the taxonomy's own
table. A part with no entry passes through title-cased rather than being dropped
or guessed at, so an unrecognised module still reads as itself and a vocabulary
gap is visible in the report rather than silent. Nothing is invented and nothing
is discarded.

The vocabulary lives in the taxonomy for the same reason the event mapping does:
it is data about the game, so it changes when the game does; correcting a word
is then a config edit that needs no release of the logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["HumaniseVocabulary", "NameHumaniser"]

# The token separator the journal uses inside an internal name.
_PART_SEPARATOR = "_"
_SPACE = " "
_EMPTY = ""

# Splits a PascalCase blueprint part into words while keeping an acronym whole,
# so "LongRange" becomes Long + Range and "FSD" stays FSD rather than F + S + D.
_PASCAL_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+")

# A token part that carries a number, for example "size5", "class2", "grade1".
_NUMBERED_PART = re.compile(r"^([a-z]+)(\d+)$")

# Rating tables are indexed from class 1, so class 1 is the first entry.
_FIRST_CLASS = 1


@dataclass(frozen=True, slots=True)
class HumaniseVocabulary:
    """The taxonomy's vocabulary for decoding journal tokens into English.

    Every field is reference data read from the taxonomy, never a literal in
    code. ``ratings`` maps a module's class number to its rating letter, ordered
    from class 1 upwards, which is how the game states a module as "5A" rather
    than "size 5 class 5".
    """

    drop_prefixes: tuple[str, ...] = ()
    # Trailing token parts that name the token rather than the thing. The
    # outfitting events state a module as "$int_fuelscoop_size4_class5_name;"
    # where engineering states the same module bare, so a decode that handled
    # only the bare form printed "$Int Fuel Scoop Name;" at the reader.
    drop_suffixes: tuple[str, ...] = ()
    # The characters that wrap a localisation key, stripped before the token is
    # split. Data, not code, for the same reason every other word here is.
    token_open: str = ""
    token_close: str = ""
    drop_categories: tuple[str, ...] = ()
    ratings: tuple[str, ...] = ()
    words: dict[str, str] = field(default_factory=dict)
    mounts: dict[str, str] = field(default_factory=dict)
    sizes: dict[str, str] = field(default_factory=dict)
    size_token: str = "size"
    class_token: str = "class"
    grade_token: str = "grade"
    rated_format: str = "{size}{rating} {name}"
    graded_format: str = "{name} (grade {grade})"
    unrated_format: str = "{name} (size {size}, class {class_number})"


def _pascal_words(part: str) -> list[str]:
    """Split one PascalCase token part into its words, acronyms kept whole."""
    return _PASCAL_WORDS.findall(part)


def _numbered(part: str) -> tuple[str, int] | None:
    """Return the (name, number) of a part like ``size5``, else None."""
    match = _NUMBERED_PART.match(part)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


class NameHumaniser:
    """Decodes journal tokens into report English using a taxonomy vocabulary.

    Each method returns a readable string for any input, including one the
    vocabulary does not cover: an unknown part is title-cased and kept. A value
    that is already readable (a localised material name the journal supplied) is
    returned untouched, so this never rewrites what the game already said.
    """

    def __init__(self, vocabulary: HumaniseVocabulary) -> None:
        self._vocabulary = vocabulary

    def _word(self, part: str) -> str:
        """Return the vocabulary's word for a part, else the part title-cased."""
        return self._vocabulary.words.get(part, part.title())

    def _rating(self, class_number: int) -> str | None:
        """Return the rating letter for a module class, else None if unlisted."""
        index = class_number - _FIRST_CLASS
        ratings = self._vocabulary.ratings
        if 0 <= index < len(ratings):
            return ratings[index]
        return None

    def _strip_prefix(self, parts: list[str]) -> list[str]:
        """Drop a leading internal/hardpoint marker, keeping everything else.

        Only a leading part is dropped, never one further in; the taxonomy must
        name it as well, so a module whose own name begins with such a word
        cannot lose it.
        """
        if parts and parts[0] in self._vocabulary.drop_prefixes:
            return parts[1:]
        return parts

    def _strip_suffix(self, parts: list[str]) -> list[str]:
        """Drop a trailing localisation-key marker, keeping everything else.

        Only a trailing part is dropped and only one the taxonomy names, so a
        module whose own name ends in such a word cannot lose it.
        """
        if len(parts) > 1 and parts[-1] in self._vocabulary.drop_suffixes:
            return parts[:-1]
        return parts

    def _unwrap(self, text: str) -> str:
        """Return a localisation key with its wrapping characters removed.

        The outfitting events state an item as "$<token>_name;" while the
        engineering events state the same token bare. Unwrapping here means the
        decode below sees one form, whichever event the value came from.
        """
        vocabulary = self._vocabulary
        if vocabulary.token_open and text.startswith(vocabulary.token_open):
            text = text[len(vocabulary.token_open) :]
        if vocabulary.token_close and text.endswith(vocabulary.token_close):
            text = text[: -len(vocabulary.token_close)]
        return text

    def module(self, token: object) -> str:
        """Return a fitted module's English name, for example "5D Sensors".

        The size and class fold into the game's own rating notation; a mount and
        a physical size move in front of the module they describe, which is the
        order English wants ("Medium Gimballed Multi-Cannon"). Anything left is
        kept in the order the token stated it.
        """
        text = self._unwrap(_as_text(token))
        if not text or _PART_SEPARATOR not in text:
            return self._word(text) if text else _EMPTY
        parts = self._strip_suffix(
            self._strip_prefix(text.lower().split(_PART_SEPARATOR))
        )
        size: int | None = None
        class_number: int | None = None
        grade: int | None = None
        mounts: list[str] = []
        physical: list[str] = []
        head: list[str] = []
        for part in parts:
            numbered = _numbered(part)
            if numbered is not None:
                name, value = numbered
                if name == self._vocabulary.size_token:
                    size = value
                    continue
                if name == self._vocabulary.class_token:
                    class_number = value
                    continue
                if name == self._vocabulary.grade_token:
                    grade = value
                    continue
            if part in self._vocabulary.mounts:
                mounts.append(self._vocabulary.mounts[part])
            elif part in self._vocabulary.sizes:
                physical.append(self._vocabulary.sizes[part])
            else:
                head.append(self._word(part))
        name = _SPACE.join(physical + mounts + head).strip()
        return self._decorate(name, size, class_number, grade)

    def _decorate(
        self, name: str, size: int | None, class_number: int | None, grade: int | None
    ) -> str:
        """Attach the rating or the grade to a decoded module name.

        A module states either a size and class (which become a rating like 5A)
        or a grade, never both in practice; when it states neither, the name
        stands alone. A class the ratings table does not cover states its size
        and class outright instead: no letter is invented for it; equally the
        size it did state is not thrown away to hide the gap.
        """
        if size is not None and class_number is not None:
            rating = self._rating(class_number)
            if rating is not None:
                return self._vocabulary.rated_format.format(
                    size=size, rating=rating, name=name
                )
            return self._vocabulary.unrated_format.format(
                name=name, size=size, class_number=class_number
            )
        if grade is not None:
            return self._vocabulary.graded_format.format(name=name, grade=grade)
        return name

    def blueprint(self, token: object) -> str:
        """Return a blueprint's English name, for example "Long Range Sensor".

        A blueprint token is stated as ``Category_Effect``. English puts the
        effect first ("Long Range Sensor", "Heavy Duty Armour"), so the parts are
        reordered; no word is added or removed by doing so.

        A category the taxonomy lists in ``drop_categories`` is left off. That
        covers the game's catch-all bucket, whose name describes how Frontier
        filed the blueprint rather than anything the Commander applied it to:
        "Light Weight Misc" says less than "Light Weight" does.
        """
        text = _as_text(token)
        if not text:
            return _EMPTY
        parts = text.split(_PART_SEPARATOR)
        category = _SPACE.join(_pascal_words(parts[0]))
        effect = _SPACE.join(word for part in parts[1:] for word in _pascal_words(part))
        if category in self._vocabulary.drop_categories:
            category = _EMPTY
        if not effect:
            return category
        return f"{effect} {category}".strip()

    def material(self, token: object) -> str:
        """Return a material's English name, leaving a readable one untouched.

        The journal states a readable ``Material_Localised`` for manufactured and
        encoded materials and nothing but the internal name for raw ones. A value
        that already carries a capital or a space is one the game supplied, so it
        is returned exactly as stated.
        """
        text = _as_text(token)
        if not text:
            return _EMPTY
        if text != text.lower() or _SPACE in text:
            return text
        return self._word(text)


def _as_text(token: object) -> str:
    """Return a token as a stripped string; empty when it is not one."""
    if isinstance(token, str):
        return token.strip()
    return _EMPTY
