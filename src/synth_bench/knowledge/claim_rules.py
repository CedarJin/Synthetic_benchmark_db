"""Claim and allergen declaration rules (Module 2 operators support).

Provides:
  - Allergen declaration formatting (Contains: milk, wheat)
  - Nutrient content claim templates
  - Health claim eligibility rules
  - Label statement templates
"""

from __future__ import annotations

from dataclasses import dataclass

from synth_bench.knowledge.fda_rules import (
    compute_daily_value_percent,
)
from synth_bench.knowledge.ingredient_knowledge import detect_allergens

# ── Allergen Declarations ─────────────────────────────────────────────────────

ALLERGEN_DECLARATION_TEMPLATES: list[str] = [
    "Contains: {allergens}",
    "Contains {allergens}",
    "Allergens: {allergens}",
    "Contains: {allergens}.",
]

ALLERGEN_ORDER: list[str] = [
    "milk",
    "eggs",
    "fish",
    "crustacean shellfish",
    "tree nuts",
    "peanuts",
    "wheat",
    "soybeans",
    "sesame",
]


def format_allergen_declaration(
    ingredient_names: list[str],
    include_may_contain: bool = True,
) -> str | None:
    """Format an allergen declaration line from ingredient names.

    Args:
        ingredient_names: List of ingredient descriptions.
        include_may_contain: Whether to include a "May contain" advisory.

    Returns:
        Formatted allergen declaration string, or None if no allergens.
    """
    allergens = detect_allergens(ingredient_names)
    if not allergens:
        return None

    # Sort by FDA allergen order
    ordered: list[str] = []
    for a in ALLERGEN_ORDER:
        if a in allergens:
            ordered.append(a)
    # Add any extra allergens not in the standard order
    for a in allergens:
        if a not in ordered:
            ordered.append(a)

    if len(ordered) == 1:
        text = ordered[0].upper()
    elif len(ordered) == 2:
        text = f"{ordered[0].upper()} and {ordered[1].upper()}"
    else:
        text = ", ".join(a.upper() for a in ordered[:-1]) + f" and {ordered[-1].upper()}"

    # Choose template based on length
    if len(text) < 80:
        declaration = f"CONTAINS: {text}"
    else:
        declaration = f"CONTAINS {text}"

    if include_may_contain:
        # Mayo contain advisory (less common, only for shared facilities)
        pass

    return declaration


# ── Nutrient Content Claim Templates ──────────────────────────────────────────

NUTRIENT_CONTENT_CLAIM_TEMPLATES: dict[str, str] = {
    "fat_free": "FAT FREE",
    "low_fat": "LOW FAT",
    "reduced_fat": "{percent}% REDUCED FAT",
    "saturated_fat_free": "SATURATED FAT FREE",
    "low_saturated_fat": "LOW SATURATED FAT",
    "cholesterol_free": "CHOLESTEROL FREE",
    "low_cholesterol": "LOW CHOLESTEROL",
    "sodium_free": "SODIUM FREE",
    "very_low_sodium": "VERY LOW SODIUM",
    "low_sodium": "LOW SODIUM",
    "sugar_free": "SUGAR FREE",
    "no_added_sugar": "NO ADDED SUGAR",
    "calorie_free": "CALORIE FREE",
    "low_calorie": "LOW CALORIE",
    "good_source_fiber": "GOOD SOURCE OF FIBER",
    "excellent_source_fiber": "EXCELLENT SOURCE OF FIBER",
}


def format_nutrient_content_claims(
    eligible_claims: list[str],
    percent: int | None = None,
) -> list[str]:
    """Format eligible nutrient content claims.

    Args:
        eligible_claims: List of claim identifiers (from check_nutrient_content_claim).
        percent: Optional percentage for 'reduced' type claims.

    Returns:
        List of formatted claim strings.
    """
    formatted: list[str] = []
    for claim in eligible_claims:
        template = NUTRIENT_CONTENT_CLAIM_TEMPLATES.get(claim, claim)
        if "{percent}" in template and percent is not None:
            formatted.append(template.format(percent=percent))
        else:
            formatted.append(template)
    return formatted


# ── % Daily Value / Good Source / Excellent Source Claims ─────────────────────


@dataclass(frozen=True)
class SourceClaim:
    """A source-level nutrient content claim."""

    nutrient: str
    level: str  # "good_source" or "excellent_source"


SOURCE_CLAIM_DISPLAY_NAMES: dict[str, str] = {
    "Protein": "PROTEIN",
    "Fiber, total dietary": "DIETARY FIBER",
    "Vitamin D (D2 + D3)": "VITAMIN D",
    "Calcium, Ca": "CALCIUM",
    "Iron, Fe": "IRON",
    "Potassium, K": "POTASSIUM",
}


def check_source_claims(
    nutrient_amounts_per_serving: dict[str, float],
) -> list[str]:
    """Check which '% Daily Value' based source claims apply.

    Good source = 10-19% DV per serving.
    Excellent source = 20%+ DV per serving.

    Args:
        nutrient_amounts_per_serving: {nutrient_name: amount_per_serving}.

    Returns:
        List of formatted claim strings (e.g. "GOOD SOURCE OF CALCIUM").
    """
    claims: list[str] = []
    for nutrient_name, amount in nutrient_amounts_per_serving.items():
        display_name = SOURCE_CLAIM_DISPLAY_NAMES.get(nutrient_name)
        if display_name is None:
            continue
        dv_pct = compute_daily_value_percent(nutrient_name, amount)
        if dv_pct is None:
            continue
        if dv_pct >= 20:
            claims.append(f"EXCELLENT SOURCE OF {display_name}")
        elif dv_pct >= 10:
            claims.append(f"GOOD SOURCE OF {display_name}")
    return claims


# ── Health Claims (simplified, from 21 CFR 101) ───────────────────────────────


@dataclass(frozen=True)
class HealthClaim:
    """A qualified health claim rule."""

    claim_id: str
    claim_text: str
    condition_nutrient: str
    condition_threshold_per_serving: float
    condition_comparison: str  # "below" or "above"
    restricted_nutrients: list[str] | None = None  # must also be below thresholds


HEALTH_CLAIMS: list[HealthClaim] = [
    HealthClaim(
        claim_id="calcium_osteoporosis",
        claim_text="Adequate calcium throughout life may reduce the risk of osteoporosis.",
        condition_nutrient="Calcium, Ca",
        condition_threshold_per_serving=200,  # mg per serving
        condition_comparison="above",
        restricted_nutrients=[],
    ),
    HealthClaim(
        claim_id="sodium_hypertension",
        claim_text="Diets low in sodium may reduce the risk of high blood pressure.",
        condition_nutrient="Sodium, Na",
        condition_threshold_per_serving=140,  # mg per serving
        condition_comparison="below",
    ),
    HealthClaim(
        claim_id="fat_cancer",
        claim_text="Diets low in total fat may reduce the risk of some cancers.",
        condition_nutrient="Total lipid (fat)",
        condition_threshold_per_serving=6.5,  # g per serving
        condition_comparison="below",
    ),
    HealthClaim(
        claim_id="saturated_fat_cholesterol_coronary",
        claim_text=(
            "Diets low in saturated fat and cholesterol may reduce the risk of "
            "coronary heart disease."
        ),
        condition_nutrient="Fatty acids, total saturated",
        condition_threshold_per_serving=4,  # g per serving
        condition_comparison="below",
    ),
    HealthClaim(
        claim_id="fiber_cancer",
        claim_text="Diets low in fat and rich in fiber may reduce the risk of some cancers.",
        condition_nutrient="Fiber, total dietary",
        condition_threshold_per_serving=2.8,  # g per serving
        condition_comparison="above",
    ),
    HealthClaim(
        claim_id="potassium_hypertension",
        claim_text=(
            "Diets containing foods that are a good source of potassium may reduce "
            "the risk of high blood pressure."
        ),
        condition_nutrient="Potassium, K",
        condition_threshold_per_serving=470,  # mg per serving
        condition_comparison="above",
    ),
]


def check_health_claims(
    nutrient_amounts_per_serving: dict[str, float],
) -> list[str]:
    """Check which health claims apply based on nutrient amounts per serving.

    Args:
        nutrient_amounts_per_serving: {nutrient_name: amount_per_serving}.

    Returns:
        List of applicable health claim texts.
    """
    applicable: list[str] = []
    for claim in HEALTH_CLAIMS:
        amount = nutrient_amounts_per_serving.get(claim.condition_nutrient)
        if amount is None:
            continue
        if claim.condition_comparison == "below" and amount < claim.condition_threshold_per_serving:
            applicable.append(claim.claim_text)
        elif (
            claim.condition_comparison == "above" and amount > claim.condition_threshold_per_serving
        ):
            applicable.append(claim.claim_text)
    return applicable


# ── Nutrition Facts label templates ───────────────────────────────────────────


def format_daily_value_percent(
    nutrient_name: str,
    amount_per_serving: float,
) -> str | None:
    """Format a % Daily Value line for a nutrient.

    Args:
        nutrient_name: USDA standard nutrient name.
        amount_per_serving: Amount per serving.

    Returns:
        Formatted DV line, e.g. "Sodium 240mg", or None if unknown.
    """
    dv_pct = compute_daily_value_percent(nutrient_name, amount_per_serving)
    if dv_pct is None:
        return None

    # Round DV% per FDA rules
    dv_rounded = round(dv_pct)
    return f"{dv_rounded}%"


NUTRITION_FACTS_TEMPLATE: str = """Nutrition Facts
Serving Size {serving_size}

{calories_block}
{daily_value_block}
* The % Daily Value tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice."""  # noqa: E501

CALORIES_TEMPLATE: str = """Calories
{calories}"""

DAILY_VALUE_LINE_TEMPLATE: str = "{label}: {amount}{unit}  {dv}%"


def format_nutrition_facts_text(
    serving_size_text: str,
    calories: int,
    nutrient_lines: list[str],
) -> str:
    """Return the full text of a Nutrition Facts panel.

    Args:
        serving_size_text: e.g. "1 cup (240ml)".
        calories: Calorie value.
        nutrient_lines: Formatted DV lines.

    Returns:
        Nutrition Facts text.
    """
    lines = [
        "Nutrition Facts",
        f"Serving Size {serving_size_text}",
        "",
        f"Calories {calories}",
    ]
    for nl in nutrient_lines:
        lines.append(nl)
    lines.extend(
        [
            "",
            "* The % Daily Value tells you how much a nutrient in a serving of food "
            "contributes to a daily diet. 2,000 calories a day is used for general "
            "nutrition advice.",
        ]
    )
    return "\n".join(lines)
