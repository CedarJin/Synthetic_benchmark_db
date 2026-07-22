"""Tests for ingredient knowledge base."""

from __future__ import annotations

import pytest

from synth_bench.knowledge.ingredient_knowledge import (
    COMPOUND_INGREDIENTS,
    STANDARD_TO_COMMERCIAL,
    classify_ingredient,
    detect_allergens,
    expand_compound,
    lookup_commercial_name,
    make_generic,
)


class TestCommercialNames:
    """Standard → commercial name mapping tests."""

    def test_lookup_milk(self) -> None:
        result = lookup_commercial_name("Milk, whole, 3.25% milkfat, with added vitamin D")
        assert result == "MILK"

    def test_lookup_flour(self) -> None:
        result = lookup_commercial_name("Wheat flour, all-purpose, enriched, bleached")
        assert result == "ENRICHED WHEAT FLOUR"

    def test_lookup_sugar(self) -> None:
        result = lookup_commercial_name("Sugar, granulated")
        assert result == "SUGAR"

    def test_lookup_unknown_falls_back(self) -> None:
        """Unknown names should fall back to UPPERCASE of the original."""
        result = lookup_commercial_name("Some exotic ingredient, raw")
        assert result == "SOME EXOTIC INGREDIENT, RAW"

    def test_lookup_egg(self) -> None:
        result = lookup_commercial_name("Egg, whole, raw")
        assert result == "EGGS"

    def test_lookup_butter(self) -> None:
        assert lookup_commercial_name("Butter, salted") == "BUTTER"

    def test_all_entries_have_commercial_name(self) -> None:
        """Every mapping should produce a non-empty, upper case result."""
        for standard, commercial in STANDARD_TO_COMMERCIAL.items():
            assert len(commercial) > 0
            assert commercial.isupper(), f"'{commercial}' should be upper case"


class TestGenericNames:
    """Generic name substitution tests."""

    def test_cheddar_to_cheese(self) -> None:
        assert make_generic("Cheddar") == "CHEESE"

    def test_granny_smith_to_apples(self) -> None:
        assert make_generic("Granny Smith") == "APPLES"

    def test_butter_is_not_generic_lettuce(self) -> None:
        assert make_generic("Butter") == "Butter"

    def test_unknown_returns_original(self) -> None:
        assert make_generic("Some Unique Variety") == "Some Unique Variety"


class TestCompoundIngredients:
    """Compound ingredient expansion tests."""

    def test_chocolate_expansion(self) -> None:
        recipe = expand_compound("Chocolate")
        assert recipe is not None
        names = [ing for ing, _ in recipe]
        assert "cocoa mass" in names
        assert "sugar" in names
        assert "cocoa butter" in names

    def test_chocolate_fractions_sum(self) -> None:
        recipe = expand_compound("Chocolate")
        assert recipe is not None
        total = sum(frac for _, frac in recipe)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_mayonnaise_expansion(self) -> None:
        recipe = expand_compound("Mayonnaise")
        assert recipe is not None
        names = [ing for ing, _ in recipe]
        assert "soybean oil" in names
        assert "egg yolk" in names

    def test_ketchup_expansion(self) -> None:
        recipe = expand_compound("Ketchup")
        assert recipe is not None
        assert sum(f for _, f in recipe) == pytest.approx(1.0, abs=0.01)

    def test_unknown_compound(self) -> None:
        recipe = expand_compound("Unknown Substance XYZ")
        assert recipe is None

    def test_all_compounds_have_valid_fractions(self) -> None:
        """Every compound ingredient should have fractions summing to ~1.0."""
        for name, recipe in COMPOUND_INGREDIENTS.items():
            total = sum(frac for _, frac in recipe)
            assert total == pytest.approx(1.0, abs=0.08), (
                f"Compound '{name}' fractions sum to {total}, expected 1.0"
            )


class TestIngredientClassification:
    """Ingredient category classification tests."""

    def test_milk_is_dairy(self) -> None:
        assert classify_ingredient("Milk, whole") == "dairy"

    def test_cheese_is_dairy(self) -> None:
        assert classify_ingredient("Cheddar cheese") == "dairy"

    def test_flour_is_grain(self) -> None:
        assert classify_ingredient("Wheat flour") == "grain"

    def test_sugar_is_sweetener(self) -> None:
        assert classify_ingredient("Sugar") == "sweetener"

    def test_chicken_is_meat(self) -> None:
        assert classify_ingredient("Chicken breast") == "meat"

    def test_water_is_water(self) -> None:
        assert classify_ingredient("Water") == "water"

    def test_unknown_ingredient(self) -> None:
        assert classify_ingredient("Artificial flavor XY-7") is None


class TestAllergenDetection:
    """Allergen detection tests."""

    def test_dairy_allergen(self) -> None:
        allergens = detect_allergens(["Milk, whole"])
        assert "milk" in allergens

    def test_multiple_allergens(self) -> None:
        allergens = detect_allergens(
            [
                "Milk, whole",
                "Wheat flour",
                "Egg, whole",
            ]
        )
        assert "milk" in allergens
        assert "wheat" in allergens
        assert "eggs" in allergens

    def test_no_allergens(self) -> None:
        allergens = detect_allergens(["Salt", "Water", "Sugar"])
        assert len(allergens) == 0

    def test_derived_ingredients(self) -> None:
        """Whey should trigger 'milk' allergen."""
        allergens = detect_allergens(["Whey protein concentrate"])
        assert "milk" in allergens

    def test_dedup(self) -> None:
        """Multiple same-allergen ingredients should produce unique results."""
        allergens = detect_allergens(
            [
                "Milk, whole",
                "Cheddar cheese",
                "Cream",
            ]
        )
        assert len([a for a in allergens if a == "milk"]) == 1

    def test_sesame_is_major_allergen(self) -> None:
        allergens = detect_allergens(["Sesame seeds"])
        assert "sesame" in allergens

    def test_allergen_word_boundaries(self) -> None:
        assert detect_allergens(["Cream of tartar"]) == []
        assert detect_allergens(["Almond flour"]) == ["tree nuts"]
        assert "tree nuts" not in detect_allergens(["Coconut water"])
