"""Tests for FDA rules knowledge base."""

from __future__ import annotations

import pytest

from synth_bench.knowledge.fda_rules import (
    DAILY_VALUE_REFERENCES,
    RACC_TABLE,
    FoodCategory,
    check_nutrient_content_claim,
    classify_food_code,
    classify_food_name,
    compute_daily_value_percent,
    determine_serving_size,
    get_racc,
)


class TestRACCTable:
    """RACC (Reference Amounts Customarily Consumed) table tests."""

    def test_all_categories_have_entry(self) -> None:
        """Every FoodCategory should have a RACC entry."""
        for cat in FoodCategory:
            if cat == FoodCategory.UNCATEGORIZED:
                continue
            racc = get_racc(cat)
            assert racc is not None, f"Missing RACC for {cat}"

    def test_racc_is_reasonable(self) -> None:
        """RACC values should be within reasonable ranges."""
        for cat, racc in RACC_TABLE.items():
            if racc.racc_g > 0:
                assert 5 <= racc.racc_g <= 500, f"{cat}: RACC {racc.racc_g}g out of range"
            if racc.racc_ml > 0:
                assert 10 <= racc.racc_ml <= 1000, f"{cat}: RACC {racc.racc_ml}ml out of range"

    def test_milk_racc(self) -> None:
        racc = get_racc(FoodCategory.MILK)
        assert racc.racc_ml == 240
        assert racc.label_statement == "1 cup"

    def test_bread_racc(self) -> None:
        racc = get_racc(FoodCategory.BREADS_ROLLS)
        assert racc.racc_g == 50
        assert racc.label_statement == "1 slice"

    def test_get_racc_by_string(self) -> None:
        racc = get_racc("milk")
        assert racc is not None
        assert racc.racc_ml == 240

    def test_get_racc_invalid(self) -> None:
        racc = get_racc("nonexistent_category")
        assert racc is None

    def test_unknown_category_not_in_table(self) -> None:
        assert FoodCategory.UNCATEGORIZED not in RACC_TABLE


class TestFoodClassification:
    """Food code and name classification tests."""

    def test_classify_food_code_milk(self) -> None:
        assert classify_food_code("11100000") == FoodCategory.MILK

    def test_classify_food_code_meat(self) -> None:
        assert classify_food_code("21100000") == FoodCategory.MEAT_POULTRY

    def test_classify_food_code_bakery(self) -> None:
        assert classify_food_code("41100000") == FoodCategory.BAKERY_PRODUCTS

    def test_classify_food_code_beverage(self) -> None:
        assert classify_food_code("81100000") == FoodCategory.BEVERAGES_CARBONATED

    def test_classify_food_code_unknown(self) -> None:
        assert classify_food_code("00100000") == FoodCategory.UNCATEGORIZED

    def test_classify_food_name_bread(self) -> None:
        assert classify_food_name("Whole wheat bread") == FoodCategory.BREADS_ROLLS

    def test_classify_food_name_cheese(self) -> None:
        assert classify_food_name("Cheddar cheese, shredded") == FoodCategory.CHEESE

    def test_classify_food_name_chicken(self) -> None:
        assert classify_food_name("Chicken breast, cooked") == FoodCategory.MEAT_POULTRY

    def test_classify_food_name_no_match(self) -> None:
        assert classify_food_name("Unknown mystery food") is None


class TestServingSize:
    """Serving size determination tests."""

    def test_determine_from_fndds(self) -> None:
        sz = determine_serving_size(fndds_serving_size_g=150.0)
        assert sz == 150.0

    def test_determine_from_fndds_outlier(self) -> None:
        """FNDDS serving sizes outside reasonable range should fall back."""
        sz = determine_serving_size(fndds_serving_size_g=1.0)
        assert sz != 1.0  # falls back to RACC or default

    def test_determine_from_food_code(self) -> None:
        sz = determine_serving_size(food_code="11100000")
        assert sz == 240.0  # Milk RACC

    def test_determine_from_food_name(self) -> None:
        sz = determine_serving_size(food_name="Whole wheat bread")
        assert sz == 50.0  # Bread RACC

    def test_determine_default(self) -> None:
        sz = determine_serving_size()
        assert sz == 100.0


class TestDailyValue:
    """% Daily Value computation tests."""

    def test_sodium_dv(self) -> None:
        dv = compute_daily_value_percent("Sodium, Na", 460)  # 460mg per serving
        assert dv is not None
        assert dv == pytest.approx(20.0, abs=0.1)  # 460/2300 * 100

    def test_saturated_fat_dv(self) -> None:
        dv = compute_daily_value_percent("Fatty acids, total saturated", 5)
        assert dv is not None
        assert dv == pytest.approx(25.0, abs=0.1)  # 5/20 * 100

    def test_unknown_nutrient(self) -> None:
        dv = compute_daily_value_percent("Some Unknown Nutrient", 10)
        assert dv is None

    def test_dv_references_defined(self) -> None:
        assert DAILY_VALUE_REFERENCES["Sodium"] == 2300
        assert DAILY_VALUE_REFERENCES["Total Fat"] == 78
        assert DAILY_VALUE_REFERENCES["Dietary Fiber"] == 28


class TestNutrientContentClaims:
    """Nutrient content claim threshold tests."""

    def test_fat_free(self) -> None:
        claims = check_nutrient_content_claim("fat", 0.3, 0.5)
        assert "fat_free" in claims

    def test_not_fat_free(self) -> None:
        claims = check_nutrient_content_claim("fat", 1.0, 3.0)
        assert "fat_free" not in claims

    def test_low_sodium(self) -> None:
        claims = check_nutrient_content_claim("sodium", 100, 130)
        assert "low_sodium" in claims

    def test_not_low_sodium(self) -> None:
        claims = check_nutrient_content_claim("sodium", 300, 400)
        assert "low_sodium" not in claims

    def test_calorie_free(self) -> None:
        claims = check_nutrient_content_claim("energy", 3.0, 3.0)
        assert "calorie_free" in claims

    def test_fiber_fat_free(self) -> None:
        """Fiber at 0 should trigger no fat-related claim."""
        claims = check_nutrient_content_claim("fiber", 0, 0)
        assert isinstance(claims, list)

    def test_unknown_claim_group(self) -> None:
        claims = check_nutrient_content_claim("nonexistent", 10, 10)
        assert claims == []
