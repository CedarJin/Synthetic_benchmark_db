"""Validation rules for synthetic benchmark samples.

Each rule checks one aspect of a BenchmarkSample and returns
a ValidationResult. Rules can optionally auto-repair samples.
"""

from __future__ import annotations

import re
from typing import Any

from synth_bench.canonical.models import BenchmarkSample
from synth_bench.validation.validator import BaseValidator, ValidationResult

# ═══════════════════════════════════════════════════════════════════════════════
# Ingredient Preservation Rule
# ═══════════════════════════════════════════════════════════════════════════════


class IngredientPreservationRule(BaseValidator):
    """Verify that all canonical ingredients appear in the structured label.

    Checks:
      - Every non-fortificant canonical ingredient is present in the label.
      - No extra (unmapped) ingredients appear.
    """

    name: str = "ingredient_preservation"
    description: str = "Check all canonical ingredients appear in the structured label"

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        canonical_ingredients = {
            ing.description for ing in sample.canonical_food.ingredients if not ing.is_fortificant
        }

        label_ingredients = {
            ing.original_description for ing in sample.structured_label.ingredient_list
        } | {ing.original_description for ing in sample.structured_label.two_percent_group}

        missing = canonical_ingredients - label_ingredients
        extra = label_ingredients - canonical_ingredients

        n_canon = len(canonical_ingredients)
        n_label = len(label_ingredients)

        passed = len(missing) == 0 and n_canon == n_label

        details: dict[str, Any] = {
            "canonical_count": n_canon,
            "label_count": n_label,
            "missing": sorted(missing),
            "extra": sorted(extra),
        }

        if passed:
            return ValidationResult(
                rule_name=self.name,
                passed=True,
                message=f"All {n_canon} ingredients preserved in label",
                details=details,
            )
        else:
            msg_parts = []
            if missing:
                msg_parts.append(f"Missing: {', '.join(sorted(missing))}")
            if extra:
                msg_parts.append(f"Extra: {', '.join(sorted(extra))}")
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                message="; ".join(msg_parts),
                details=details,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Ingredient Order Rule
# ═══════════════════════════════════════════════════════════════════════════════


class IngredientOrderRule(BaseValidator):
    """Verify that ingredient order follows label weight conventions.

    Checks:
      - Main list ingredient fractions are non-increasing.
      - ≤2% group ingredients are below the grouping threshold.
      - The ≤2% group is not heavier than any main-list ingredient.
    """

    name: str = "ingredient_order"
    description: str = "Verify ingredient order follows descending fraction order"
    DEFAULT_LT2_THRESHOLD: float = 0.02
    FRACTION_TOLERANCE: float = 1e-9

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        violations: list[str] = []
        prev_fraction = float("inf")
        for i, declared_ing in enumerate(sample.structured_label.ingredient_list):
            current_fraction = declared_ing.original_fraction
            if current_fraction > prev_fraction + self.FRACTION_TOLERANCE:
                violations.append(
                    f"Position {i}: '{declared_ing.original_description}' "
                    f"fraction={current_fraction:.4f} after previous fraction={prev_fraction:.4f}"
                )
            prev_fraction = min(prev_fraction, current_fraction)

        # Check ≤2% group — should contain only low-fraction ingredients.
        if sample.structured_label.two_percent_group:
            main_fracs = [ing.original_fraction for ing in sample.structured_label.ingredient_list]
            lt_fracs = [ing.original_fraction for ing in sample.structured_label.two_percent_group]
            threshold = _operator_config_value(
                sample,
                operator_name="less_than_2_pct",
                key="threshold",
                default=self.DEFAULT_LT2_THRESHOLD,
            )
            oversized = [
                ing.original_description
                for ing in sample.structured_label.two_percent_group
                if ing.original_fraction > threshold + self.FRACTION_TOLERANCE
            ]
            if oversized:
                violations.append(
                    f"≤2% group has ingredients above threshold {threshold:.3f}: "
                    f"{', '.join(oversized)}"
                )
            if lt_fracs and main_fracs:
                max_lt = max(lt_fracs)
                min_main = min(main_fracs)
                if max_lt > min_main + self.FRACTION_TOLERANCE:
                    violations.append(
                        f"≤2% group has fraction {max_lt:.3f} which is > "
                        f"main group min {min_main:.3f}"
                    )

        passed = len(violations) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message=f"{len(violations)} order violations"
            if violations
            else "Ingredient order correct",
            details={"violations": violations, "n_violations": len(violations)},
        )


def _operator_config_value(
    sample: BenchmarkSample,
    operator_name: str,
    key: str,
    default: float,
) -> float:
    for record in sample.metadata.operator_records:
        if record.operator_name == operator_name and key in record.config:
            value = record.config[key]
            if isinstance(value, int | float):
                return float(value)
    return default


# ═══════════════════════════════════════════════════════════════════════════════
# FDA Syntax Rule
# ═══════════════════════════════════════════════════════════════════════════════


# Common FDA-prohibited or discouraged terms on food labels
PROHIBITED_TERMS: list[re.Pattern] = [
    re.compile(r"\bnatural\b", re.I),  # "natural" has strict FSIS/FDA rules
    re.compile(r"\bwholesome\b", re.I),
    re.compile(r"\bhealthful\b", re.I),
    re.compile(r"\borganic\b", re.I),  # "organic" requires USDA certification
    re.compile(r"\bcure\b", re.I),  # disease claim
    re.compile(r"\bmiracle\b", re.I),
    re.compile(r"\bguaranteed\b", re.I),
    re.compile(r"\b100%\s*(natural|pure|organic)\b", re.I),
]

# Required elements on a Nutrition Facts label
REQUIRED_NF_ELEMENTS: list[str] = [
    "Serving Size",
    "Calories",
    "Total Fat",
    "Sodium",
    "Total Carbohydrate",
    "Protein",
]


class FDASyntaxRule(BaseValidator):
    """Check that the label follows basic FDA syntax conventions.

    Checks:
      - No prohibited or misleading terms.
      - Required Nutrition Facts elements present.
      - Ingredient list format conventions.
    """

    name: str = "fda_syntax"
    description: str = "Check FDA syntax compliance"

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        issues: list[str] = []

        # Check rendered label text
        label_text = sample.rendered_label_text or ""
        nf_text = sample.rendered_nutrition_facts or ""

        # Check for prohibited terms
        for pattern in PROHIBITED_TERMS:
            if pattern.search(label_text) or pattern.search(nf_text):
                issues.append(f"Potentially prohibited term: '{pattern.pattern}'")

        # Check NF panel required elements
        nf = sample.nutrition_facts_json
        if nf is not None:
            # Check required fields are populated (allow 0 for zero-calorie foods)
            if nf.serving_size is None or nf.serving_size == "":
                issues.append("Serving size not set")
            if nf.total_fat is None:
                issues.append("Total Fat not set")
            if nf.sodium is None:
                issues.append("Sodium not set")
            if nf.total_carbohydrate is None:
                issues.append("Total Carbohydrate not set")
            if nf.protein is None:
                issues.append("Protein not set")
        else:
            issues.append("No Nutrition Facts panel")

        passed = len(issues) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message=f"{len(issues)} FDA syntax issues" if issues else "FDA syntax OK",
            details={"issues": issues, "n_issues": len(issues)},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Allergen Declaration Rule
# ═══════════════════════════════════════════════════════════════════════════════


class AllergenDeclarationRule(BaseValidator):
    """Verify allergen declarations match ingredient content.

    Checks:
      - If allergens are present in ingredients, a declaration exists.
      - If a declaration exists, its allergens are actually present.
    """

    name: str = "allergen_declaration"
    description: str = "Check allergen declarations match ingredient content"

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        from synth_bench.knowledge.ingredient_knowledge import detect_allergens

        # Get all ingredient descriptions
        all_desc = [ing.original_description for ing in sample.structured_label.ingredient_list] + [
            ing.original_description for ing in sample.structured_label.two_percent_group
        ]

        detected = set(detect_allergens(all_desc))

        declared: set[str] = set()
        if sample.structured_label.allergens is not None:
            structured_declared = set(sample.structured_label.allergens.allergens)
            declared.update(structured_declared)
            decl_text = sample.structured_label.allergens.declaration_text.lower()
            for allergen in [
                "crustacean shellfish",
                "tree nuts",
                "soybeans",
                "peanuts",
                "sesame",
                "milk",
                "eggs",
                "wheat",
                "fish",
            ]:
                if re.search(rf"(?<![a-z0-9]){re.escape(allergen)}(?![a-z0-9])", decl_text):
                    declared.add(allergen)
            if "fish" not in structured_declared and "crustacean shellfish" in declared:
                declared.discard("fish")

        missing_declaration = detected - declared
        false_declaration = declared - detected

        issues: list[str] = []
        if missing_declaration:
            issues.append(
                f"Missing allergen declarations: {', '.join(sorted(missing_declaration))}"
            )
        if false_declaration:
            issues.append(
                f"Unexpected allergen declarations: {', '.join(sorted(false_declaration))}"
            )

        passed = len(issues) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message="; ".join(issues)
            if issues
            else f"Allergens correct ({len(detected)} detected)",
            details={
                "detected": sorted(detected),
                "declared": sorted(declared),
                "missing": sorted(missing_declaration),
                "false": sorted(false_declaration),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Claim Eligibility Rule
# ═══════════════════════════════════════════════════════════════════════════════


class ClaimEligibilityRule(BaseValidator):
    """Verify that claims on the label are eligible based on nutrient content.

    Checks:
      - Each "Free" claim has per-serving amount below threshold.
      - Each "Low" claim meets per-100g threshold.
      - Each "Source" claim corresponds to 10%+ DV.
    """

    name: str = "claim_eligibility"
    description: str = "Check claim eligibility based on nutrient content"

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        from nusol.core.units import convert_to_per_serving

        from synth_bench.knowledge.fda_rules import determine_serving_size

        food = sample.canonical_food
        serving_size = determine_serving_size(
            food_code=food.food_code,
            food_name=food.food_name,
            fndds_serving_size_g=food.canonical_serving.serving_size_g,
        )

        # Build per-serving nutrient amounts
        per_serving: dict[str, float] = {}
        for n in sample.canonical_food.nutrients:
            per_serving[n.name] = convert_to_per_serving(n.amount, serving_size)

        # Check claims
        issues: list[str] = []
        for claim in sample.structured_label.claims:
            claim_lower = claim.claim_text.lower()

            # Check "Free" claims (amount per serving below threshold)
            if "saturated fat free" in claim_lower:
                sat_fat_ps = per_serving.get("Fatty acids, total saturated", 1.0)
                if sat_fat_ps >= 0.5:
                    issues.append(
                        "'Saturated Fat Free' claim but saturated "
                        f"fat={sat_fat_ps:.1f}g/serving (≥0.5)"
                    )
            elif "fat free" in claim_lower:
                fat_ps = per_serving.get("Total lipid (fat)", 1.0)
                if fat_ps >= 0.5:
                    issues.append(f"'Fat Free' claim but fat={fat_ps:.1f}g/serving (≥0.5)")
            if "sodium free" in claim_lower:
                na_ps = per_serving.get("Sodium, Na", 1000.0)
                if na_ps >= 5:
                    issues.append(f"'Sodium Free' claim but sodium={na_ps:.0f}mg/serving (≥5)")

            # Check "Source" claims
            if "good source" in claim_lower or "excellent source" in claim_lower:
                from synth_bench.knowledge.fda_rules import compute_daily_value_percent

                # Extract the nutrient name from the claim
                for n_name in ["CALCIUM", "FIBER", "IRON", "POTASSIUM", "VITAMIN D", "PROTEIN"]:
                    if n_name.lower() in claim_lower:
                        # Find the USDA nutrient name
                        usda_name = _DISPLAY_TO_USDA.get(n_name)
                        if usda_name and usda_name in per_serving:
                            dv = compute_daily_value_percent(usda_name, per_serving[usda_name])
                            if dv is not None and dv < 10 and "good" in claim_lower:
                                issues.append(f"'{claim.claim_text}' but DV={dv:.0f}% (<10%)")
                            elif dv is not None and dv < 20 and "excellent" in claim_lower:
                                issues.append(f"'{claim.claim_text}' but DV={dv:.0f}% (<20%)")

        passed = len(issues) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message="; ".join(issues) if issues else "All claims eligible",
            details={"issues": issues, "n_claims": len(sample.structured_label.claims)},
        )


# Map from display nutrient names to USDA standard names
_DISPLAY_TO_USDA: dict[str, str] = {
    "CALCIUM": "Calcium, Ca",
    "FIBER": "Fiber, total dietary",
    "IRON": "Iron, Fe",
    "POTASSIUM": "Potassium, K",
    "VITAMIN D": "Vitamin D (D2 + D3)",
    "PROTEIN": "Protein",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Nutrition Facts Consistency Rule
# ═══════════════════════════════════════════════════════════════════════════════


class NutritionFactsConsistencyRule(BaseValidator):
    """Verify Nutrition Facts panel is consistent with canonical nutrients.

    Checks:
      - NF calories match the Energy nutrient after per-serving conversion.
      - NF macronutrient values are within rounding tolerance of computed values.
    """

    name: str = "nutrition_facts_consistency"
    description: str = "Check NF panel consistency with canonical nutrients"

    # Allowable absolute difference for rounding
    ROUNDING_TOLERANCE: float = 2.0

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        from nusol.core.units import convert_to_per_serving
        from nusol.utils.numerics import apply_fda_rounding

        from synth_bench.knowledge.fda_rules import determine_serving_size

        nf = sample.nutrition_facts_json
        if nf is None:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                message="No Nutrition Facts JSON to validate",
                details={},
            )

        food = sample.canonical_food
        sv = determine_serving_size(
            food_code=food.food_code,
            food_name=food.food_name,
            fndds_serving_size_g=food.canonical_serving.serving_size_g,
        )
        issues: list[str] = []

        # Helper: get per-serving rounded value
        def _ps(name: str) -> float | None:
            for n in sample.canonical_food.nutrients:
                if n.name == name:
                    return apply_fda_rounding(convert_to_per_serving(n.amount, sv), name)
            return None

        # Check calories
        expected_cal = _ps("Energy")
        if expected_cal is None:
            issues.append("Energy nutrient missing from canonical food")
        elif abs(expected_cal - nf.calories) > self.ROUNDING_TOLERANCE:
            issues.append(f"Calories: label={nf.calories}, expected≈{expected_cal:.0f}")

        # Check total fat
        if nf.total_fat is not None:
            expected = _ps("Total lipid (fat)")
            if expected is not None and abs(expected - nf.total_fat) > self.ROUNDING_TOLERANCE:
                issues.append(f"Total Fat: label={nf.total_fat}g, expected≈{expected:.1f}g")

        # Check sodium
        if nf.sodium is not None:
            expected = _ps("Sodium, Na")
            if expected is not None and abs(expected - nf.sodium) > self.ROUNDING_TOLERANCE * 10:
                issues.append(f"Sodium: label={nf.sodium}mg, expected≈{expected:.0f}mg")

        # Check protein
        if nf.protein is not None:
            expected = _ps("Protein")
            if expected is not None and abs(expected - nf.protein) > self.ROUNDING_TOLERANCE:
                issues.append(f"Protein: label={nf.protein}g, expected≈{expected:.1f}g")

        passed = len(issues) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message="; ".join(issues) if issues else "NF panel consistent",
            details={"issues": issues, "serving_size_g": sv},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Prohibited Terminology Rule
# ═══════════════════════════════════════════════════════════════════════════════


class ProhibitedTerminologyRule(BaseValidator):
    """Check for FDA-prohibited or restricted terminology on labels.

    Separate check from FDASyntaxRule for clearer diagnostics.
    """

    name: str = "prohibited_terminology"
    description: str = "Check for FDA-prohibited terminology"

    def validate(self, sample: BenchmarkSample) -> ValidationResult:
        label_text = (
            (sample.rendered_label_text or "") + " " + (sample.rendered_nutrition_facts or "")
        )
        label_lower = label_text.lower()

        violations: list[str] = []
        for pattern in PROHIBITED_TERMS:
            if pattern.search(label_lower):
                violations.append(f"Found: '{pattern.pattern}'")

        passed = len(violations) == 0
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            message="; ".join(violations) if violations else "No prohibited terminology",
            details={"violations": violations},
        )
