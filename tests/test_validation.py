"""Tests for the validation framework and all rules."""

from __future__ import annotations

import pytest

from synth_bench.canonical.models import (
    AllergenDeclaration,
    BenchmarkSample,
    CanonicalFood,
    CanonicalIngredient,
    CanonicalServing,
    ClaimDeclaration,
    DeclaredIngredient,
    GroundTruth,
    NutrientValue,
    NutritionFactsPanel,
    SampleMetadata,
    StructuredLabel,
)
from synth_bench.validation.rules import (
    AllergenDeclarationRule,
    ClaimEligibilityRule,
    FDASyntaxRule,
    IngredientOrderRule,
    IngredientPreservationRule,
    NutritionFactsConsistencyRule,
    ProhibitedTerminologyRule,
)
from synth_bench.validation.validator import (
    ValidationEngine,
    ValidationReport,
    ValidationResult,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def simple_sample() -> BenchmarkSample:
    """A minimal valid sample with one ingredient."""
    ing = CanonicalIngredient(
        ingredient_code=1001,
        description="Flour, white",
        weight_g=100.0,
        fraction=1.0,
        sequence_number=1,
    )
    food = CanonicalFood(
        fdc_id=1,
        food_name="White Flour",
        ingredients=[ing],
        nutrients=[NutrientValue(nutrient_id=1008, name="Energy", amount=364.0, unit="kcal")],
    )
    return BenchmarkSample(
        metadata=SampleMetadata(sample_id="simple"),
        canonical_food=food,
        ground_truth=GroundTruth(canonical_food=food),
        structured_label=StructuredLabel(
            product_name="WHITE FLOUR",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Flour, white",
                    declared_name="FLOUR",
                    original_code=1001,
                    original_fraction=1.0,
                ),
            ],
        ),
    )


@pytest.fixture
def multi_ingredient_sample() -> BenchmarkSample:
    """Sample with multiple canonical ingredients matching a label."""
    ings = [
        CanonicalIngredient(
            ingredient_code=1001,
            description="Wheat flour",
            weight_g=60.0,
            fraction=0.60,
            sequence_number=1,
        ),
        CanonicalIngredient(
            ingredient_code=1002,
            description="Sugar",
            weight_g=30.0,
            fraction=0.30,
            sequence_number=2,
        ),
        CanonicalIngredient(
            ingredient_code=1003,
            description="Egg, whole",
            weight_g=10.0,
            fraction=0.10,
            sequence_number=3,
        ),
    ]
    food = CanonicalFood(fdc_id=2, food_name="Cake", ingredients=ings)
    return BenchmarkSample(
        metadata=SampleMetadata(sample_id="multi"),
        canonical_food=food,
        ground_truth=GroundTruth(canonical_food=food),
        structured_label=StructuredLabel(
            product_name="CAKE",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Wheat flour",
                    declared_name="WHEAT FLOUR",
                    original_code=1001,
                    original_fraction=0.60,
                ),
                DeclaredIngredient(
                    original_description="Sugar",
                    declared_name="SUGAR",
                    original_code=1002,
                    original_fraction=0.30,
                ),
                DeclaredIngredient(
                    original_description="Egg, whole",
                    declared_name="EGGS",
                    original_code=1003,
                    original_fraction=0.10,
                ),
            ],
        ),
    )


@pytest.fixture
def validation_engine() -> ValidationEngine:
    engine = ValidationEngine()
    engine.add_rule(IngredientPreservationRule())
    engine.add_rule(IngredientOrderRule())
    engine.add_rule(FDASyntaxRule())
    engine.add_rule(AllergenDeclarationRule())
    engine.add_rule(ClaimEligibilityRule())
    engine.add_rule(NutritionFactsConsistencyRule())
    engine.add_rule(ProhibitedTerminologyRule())
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Framework
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidationFramework:
    """ValidationReport and ValidationEngine."""

    def test_report_counts(self) -> None:
        report = ValidationReport(sample_id="test")
        report.results = [
            ValidationResult(rule_name="r1", passed=True),
            ValidationResult(rule_name="r2", passed=False),
            ValidationResult(rule_name="r3", passed=True),
        ]
        assert report.n_passed == 2
        assert report.n_failed == 1
        assert not report.all_passed

    def test_report_serialization(self) -> None:
        report = ValidationReport(sample_id="test")
        report.results = [
            ValidationResult(rule_name="r1", passed=True, message="OK"),
            ValidationResult(
                rule_name="r2",
                passed=False,
                message="FAIL",
                auto_repaired=True,
                repair_description="fixed",
            ),
        ]
        report.auto_repairs_applied = 1
        d = report.to_dict()
        assert d["sample_id"] == "test"
        assert not d["all_passed"]  # all_passed is now computed from results
        assert d["auto_repairs_applied"] == 1
        assert len(d["results"]) == 2
        assert d["results"][1]["auto_repaired"]

    def test_engine_run_all(
        self, validation_engine: ValidationEngine, multi_ingredient_sample: BenchmarkSample
    ) -> None:
        sample, report = validation_engine.validate(multi_ingredient_sample)
        assert len(report.results) == 7  # all 7 rules
        assert isinstance(sample, BenchmarkSample)

    def test_report_to_dict(
        self, validation_engine: ValidationEngine, multi_ingredient_sample: BenchmarkSample
    ) -> None:
        _, report = validation_engine.validate(multi_ingredient_sample)
        d = report.to_dict()
        assert "sample_id" in d
        assert "results" in d
        assert "all_passed" in d


# ═══════════════════════════════════════════════════════════════════════════════
# Ingredient Preservation Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestIngredientPreservationRule:
    """IngredientPreservationRule tests."""

    def test_all_preserved(self, multi_ingredient_sample: BenchmarkSample) -> None:
        rule = IngredientPreservationRule()
        result = rule.validate(multi_ingredient_sample)
        assert result.passed

    def test_missing_ingredient(self, multi_ingredient_sample: BenchmarkSample) -> None:
        # Remove one ingredient from label
        multi_ingredient_sample.structured_label.ingredient_list.pop()
        rule = IngredientPreservationRule()
        result = rule.validate(multi_ingredient_sample)
        assert not result.passed
        assert "missing" in result.message.lower()

    def test_single_ingredient(self, simple_sample: BenchmarkSample) -> None:
        rule = IngredientPreservationRule()
        result = rule.validate(simple_sample)
        assert result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# Ingredient Order Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestIngredientOrderRule:
    """IngredientOrderRule tests."""

    def test_correct_order(self, multi_ingredient_sample: BenchmarkSample) -> None:
        rule = IngredientOrderRule()
        result = rule.validate(multi_ingredient_sample)
        assert result.passed

    def test_wrong_order(self, multi_ingredient_sample: BenchmarkSample) -> None:
        # Swap first two ingredients
        lst = multi_ingredient_sample.structured_label.ingredient_list
        lst[0], lst[1] = lst[1], lst[0]
        rule = IngredientOrderRule()
        result = rule.validate(multi_ingredient_sample)
        assert not result.passed
        assert "violation" in result.message.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# FDA Syntax Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestFDASyntaxRule:
    """FDASyntaxRule tests."""

    def test_nf_with_required_fields(self) -> None:
        """Sample with complete NF should pass."""
        ing = CanonicalIngredient(
            ingredient_code=1, description="Salt", weight_g=100.0, fraction=1.0, sequence_number=1
        )
        food = CanonicalFood(
            fdc_id=3,
            food_name="Salt",
            ingredients=[ing],
            nutrients=[
                NutrientValue(nutrient_id=1008, name="Energy", amount=0.0, unit="kcal"),
                NutrientValue(nutrient_id=1004, name="Total lipid (fat)", amount=0.0, unit="g"),
                NutrientValue(nutrient_id=1093, name="Sodium, Na", amount=38700.0, unit="mg"),
                NutrientValue(
                    nutrient_id=1005, name="Carbohydrate, by difference", amount=0.0, unit="g"
                ),
                NutrientValue(nutrient_id=1003, name="Protein", amount=0.0, unit="g"),
            ],
        )
        nf = NutritionFactsPanel(
            serving_size="1g",
            calories=0,
            total_fat=0.0,
            sodium=387.0,
            total_carbohydrate=0.0,
            protein=0.0,
        )
        sample = BenchmarkSample(
            metadata=SampleMetadata(sample_id="nf_test"),
            canonical_food=food,
            ground_truth=GroundTruth(canonical_food=food),
            structured_label=StructuredLabel(product_name="SALT"),
            nutrition_facts_json=nf,
        )
        rule = FDASyntaxRule()
        result = rule.validate(sample)
        assert result.passed

    def test_missing_nf_fields(self, simple_sample: BenchmarkSample) -> None:
        rule = FDASyntaxRule()
        result = rule.validate(simple_sample)
        assert not result.passed  # no NF at all

    def test_prohibited_term_in_label(self, simple_sample: BenchmarkSample) -> None:
        simple_sample.rendered_label_text = "100% NATURAL fresh ingredients"
        rule = FDASyntaxRule()
        result = rule.validate(simple_sample)
        assert not result.passed  # "natural" flagged


# ═══════════════════════════════════════════════════════════════════════════════
# Allergen Declaration Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllergenDeclarationRule:
    """AllergenDeclarationRule tests."""

    def test_allergen_detected_no_declaration(
        self, multi_ingredient_sample: BenchmarkSample
    ) -> None:
        """Sample with egg but no allergen declaration should fail."""
        rule = AllergenDeclarationRule()
        result = rule.validate(multi_ingredient_sample)
        # Egg is present but no allergen declaration
        assert not result.passed

    def test_allergen_with_correct_declaration(
        self, multi_ingredient_sample: BenchmarkSample
    ) -> None:
        """Add allergen declaration for egg should pass."""
        multi_ingredient_sample.structured_label.allergens = AllergenDeclaration(
            allergens=["eggs", "wheat"],
            declaration_text="CONTAINS: WHEAT and EGGS",
        )
        rule = AllergenDeclarationRule()
        result = rule.validate(multi_ingredient_sample)
        assert result.passed

    def test_no_allergens(self) -> None:
        """Salt alone should not require an allergen declaration."""
        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Salt",
            weight_g=100.0,
            fraction=1.0,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=7, food_name="Salt", ingredients=[ing])
        sample = BenchmarkSample(
            metadata=SampleMetadata(sample_id="salt"),
            canonical_food=food,
            ground_truth=GroundTruth(canonical_food=food),
            structured_label=StructuredLabel(
                ingredient_list=[
                    DeclaredIngredient(
                        original_description="Salt",
                        declared_name="SALT",
                        original_code=1,
                        original_fraction=1.0,
                    )
                ]
            ),
        )
        rule = AllergenDeclarationRule()
        result = rule.validate(sample)
        assert result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# Claim Eligibility Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestClaimEligibilityRule:
    """ClaimEligibilityRule tests."""

    def test_no_claims_pass(self, simple_sample: BenchmarkSample) -> None:
        rule = ClaimEligibilityRule()
        result = rule.validate(simple_sample)
        assert result.passed

    def test_invalid_claim_fails(self, simple_sample: BenchmarkSample) -> None:
        """A 'Fat Free' claim on a high-fat food should fail."""
        # Add a "Fat Free" claim to a food with 364 kcal (flour actually has ~1g fat)
        # But for test purposes, let's just add a false claim
        fat_ing = CanonicalIngredient(
            ingredient_code=4, description="Oil", weight_g=100.0, fraction=1.0, sequence_number=1
        )
        fat_food = CanonicalFood(
            fdc_id=5,
            food_name="Oil",
            ingredients=[fat_ing],
            nutrients=[
                NutrientValue(nutrient_id=1004, name="Total lipid (fat)", amount=100.0, unit="g"),
            ],
        )
        sample = BenchmarkSample(
            metadata=SampleMetadata(sample_id="oil"),
            canonical_food=fat_food,
            ground_truth=GroundTruth(canonical_food=fat_food),
            structured_label=StructuredLabel(
                product_name="OIL",
                claims=[ClaimDeclaration(claim_text="FAT FREE", claim_type="nutrient_content")],
            ),
        )
        rule = ClaimEligibilityRule()
        result = rule.validate(sample)
        assert not result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# Nutrition Facts Consistency Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestNutritionFactsConsistencyRule:
    """NutritionFactsConsistencyRule tests."""

    def test_no_nf_fails(self, simple_sample: BenchmarkSample) -> None:
        rule = NutritionFactsConsistencyRule()
        result = rule.validate(simple_sample)
        assert not result.passed

    def test_consistent_nf(self) -> None:
        """Calories should match Energy nutrient per serving."""
        ing = CanonicalIngredient(
            ingredient_code=1, description="Sugar", weight_g=100.0, fraction=1.0, sequence_number=1
        )
        food = CanonicalFood(
            fdc_id=6,
            food_name="Sugar",
            ingredients=[ing],
            canonical_serving=CanonicalServing(serving_size_g=100.0),
            nutrients=[NutrientValue(nutrient_id=1008, name="Energy", amount=387.0, unit="kcal")],
        )
        nf = NutritionFactsPanel(
            serving_size="100g",
            calories=387,
            total_fat=0.0,
            sodium=0.0,
            total_carbohydrate=100.0,
            protein=0.0,
        )
        sample = BenchmarkSample(
            metadata=SampleMetadata(sample_id="sugar"),
            canonical_food=food,
            ground_truth=GroundTruth(canonical_food=food),
            structured_label=StructuredLabel(product_name="SUGAR"),
            nutrition_facts_json=nf,
        )
        rule = NutritionFactsConsistencyRule()
        result = rule.validate(sample)
        assert result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# Prohibited Terminology Rule
# ═══════════════════════════════════════════════════════════════════════════════


class TestProhibitedTerminologyRule:
    """ProhibitedTerminologyRule tests."""

    def test_clean_label(self, simple_sample: BenchmarkSample) -> None:
        rule = ProhibitedTerminologyRule()
        result = rule.validate(simple_sample)
        assert result.passed  # no prohibited terms

    def test_natural_term_fails(self, simple_sample: BenchmarkSample) -> None:
        simple_sample.rendered_label_text = "100% NATURAL ingredients"
        rule = ProhibitedTerminologyRule()
        result = rule.validate(simple_sample)
        assert not result.passed
