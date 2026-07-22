"""AllergenOperator, ClaimEligibilityOperator, NutritionFactsOperator.

Handles allergen declarations, nutrient content claims, and
Nutrition Facts panel generation.
"""

from __future__ import annotations

from nusol.utils.numerics import apply_fda_rounding

from synth_bench.canonical.models import (
    AllergenDeclaration,
    ClaimDeclaration,
    NutritionFactsPanel,
)
from synth_bench.knowledge.claim_rules import (
    check_health_claims,
    check_source_claims,
    format_allergen_declaration,
    format_nutrient_content_claims,
)
from synth_bench.knowledge.fda_rules import (
    check_nutrient_content_claim,
    compute_daily_value_percent,
    determine_serving_size,
)
from synth_bench.knowledge.ingredient_knowledge import detect_allergens
from synth_bench.transform.engine import BaseOperator, LabelState

# ── Nutrient name → claim group mapping ───────────────────────────────────────

CLAIM_NUTRIENT_MAP: dict[str, str] = {
    "fat": "Total lipid (fat)",
    "saturated_fat": "Fatty acids, total saturated",
    "cholesterol": "Cholesterol",
    "sodium": "Sodium, Na",
    "sugar": "Total Sugars",
    "energy": "Energy",
    "fiber": "Fiber, total dietary",
}


# ── AllergenOperator ──────────────────────────────────────────────────────────


class AllergenOperator(BaseOperator):
    """Add allergen declaration lines based on ingredient content.

    Scans declared ingredients for FDA major allergens and appends
    a "Contains: milk, wheat, eggs, ..." declaration.
    """

    name: str = "allergen"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        all_names = [ing.original_description for ing in state.declared_ingredients] + [
            ing.original_description for ing in state.two_percent_group
        ]

        decl_text = format_allergen_declaration(all_names)
        if decl_text is not None:
            allergens = detect_allergens(all_names)
            state.allergens = AllergenDeclaration(
                allergens=allergens,
                declaration_text=decl_text,
            )

        state.operator_records.append(
            self.make_record(
                affected=all_names if decl_text is not None else None,
            )
        )
        return state


# ── ClaimEligibilityOperator ──────────────────────────────────────────────────


class ClaimEligibilityOperator(BaseOperator):
    """Evaluate and add eligible nutrient content and health claims.

    Checks FDA thresholds for nutrient content claims (low fat,
    good source of fiber, etc.) and health claims based on
    the Food's nutrient profile per serving.
    """

    name: str = "claim"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        from nusol.core.units import convert_to_per_serving

        food = state.canonical_food
        serving_size = determine_serving_size(
            food_code=food.food_code,
            food_name=food.food_name,
            fndds_serving_size_g=food.canonical_serving.serving_size_g,
        )

        # Build per-serving and per-100g nutrient amounts
        per_serving: dict[str, float] = {}
        per_100g: dict[str, float] = {}
        for n in food.nutrients:
            per_serving[n.name] = convert_to_per_serving(n.amount, serving_size)
            per_100g[n.name] = n.amount

        # ── Determine is_liquid heuristic ──
        name_lower = food.food_name.lower()
        is_liquid = any(
            kw in name_lower for kw in ("milk", "juice", "beverage", "broth", "soup", "drink")
        )

        # ── Nutrient content claims (free/low/reduced) ──
        eligible_content_claims: list[str] = []
        for claim_group, nutrient_key in CLAIM_NUTRIENT_MAP.items():
            if claim_group == "fiber":  # source claims handled via %DV
                continue
            ps_val = per_serving.get(nutrient_key)
            p100_val = per_100g.get(nutrient_key)
            if ps_val is None or p100_val is None:
                continue
            eligible = check_nutrient_content_claim(
                claim_group,
                ps_val,
                p100_val,
                is_liquid=is_liquid,
            )
            eligible_content_claims.extend(eligible)

        formatted_claims = format_nutrient_content_claims(eligible_content_claims)

        # ── Source claims (Good/Excellent Source) via %DV ──
        source_claim_texts = check_source_claims(per_serving)
        formatted_claims.extend(source_claim_texts)

        # ── Health claims ──
        health_claim_texts = check_health_claims(per_serving)
        formatted_claims.extend(health_claim_texts)
        formatted_claims = list(dict.fromkeys(formatted_claims))

        # Build ClaimDeclaration objects
        claims_list: list[ClaimDeclaration] = []
        for claim_text in formatted_claims:
            claim_type = (
                "nutrient_content"
                if any(kw in claim_text.lower() for kw in ("source", "free", "low", "reduced"))
                else "health"
            )
            claims_list.append(
                ClaimDeclaration(
                    claim_text=claim_text,
                    claim_type=claim_type,
                )
            )

        state.claims = claims_list
        state.operator_records.append(
            self.make_record(
                affected=list(per_serving.keys()),
                n_claims=len(claims_list),
            )
        )
        return state


# ── NutritionFactsOperator ────────────────────────────────────────────────────


class NutritionFactsOperator(BaseOperator):
    """Generate the Nutrition Facts panel from the canonical food nutrients.

    Produces a NutritionFactsPanel with:
      - Serving size (from RACC or FNDDS)
      - Calorie value per serving
      - Macronutrient values per serving (rounded per FDA rules)
      - % Daily Values
    """

    name: str = "nutrition_facts"
    version: str = "1.0"

    def apply(self, state: LabelState) -> LabelState:
        from nusol.core.units import convert_to_per_serving

        food = state.canonical_food
        serving_size = determine_serving_size(
            food_code=food.food_code,
            food_name=food.food_name,
            fndds_serving_size_g=food.canonical_serving.serving_size_g,
        )

        # Helper: get FDA-rounded per-serving value
        def _per_serving(name: str) -> float | None:
            for n in food.nutrients:
                if n.name == name:
                    return apply_fda_rounding(
                        convert_to_per_serving(n.amount, serving_size),
                        name,
                    )
            return None

        def _dv(name: str) -> float | None:
            amount = _per_serving(name)
            if amount is None:
                return None
            dv = compute_daily_value_percent(name, amount)
            return round(dv) if dv is not None else None

        calories = _per_serving("Energy")

        panel = NutritionFactsPanel(
            serving_size=f"{serving_size:.0f}g",
            servings_per_container=state.config.get("servings_per_container"),
            calories=round(calories) if calories is not None else 0.0,
            total_fat=_per_serving("Total lipid (fat)"),
            saturated_fat=_per_serving("Fatty acids, total saturated"),
            trans_fat=_per_serving("Fatty acids, total trans"),
            cholesterol=_per_serving("Cholesterol"),
            sodium=_per_serving("Sodium, Na"),
            total_carbohydrate=_per_serving("Carbohydrate, by difference"),
            dietary_fiber=_per_serving("Fiber, total dietary"),
            total_sugars=_per_serving("Total Sugars"),
            added_sugars=_per_serving("Sugars, added"),
            protein=_per_serving("Protein"),
            vitamin_d=_per_serving("Vitamin D (D2 + D3)"),
            calcium=_per_serving("Calcium, Ca"),
            iron=_per_serving("Iron, Fe"),
            potassium=_per_serving("Potassium, K"),
            daily_values={},
        )

        # Populate %DV references
        for dv_nutrient in [
            "Total lipid (fat)",
            "Fatty acids, total saturated",
            "Cholesterol",
            "Sodium, Na",
            "Carbohydrate, by difference",
            "Fiber, total dietary",
            "Protein",
            "Vitamin D (D2 + D3)",
            "Calcium, Ca",
            "Iron, Fe",
            "Potassium, K",
        ]:
            dv_pct = _dv(dv_nutrient)
            if dv_pct is not None:
                panel.daily_values[dv_nutrient] = dv_pct

        state.nutrition_facts = panel
        state.operator_records.append(self.make_record(serving_size_g=serving_size))
        return state
