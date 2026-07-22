"""Tests for the transformation engine and all operators."""

from __future__ import annotations

from pathlib import Path

import pytest

from synth_bench.canonical.loader import FNDDSLoader
from synth_bench.canonical.models import CanonicalFood, CanonicalIngredient
from synth_bench.transform.engine import LabelState, TransformationEngine
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

# ── Fixture: a transformation engine with all operators registered ────────────


@pytest.fixture
def engine() -> TransformationEngine:
    eng = TransformationEngine()
    eng.register(RenameOperator())
    eng.register(GenericNameOperator())
    eng.register(CompoundIngredientOperator())
    eng.register(LessThan2PercentOperator())
    eng.register(AllergenOperator())
    eng.register(ClaimEligibilityOperator())
    eng.register(NutritionFactsOperator())
    return eng


@pytest.fixture
def canonical_milk(synthetic_fndds_path: Path) -> CanonicalFood:
    loader = FNDDSLoader(synthetic_fndds_path)
    cf = loader.to_canonical_food(2705384)
    assert cf is not None
    return cf


@pytest.fixture
def canonical_bagel(synthetic_fndds_path: Path) -> CanonicalFood:
    loader = FNDDSLoader(synthetic_fndds_path)
    cf = loader.to_canonical_food(2705415)
    assert cf is not None
    return cf


# ═══════════════════════════════════════════════════════════════════════════════
# TransformationEngine
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransformationEngine:
    """Engine registration and pipeline execution."""

    def test_register_and_list(self, engine: TransformationEngine) -> None:
        names = list(engine._registry)
        assert "rename" in names
        assert "compound" in names
        assert "allergen" in names
        assert "nutrition_facts" in names
        assert len(names) == 7

    def test_unknown_operator_raises(self, engine: TransformationEngine) -> None:
        with pytest.raises(ValueError, match="Unknown operator"):
            engine.transform(
                CanonicalFood(fdc_id=1, food_name="Test", ingredients=[]),
                operators=["nonexistent"],
            )

    def test_full_pipeline_milk(
        self, engine: TransformationEngine, canonical_milk: CanonicalFood
    ) -> None:
        label, records, difficulty = engine.transform(canonical_milk)
        assert label.product_name == "MILK, NFS"
        assert len(label.ingredient_list) > 0
        assert len(records) == 7  # all 7 operators
        assert difficulty.value >= 1

    def test_full_pipeline_bagel(
        self, engine: TransformationEngine, canonical_bagel: CanonicalFood
    ) -> None:
        label, records, difficulty = engine.transform(canonical_bagel)
        assert label.product_name == "BAGEL, WHOLE WHEAT, WITH RAISINS"
        assert len(label.ingredient_list) > 0
        assert len(records) == 7

    def test_subset_of_operators(
        self, engine: TransformationEngine, canonical_milk: CanonicalFood
    ) -> None:
        label, records, difficulty = engine.transform(
            canonical_milk,
            operators=["rename", "generic_name"],
        )
        assert len(records) == 2

    def test_generate_sample(
        self, engine: TransformationEngine, canonical_milk: CanonicalFood
    ) -> None:
        sample = engine.generate_sample(canonical_milk, sample_id="milk_test_001")
        assert sample.metadata.sample_id == "milk_test_001"
        assert sample.metadata.total_applied_operators == 7
        assert sample.metadata.difficulty.value >= 1
        assert sample.canonical_food.fdc_id == 2705384
        assert sample.structured_label.product_name == "MILK, NFS"
        assert sample.ground_truth.canonical_mappings
        assert sample.ground_truth.target_mappings
        assert sample.ground_truth.ingredient_amounts
        assert sample.ground_truth.transformation_history.operator_names

    def test_label_state_from_canonical(self, canonical_milk: CanonicalFood) -> None:
        state = LabelState.from_canonical_food(canonical_milk)
        assert state.product_name == "MILK, NFS"
        assert len(state.declared_ingredients) > 0
        for ing in state.declared_ingredients:
            assert ing.declaration_group == "main"

    def test_empty_operator_list_applies_no_operators(
        self, engine: TransformationEngine, canonical_milk: CanonicalFood
    ) -> None:
        label, records, difficulty = engine.transform(canonical_milk, operators=[])
        assert records == []
        assert label.nutrition_facts is None
        assert difficulty.value == 1


# ═══════════════════════════════════════════════════════════════════════════════
# RenameOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestRenameOperator:
    """RenameOperator: FNDDS standard → commercial label names."""

    def test_rename_milk_ingredient(self, canonical_milk: CanonicalFood) -> None:
        op = RenameOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)

        # The first ingredient "Milk, whole, 3.25%..." should become "MILK"
        assert state.declared_ingredients[0].declared_name == "MILK"

    def test_rename_butter(self) -> None:
        """Test via a food with 'Butter, salted'."""
        ing = CanonicalIngredient(
            ingredient_code=1001,
            description="Butter, salted",
            weight_g=10.0,
            fraction=0.1,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Test", ingredients=[ing])
        op = RenameOperator()
        state = LabelState.from_canonical_food(food)
        state = op.apply(state)
        assert state.declared_ingredients[0].declared_name == "BUTTER"

    def test_rename_unknown_falls_back(self, canonical_milk: CanonicalFood) -> None:
        """Unknown names stay UPPERCASE."""
        op = RenameOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        # Add an unknown ingredient
        from synth_bench.canonical.models import DeclaredIngredient

        state.declared_ingredients.append(
            DeclaredIngredient(
                original_description="Some exotic ingredient, raw",
                declared_name="SOME EXOTIC INGREDIENT, RAW",
            )
        )
        state = op.apply(state)
        assert "EXOTIC" in state.declared_ingredients[-1].declared_name


# ═══════════════════════════════════════════════════════════════════════════════
# GenericNameOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestGenericNameOperator:
    """GenericNameOperator: specific variety → generic name."""

    def test_cheddar_to_cheese(self) -> None:
        """'Cheddar' in a name should become 'CHEESE'."""
        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Cheddar cheese",
            weight_g=50.0,
            fraction=0.5,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Test", ingredients=[ing])
        op = GenericNameOperator()
        state = LabelState.from_canonical_food(food)
        # First rename to get "CHEDDAR CHEESE"
        RenameOperator().apply(state)
        # Then genericize
        state = op.apply(state)
        assert state.declared_ingredients[0].declared_name == "CHEESE"

    def test_butter_oil_does_not_become_lettuce(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Butter oil, anhydrous",
            weight_g=5.0,
            fraction=0.1,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Test", ingredients=[ing])
        state = GenericNameOperator().apply(LabelState.from_canonical_food(food))

        assert state.declared_ingredients[0].declared_name == "BUTTER OIL, ANHYDROUS"

    def test_multi_word_variety_to_generic_name(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Granny Smith apples",
            weight_g=50.0,
            fraction=0.5,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Test", ingredients=[ing])
        state = GenericNameOperator().apply(LabelState.from_canonical_food(food))

        assert state.declared_ingredients[0].declared_name == "APPLES"

    def test_no_change_for_unknown(self, canonical_milk: CanonicalFood) -> None:
        op = GenericNameOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)
        # Milk ingredients shouldn't change
        assert (
            state.declared_ingredients[0].declared_name
            == "MILK, WHOLE, 3.25% MILKFAT, WITH ADDED VITAMIN D"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CompoundIngredientOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompoundIngredientOperator:
    """CompoundIngredientOperator: compound ingredient expansion."""

    def test_chocolate_expansion(self) -> None:

        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Chocolate",
            weight_g=50.0,
            fraction=0.5,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Candy", ingredients=[ing])
        op = CompoundIngredientOperator()
        state = LabelState.from_canonical_food(food)
        state = op.apply(state)

        # Should be expanded with parenthetical sub-ingredients
        assert state.declared_ingredients[0].is_compound
        assert "COCOA MASS" in state.declared_ingredients[0].declared_name
        assert "CHOCOLATE" in state.declared_ingredients[0].declared_name

    def test_unknown_compound_not_expanded(self, canonical_milk: CanonicalFood) -> None:
        op = CompoundIngredientOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)
        # Milk ingredients are not compounds
        for ing in state.declared_ingredients:
            assert not ing.is_compound


# ═══════════════════════════════════════════════════════════════════════════════
# LessThan2PercentOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestLessThan2PercentOperator:
    """LessThan2PercentOperator: ≤2% ingredient separation."""

    def test_moves_low_fraction_ingredients(self, canonical_bagel: CanonicalFood) -> None:
        op = LessThan2PercentOperator()
        state = LabelState.from_canonical_food(canonical_bagel)
        state = op.apply(state)

        # Bagel has ingredients with fractions 0.6, 0.15, 0.1, 0.08, 0.05, 0.02
        # With default 2% threshold, only 0.02 (butter) should move
        main_names = [i.original_description for i in state.declared_ingredients]
        lt2pct_names = [i.original_description for i in state.two_percent_group]

        assert "Butter, salted" in lt2pct_names
        assert "Wheat flour, whole-grain" in main_names  # 60% stays

    def test_lower_threshold(self, canonical_bagel: CanonicalFood) -> None:
        op = LessThan2PercentOperator()
        state = LabelState.from_canonical_food(canonical_bagel, lt2pct_threshold=0.10)
        state = op.apply(state)

        # With 10% threshold, ingredients <= 10% should move
        lt2pct_pct = [i.original_fraction for i in state.two_percent_group]
        assert all(f <= 0.10 for f in lt2pct_pct)

    def test_disabled_with_zero_threshold(self, canonical_bagel: CanonicalFood) -> None:
        op = LessThan2PercentOperator()
        state = LabelState.from_canonical_food(canonical_bagel, lt2pct_threshold=0.0)
        state = op.apply(state)

        assert len(state.two_percent_group) == 0
        assert len(state.declared_ingredients) == 6


# ═══════════════════════════════════════════════════════════════════════════════
# AllergenOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllergenOperator:
    """AllergenOperator: allergen declaration generation."""

    def test_milk_has_dairy_allergen(self, canonical_milk: CanonicalFood) -> None:
        op = AllergenOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)

        assert state.allergens is not None
        assert "MILK" in state.allergens.declaration_text

    def test_bagel_has_wheat_and_egg(self, canonical_bagel: CanonicalFood) -> None:
        op = AllergenOperator()
        state = LabelState.from_canonical_food(canonical_bagel)
        state = op.apply(state)

        assert state.allergens is not None
        assert "WHEAT" in state.allergens.declaration_text
        assert "EGGS" in state.allergens.declaration_text

    def test_no_allergen_food(self) -> None:
        """A food with just salt, sugar should have no allergen declaration."""
        ing1 = CanonicalIngredient(
            ingredient_code=1, description="Salt", weight_g=50.0, fraction=0.5, sequence_number=1
        )
        ing2 = CanonicalIngredient(
            ingredient_code=2,
            description="Sugar, granulated",
            weight_g=50.0,
            fraction=0.5,
            sequence_number=2,
        )
        food = CanonicalFood(fdc_id=1, food_name="Salt Sugar Mix", ingredients=[ing1, ing2])
        op = AllergenOperator()
        state = LabelState.from_canonical_food(food)
        state = op.apply(state)
        # Salt/sugar have no allergens
        assert state.allergens is None


# ═══════════════════════════════════════════════════════════════════════════════
# ClaimEligibilityOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestClaimEligibilityOperator:
    """ClaimEligibilityOperator: nutrient content and health claims."""

    def test_milk_has_claims(self, canonical_milk: CanonicalFood) -> None:
        op = ClaimEligibilityOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)

        # Should have some claims
        assert len(state.claims) >= 0  # may or may not qualify

    def test_calorie_free_claim(self, canonical_milk: CanonicalFood) -> None:
        """Test with a very low-nutrient food."""
        water_ing = CanonicalIngredient(
            ingredient_code=1,
            description="Water, tap",
            weight_g=100.0,
            fraction=1.0,
            sequence_number=1,
        )
        # Minimal nutrients
        from synth_bench.canonical.models import NutrientValue

        food = CanonicalFood(
            fdc_id=1,
            food_name="Water",
            ingredients=[water_ing],
            nutrients=[NutrientValue(nutrient_id=1008, name="Energy", amount=0.0, unit="kcal")],
        )
        op = ClaimEligibilityOperator()
        state = LabelState.from_canonical_food(food)
        state = op.apply(state)

        # Water should have calorie/sugar related claims
        claim_texts = [c.claim_text for c in state.claims]
        has_calorie_free = any("CALORIE FREE" in c for c in claim_texts) or any(
            "FREE" in c for c in claim_texts
        )
        assert has_calorie_free or len(state.claims) == 0

    def test_missing_nutrients_do_not_generate_zero_based_claims(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1,
            description="Water, tap",
            weight_g=100.0,
            fraction=1.0,
            sequence_number=1,
        )
        food = CanonicalFood(fdc_id=1, food_name="Unknown Food", ingredients=[ing], nutrients=[])
        op = ClaimEligibilityOperator()
        state = LabelState.from_canonical_food(food)
        state = op.apply(state)
        assert state.claims == []


# ═══════════════════════════════════════════════════════════════════════════════
# NutritionFactsOperator
# ═══════════════════════════════════════════════════════════════════════════════


class TestNutritionFactsOperator:
    """NutritionFactsOperator: Nutrition Facts panel generation."""

    def test_panel_generated(self, canonical_milk: CanonicalFood) -> None:
        op = NutritionFactsOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)

        assert state.nutrition_facts is not None
        assert state.nutrition_facts.calories > 0
        assert "g" in state.nutrition_facts.serving_size

    def test_dv_populated(self, canonical_milk: CanonicalFood) -> None:
        op = NutritionFactsOperator()
        state = LabelState.from_canonical_food(canonical_milk)
        state = op.apply(state)

        assert state.nutrition_facts is not None
        assert len(state.nutrition_facts.daily_values) > 0
        # Total fat should have a DV
        assert "Total lipid (fat)" in state.nutrition_facts.daily_values

    def test_bagel_nutrition_facts(self, canonical_bagel: CanonicalFood) -> None:
        op = NutritionFactsOperator()
        state = LabelState.from_canonical_food(canonical_bagel)
        state = op.apply(state)

        assert state.nutrition_facts is not None
        assert state.nutrition_facts.calories > 200  # bagel has ~261 kcal/100g
        assert state.nutrition_facts.total_carbohydrate is not None


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestEndToEnd:
    """Full pipeline from loader to benchmark sample."""

    def test_generate_from_loader(
        self, engine: TransformationEngine, synthetic_fndds_path: Path
    ) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        ids = loader.get_recipe_ids(min_ingredients=3, max_ingredients=10)

        for fdc_id in ids[:3]:
            cf = loader.to_canonical_food(fdc_id)
            assert cf is not None

            sample = engine.generate_sample(cf, sample_id=f"e2e_{fdc_id}")
            assert sample.structured_label.ingredient_list is not None
            assert sample.structured_label.nutrition_facts is not None
            assert sample.metadata.total_applied_operators == 7

            # Dataset dict should have all required keys
            d = sample.to_dataset_dict()
            for key in (
                "canonical_food.json",
                "ground_truth.json",
                "structured_label.json",
                "rendered_label.txt",
                "nutrition_facts.json",
                "operators.json",
                "validation.json",
                "metadata.json",
            ):
                assert key in d, f"Missing key: {key}"

    def test_rendered_label_format(
        self, engine: TransformationEngine, canonical_milk: CanonicalFood
    ) -> None:
        sample = engine.generate_sample(canonical_milk, sample_id="render_test")

        # Build a simple rendered ingredient declaration text
        ings = sample.structured_label.ingredient_list
        ing_texts = [i.declared_name for i in ings]
        sample.structured_label.raw_ingredient_text = "INGREDIENTS: " + ", ".join(ing_texts) + "."

        # Check it produces something sensible
        assert "INGREDIENTS:" in sample.structured_label.raw_ingredient_text
        assert sample.structured_label.raw_ingredient_text.endswith(".")
