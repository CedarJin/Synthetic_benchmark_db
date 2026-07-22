"""RenameOperator and GenericNameOperator.

Renames FNDDS standardized descriptions to commercial label names.
"""

from __future__ import annotations

from synth_bench.knowledge.ingredient_knowledge import (
    GENERIC_NAME_MAP,
    lookup_commercial_name,
    make_generic,
)
from synth_bench.transform.engine import BaseOperator, LabelState


def _contains_target_category(declared_name: str, matched_word: str, generic_name: str) -> bool:
    declared_words = {
        word.strip(" ,()").casefold()
        for word in declared_name.split()
        if word.strip(" ,()")
    }
    declared_words.discard(matched_word.casefold())
    target_words = {
        word.strip(" ,()").casefold().removesuffix("s")
        for word in generic_name.split()
        if word.strip(" ,()")
    }
    declared_singular = {word.removesuffix("s") for word in declared_words}
    return bool(target_words & declared_singular)


class RenameOperator(BaseOperator):
    """Convert FNDDS standardized ingredient names to commercial label names.

    E.g.: "Milk, whole, 3.25% milkfat, with added vitamin D" → "MILK"
    """

    name: str = "rename"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        affected: list[str] = []
        for ing in state.declared_ingredients:
            commercial = lookup_commercial_name(ing.original_description)
            if commercial != ing.declared_name:
                affected.append(ing.original_description)
                ing.declared_name = commercial

        state.operator_records.append(
            self.make_record(affected=affected or None)
        )
        return state


class GenericNameOperator(BaseOperator):
    """Replace specific variety/cultivar names with generic descriptions.

    Performs whole-name and constrained phrase/word-level matching. Single-word matches are only
    accepted when the declared name also contains the target ingredient category, preventing
    ambiguous words such as "butter" from changing "BUTTER OIL" to "LETTUCE".

    E.g.: "CHEDDAR CHEESE" → "CHEESE", "GRANNY SMITH APPLES" → "APPLES"
    """

    name: str = "generic_name"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        affected: list[str] = []
        for ing in state.declared_ingredients:
            # Try whole-name match first
            generic = make_generic(ing.declared_name.title())
            if generic != ing.declared_name.title():
                affected.append(ing.original_description)
                ing.declared_name = generic.upper()
                continue

            # Try phrase-level matching for multi-word variety names.
            declared_title = ing.declared_name.title()
            declared_lower = declared_title.casefold()
            phrase_match = False
            for phrase in sorted(GENERIC_NAME_MAP, key=len, reverse=True):
                if len(phrase.split()) < 2 or phrase.casefold() not in declared_lower:
                    continue
                generic = make_generic(phrase)
                if generic != phrase:
                    affected.append(ing.original_description)
                    ing.declared_name = generic.upper()
                    phrase_match = True
                    break
            if phrase_match:
                continue

            # Try constrained word-level matching.
            words = declared_title.split()
            for word in words:
                generic = make_generic(word)
                if generic != word and _contains_target_category(declared_title, word, generic):
                    affected.append(ing.original_description)
                    ing.declared_name = generic.upper()
                    break

        state.operator_records.append(
            self.make_record(affected=affected or None)
        )
        return state
