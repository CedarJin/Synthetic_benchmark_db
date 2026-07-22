"""RenameOperator and GenericNameOperator.

Renames FNDDS standardized descriptions to commercial label names.
"""

from __future__ import annotations

from synth_bench.knowledge.ingredient_knowledge import (
    lookup_commercial_name,
    make_generic,
)
from synth_bench.transform.engine import BaseOperator, LabelState


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

    Performs word-level matching: each word in the declared name is checked
    against the generic name map. If a match is found, the whole name is
    replaced with the generic equivalent.

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

            # Try word-level matching
            words = ing.declared_name.title().split()
            for word in words:
                generic = make_generic(word)
                if generic != word:
                    affected.append(ing.original_description)
                    ing.declared_name = generic.upper()
                    break

        state.operator_records.append(
            self.make_record(affected=affected or None)
        )
        return state
