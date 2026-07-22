"""CompoundIngredientOperator and LessThan2PercentOperator.

Handles compound ingredient expansion and ≤2% group declarations.
"""

from __future__ import annotations

from synth_bench.canonical.models import DeclaredIngredient
from synth_bench.knowledge.ingredient_knowledge import expand_compound
from synth_bench.transform.engine import BaseOperator, LabelState


class CompoundIngredientOperator(BaseOperator):
    """Expand known compound ingredients into their sub-ingredient declarations.

    E.g.: "CHOCOLATE" → "CHOCOLATE (COCOA MASS, SUGAR, COCOA BUTTER, ...)"

    Only compounds in the knowledge base are expanded. Unknown compounds
    are left as-is.
    """

    name: str = "compound"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        affected: list[str] = []
        expanded: list[DeclaredIngredient] = []

        for ing in state.declared_ingredients:
            recipe = expand_compound(ing.declared_name.title())
            if recipe is not None:
                affected.append(ing.original_description)
                # Mark the original as compound
                ing.is_compound = True
                # Add sub-ingredient names
                sub_names = [name.upper() for name, _ in recipe]
                ing.sub_ingredients = sub_names
                # Generate parenthetical text
                ing.declared_name = f"{ing.declared_name} ({', '.join(sub_names)})"
            expanded.append(ing)

        state.declared_ingredients = expanded
        state.operator_records.append(
            self.make_record(affected=affected or None)
        )
        return state


class LessThan2PercentOperator(BaseOperator):
    """Move low-fraction ingredients (<2%) into a 'Contains 2% or less' group.

    Ingredients with fraction below the threshold are moved to
    ``two_percent_group``. The remaining ingredients stay in the
    main list with a "Contains 2% or less of ..." note appended.
    """

    name: str = "less_than_2_pct"
    version: str = "1.0"

    # Default threshold — set via state.config["lt2pct_threshold"]
    DEFAULT_THRESHOLD: float = 0.02

    def apply(self, state: LabelState) -> LabelState:
        threshold = state.config.get("lt2pct_threshold", self.DEFAULT_THRESHOLD)
        if threshold <= 0:
            return state  # feature disabled

        main: list[DeclaredIngredient] = []
        lt2pct: list[DeclaredIngredient] = []

        for ing in state.declared_ingredients:
            if ing.original_fraction <= threshold:
                ing.declaration_group = "two_percent_or_less"
                lt2pct.append(ing)
            else:
                main.append(ing)

        state.declared_ingredients = main
        state.two_percent_group = lt2pct

        affected = [ing.original_description for ing in lt2pct]
        state.operator_records.append(
            self.make_record(
                affected=affected or None,
                threshold=threshold,
            )
        )
        return state
