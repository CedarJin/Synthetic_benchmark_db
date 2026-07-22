"""Tests for the label realizer (template-based rendering)."""

from __future__ import annotations

import pytest

from synth_bench.canonical.models import (
    AllergenDeclaration,
    BenchmarkSample,
    CanonicalFood,
    CanonicalIngredient,
    DeclaredIngredient,
    GroundTruth,
    NutritionFactsPanel,
    SampleMetadata,
    StructuredLabel,
)
from synth_bench.llm.realizer import (
    _call_llm,
    _render_ingredient_list,
    _render_nutrition_facts,
    llm_refine_label,
    render_full_label,
    render_sample,
)
from synth_bench.transform.engine import TransformationEngine
from synth_bench.transform.operators.compound import (
    CompoundIngredientOperator,
    LessThan2PercentOperator,
)
from synth_bench.transform.operators.label_ops import (
    AllergenOperator,
    ClaimEligibilityOperator,
    NutritionFactsOperator,
)
from synth_bench.transform.operators.rename import GenericNameOperator, RenameOperator

# ═══════════════════════════════════════════════════════════════════════════════
# _render_ingredient_list
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderIngredientList:
    """Ingredient list text rendering tests."""

    def test_simple_list(self) -> None:
        label = StructuredLabel(
            product_name="BREAD",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Flour",
                    declared_name="WHEAT FLOUR",
                    original_code=1,
                    original_fraction=0.6,
                ),
                DeclaredIngredient(
                    original_description="Water",
                    declared_name="WATER",
                    original_code=2,
                    original_fraction=0.3,
                ),
                DeclaredIngredient(
                    original_description="Salt",
                    declared_name="SALT",
                    original_code=3,
                    original_fraction=0.1,
                ),
            ],
        )
        text = _render_ingredient_list(label)
        assert text.startswith("INGREDIENTS:")
        assert "WHEAT FLOUR" in text
        assert "WATER" in text
        assert "SALT" in text
        assert text.endswith(".")

    def test_with_compound_ingredient(self) -> None:
        label = StructuredLabel(
            product_name="COOKIE",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Chocolate",
                    declared_name="CHOCOLATE (COCOA MASS, SUGAR, COCOA BUTTER)",
                    original_code=1,
                    original_fraction=0.5,
                    is_compound=True,
                    sub_ingredients=["COCOA MASS", "SUGAR", "COCOA BUTTER"],
                ),
                DeclaredIngredient(
                    original_description="Flour",
                    declared_name="FLOUR",
                    original_code=2,
                    original_fraction=0.5,
                ),
            ],
        )
        text = _render_ingredient_list(label)
        assert "CHOCOLATE" in text
        assert "COCOA MASS" in text
        assert "FLOUR" in text

    def test_with_two_percent_group(self) -> None:
        label = StructuredLabel(
            product_name="SPICE MIX",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Salt",
                    declared_name="SALT",
                    original_code=1,
                    original_fraction=0.95,
                ),
            ],
            two_percent_group=[
                DeclaredIngredient(
                    original_description="Spices",
                    declared_name="SPICES",
                    original_code=2,
                    original_fraction=0.03,
                ),
                DeclaredIngredient(
                    original_description="Garlic",
                    declared_name="GARLIC",
                    original_code=3,
                    original_fraction=0.02,
                ),
            ],
        )
        text = _render_ingredient_list(label)
        assert "CONTAINS 2% OR LESS OF:" in text
        assert "SPICES" in text
        assert "GARLIC" in text

    def test_with_allergen_declaration(self) -> None:
        label = StructuredLabel(
            product_name="MILK",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Milk",
                    declared_name="MILK",
                    original_code=1,
                    original_fraction=1.0,
                ),
            ],
            allergens=AllergenDeclaration(
                allergens=["milk"],
                declaration_text="CONTAINS: MILK",
            ),
        )
        text = _render_ingredient_list(label)
        assert "CONTAINS: MILK" in text

    def test_empty_ingredients(self) -> None:
        label = StructuredLabel(product_name="")
        text = _render_ingredient_list(label)
        assert "INGREDIENTS:" in text


# ═══════════════════════════════════════════════════════════════════════════════
# _render_nutrition_facts
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderNutritionFacts:
    """Nutrition Facts text rendering tests."""

    def test_basic_nf(self) -> None:
        nf = NutritionFactsPanel(
            serving_size="1 cup (240ml)",
            calories=150,
            total_fat=8.0,
            sodium=240.0,
            total_carbohydrate=12.0,
            protein=5.0,
        )
        text = _render_nutrition_facts(nf)
        assert "Nutrition Facts" in text
        assert "Serving Size 1 cup (240ml)" in text
        assert "Calories 150" in text
        assert "Total Fat 8.0g" in text
        assert "Sodium 240mg" in text
        assert "Total Carbohydrate 12.0g" in text
        assert "Protein 5.0g" in text

    def test_nf_with_dv(self) -> None:
        nf = NutritionFactsPanel(
            serving_size="100g",
            calories=200,
            total_fat=10.0,
            sodium=400.0,
            total_carbohydrate=30.0,
            protein=8.0,
            daily_values={
                "Total lipid (fat)": 13,
                "Sodium, Na": 17,
                "Carbohydrate, by difference": 11,
                "Protein": 16,
            },
        )
        text = _render_nutrition_facts(nf)
        # DV values should appear
        assert "13%" in text
        assert "17%" in text
        assert "11%" in text

    def test_nf_with_vitamins(self) -> None:
        nf = NutritionFactsPanel(
            serving_size="100g",
            calories=100,
            total_fat=2.0,
            sodium=50.0,
            total_carbohydrate=20.0,
            protein=3.0,
            daily_values={
                "Calcium, Ca": 15,
                "Iron, Fe": 10,
                "Vitamin D (D2 + D3)": 5,
                "Potassium, K": 8,
            },
        )
        text = _render_nutrition_facts(nf)
        assert "Calcium  15%" in text
        assert "Iron  10%" in text
        assert "Vitamin D  5%" in text

    def test_nf_with_servings(self) -> None:
        nf = NutritionFactsPanel(
            serving_size="1 bar (40g)",
            servings_per_container="6",
            calories=120,
            total_fat=4.0,
            sodium=60.0,
            total_carbohydrate=18.0,
            protein=3.0,
        )
        text = _render_nutrition_facts(nf)
        assert "Servings Per Container 6" in text

    def test_nf_with_trans_fat(self) -> None:
        nf = NutritionFactsPanel(
            serving_size="100g",
            calories=300,
            total_fat=15.0,
            saturated_fat=5.0,
            trans_fat=0.5,
            cholesterol=30.0,
            sodium=200.0,
            total_carbohydrate=35.0,
            dietary_fiber=3.0,
            total_sugars=10.0,
            added_sugars=5.0,
            protein=8.0,
        )
        text = _render_nutrition_facts(nf)
        assert "Saturated Fat 5.0g" in text
        assert "Trans Fat 0.5g" in text
        assert "Cholesterol 30mg" in text
        assert "Dietary Fiber 3.0g" in text
        assert "Includes Added Sugars 5.0g" in text


# ═══════════════════════════════════════════════════════════════════════════════
# render_full_label
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderFullLabel:
    """Full label rendering tests."""

    def test_without_nf(self) -> None:
        label = StructuredLabel(
            product_name="SALT",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Salt",
                    declared_name="SALT",
                    original_code=1,
                    original_fraction=1.0,
                ),
            ],
        )
        ing_text, nf_text = render_full_label(label)
        assert "SALT" in ing_text
        assert nf_text is None

    def test_with_nf(self) -> None:
        label = StructuredLabel(
            product_name="JUICE",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Orange juice",
                    declared_name="ORANGE JUICE",
                    original_code=1,
                    original_fraction=1.0,
                ),
            ],
        )
        nf = NutritionFactsPanel(
            serving_size="1 cup (240ml)",
            calories=110,
            total_fat=0.0,
            sodium=0.0,
            total_carbohydrate=26.0,
            protein=2.0,
        )
        ing_text, nf_text = render_full_label(label, nf)
        assert "ORANGE JUICE" in ing_text
        assert nf_text is not None
        assert "Nutrition Facts" in nf_text
        assert "Calories 110" in nf_text

    def test_renders_claims(self) -> None:
        label = StructuredLabel(
            product_name="JUICE",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Orange juice",
                    declared_name="ORANGE JUICE",
                    original_code=1,
                    original_fraction=1.0,
                ),
            ],
        )
        ing_text, _ = render_full_label(label, claims=["LOW SODIUM"])
        assert ing_text.startswith("LOW SODIUM\nINGREDIENTS:")


class TestLLMRefinement:
    """LLM fallback behavior."""

    def test_call_llm_returns_fallback_for_unknown_model(self) -> None:
        assert (
            _call_llm("PROMPT", "unknown", "key", fallback="INGREDIENTS: MILK.")
            == "INGREDIENTS: MILK."
        )

    def test_refinement_does_not_return_prompt_when_sdk_missing(self) -> None:
        result = llm_refine_label(
            "INGREDIENTS: MILK.",
            "Nutrition Facts\nCalories 100",
            api_key="fake",
            model="unknown",
        )
        assert result == "INGREDIENTS: MILK."


# ═══════════════════════════════════════════════════════════════════════════════
# render_sample
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenderSample:
    """Full sample rendering tests."""

    @pytest.fixture
    def sample(self) -> BenchmarkSample:
        ing = CanonicalIngredient(
            ingredient_code=1, description="Flour", weight_g=100.0, fraction=1.0, sequence_number=1
        )
        food = CanonicalFood(fdc_id=1, food_name="Flour", ingredients=[ing])
        label = StructuredLabel(
            product_name="FLOUR",
            ingredient_list=[
                DeclaredIngredient(
                    original_description="Flour",
                    declared_name="WHEAT FLOUR",
                    original_code=1,
                    original_fraction=1.0,
                ),
            ],
        )
        nf = NutritionFactsPanel(
            serving_size="100g",
            calories=364,
            total_fat=1.0,
            sodium=0.0,
            total_carbohydrate=76.0,
            protein=10.0,
        )
        return BenchmarkSample(
            metadata=SampleMetadata(sample_id="flour"),
            canonical_food=food,
            ground_truth=GroundTruth(canonical_food=food),
            structured_label=label,
            nutrition_facts_json=nf,
        )

    def test_render_sets_text_fields(self, sample: BenchmarkSample) -> None:
        result = render_sample(sample)
        assert result.rendered_label_text is not None
        assert "WHEAT FLOUR" in result.rendered_label_text

    def test_render_sets_nf_text(self, sample: BenchmarkSample) -> None:
        result = render_sample(sample)
        assert result.rendered_nutrition_facts is not None
        assert "Nutrition Facts" in result.rendered_nutrition_facts

    def test_render_returns_same_instance(self, sample: BenchmarkSample) -> None:
        result = render_sample(sample)
        assert result is sample  # in-place modification


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: engine → realizer
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Pipeline integration: TransformationEngine → LabelRealizer."""

    # Re-use engine fixture from test_transformation_engine
    @pytest.fixture
    def engine(self) -> TransformationEngine:
        eng = TransformationEngine()
        eng.register(RenameOperator())
        eng.register(GenericNameOperator())
        eng.register(CompoundIngredientOperator())
        eng.register(LessThan2PercentOperator())
        eng.register(AllergenOperator())
        eng.register(ClaimEligibilityOperator())
        eng.register(NutritionFactsOperator())
        return eng

    def test_engine_then_realizer(
        self, synthetic_fndds_path: str, engine: TransformationEngine
    ) -> None:
        """Full flow: load → transform → render."""
        from synth_bench.canonical.loader import FNDDSLoader

        loader = FNDDSLoader(synthetic_fndds_path)
        cf = loader.to_canonical_food(2705384)
        assert cf is not None

        sample = engine.generate_sample(cf, sample_id="int_test")
        result = render_sample(sample)

        assert result.rendered_label_text is not None
        assert result.rendered_nutrition_facts is not None
        assert len(result.rendered_label_text) > 10

    def test_rendered_label_contains_ingredients(self, synthetic_fndds_path, engine) -> None:
        """The rendered label should contain the declared ingredients."""
        from synth_bench.canonical.loader import FNDDSLoader

        loader = FNDDSLoader(synthetic_fndds_path)
        cf = loader.to_canonical_food(2705415)  # bagel
        assert cf is not None

        sample = engine.generate_sample(cf, sample_id="bagel_render")
        result = render_sample(sample)

        # The label text should mention WHEAT FLOUR or similar
        assert len(result.rendered_label_text) > 20
        assert "INGREDIENTS:" in result.rendered_label_text
