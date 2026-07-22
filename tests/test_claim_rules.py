"""Tests for claim and allergen declaration rules."""

from __future__ import annotations

from synth_bench.knowledge.claim_rules import (
    NUTRIENT_CONTENT_CLAIM_TEMPLATES,
    check_health_claims,
    check_source_claims,
    format_allergen_declaration,
    format_nutrient_content_claims,
    format_nutrition_facts_text,
)


class TestAllergenDeclaration:
    """Allergen declaration formatting tests."""

    def test_single_allergen(self) -> None:
        decl = format_allergen_declaration(["Milk, whole"])
        assert decl is not None
        assert "MILK" in decl

    def test_two_allergens(self) -> None:
        decl = format_allergen_declaration(["Milk, whole", "Wheat flour"])
        assert decl is not None
        assert "MILK" in decl
        assert "WHEAT" in decl
        assert "and" in decl

    def test_multiple_allergens(self) -> None:
        decl = format_allergen_declaration([
            "Milk, whole", "Egg, whole", "Wheat flour", "Peanut butter",
        ])
        assert decl is not None
        assert "MILK" in decl
        assert "EGGS" in decl
        assert "WHEAT" in decl
        assert "PEANUTS" in decl

    def test_no_allergens(self) -> None:
        decl = format_allergen_declaration(["Salt", "Water"])
        assert decl is None

    def test_empty_list(self) -> None:
        decl = format_allergen_declaration([])
        assert decl is None


class TestNutrientContentClaims:
    """Nutrient content claim formatting tests."""

    def test_claim_formatting(self) -> None:
        claims = format_nutrient_content_claims(["fat_free", "low_calorie"])
        assert "FAT FREE" in claims
        assert "LOW CALORIE" in claims

    def test_claim_with_percent(self) -> None:
        claims = format_nutrient_content_claims(["reduced_fat"], percent=25)
        assert "25% REDUCED FAT" in claims

    def test_empty_claims(self) -> None:
        assert format_nutrient_content_claims([]) == []

    def test_unknown_claim_id(self) -> None:
        claims = format_nutrient_content_claims(["some_unknown_claim"])
        assert "some_unknown_claim" in claims  # passes through

    def test_templates_defined(self) -> None:
        assert "fat_free" in NUTRIENT_CONTENT_CLAIM_TEMPLATES
        assert "good_source_fiber" in NUTRIENT_CONTENT_CLAIM_TEMPLATES


class TestSourceClaims:
    """Good Source / Excellent Source claim tests."""

    def test_excellent_source(self) -> None:
        """20%+ DV should trigger Excellent Source."""
        claims = check_source_claims({"Calcium, Ca": 400})  # 400/1300 ≈ 30.8%
        assert any("EXCELLENT SOURCE" in c and "CALCIUM" in c for c in claims)

    def test_good_source(self) -> None:
        """10-19% DV should trigger Good Source."""
        claims = check_source_claims({"Calcium, Ca": 150})  # 150/1300 ≈ 11.5%
        assert any("GOOD SOURCE" in c and "CALCIUM" in c for c in claims)

    def test_below_threshold(self) -> None:
        """<10% DV should not trigger any claim."""
        claims = check_source_claims({"Calcium, Ca": 50})  # 50/1300 ≈ 3.8%
        assert not any("SOURCE OF" in c and "CALCIUM" in c for c in claims)

    def test_unknown_nutrient(self) -> None:
        claims = check_source_claims({"Unknown Nutrient": 100})
        assert len(claims) == 0

    def test_sodium_does_not_generate_source_claim(self) -> None:
        claims = check_source_claims({"Sodium, Na": 1000})
        assert not any("SOURCE OF SODIUM" in c for c in claims)

    def test_fat_does_not_generate_source_claim(self) -> None:
        claims = check_source_claims({"Total lipid (fat)": 50})
        assert not any("SOURCE OF TOTAL LIPID" in c for c in claims)

    def test_vitamin_d_display_name(self) -> None:
        claims = check_source_claims({"Vitamin D (D2 + D3)": 4})
        assert any("SOURCE OF VITAMIN D" in c for c in claims)


class TestHealthClaims:
    """Health claim eligibility tests."""

    def test_low_sodium_hypertension_claim(self) -> None:
        claims = check_health_claims({"Sodium, Na": 100})
        assert any("low in sodium" in c.lower() for c in claims)

    def test_high_sodium_no_claim(self) -> None:
        claims = check_health_claims({"Sodium, Na": 500})
        assert not any("low in sodium" in c.lower() for c in claims)

    def test_high_calcium_osteoporosis_claim(self) -> None:
        claims = check_health_claims({"Calcium, Ca": 300})
        assert any("calcium" in c.lower() for c in claims)

    def test_no_applicable_claims(self) -> None:
        claims = check_health_claims({
            "Calcium, Ca": 0,
            "Sodium, Na": 300,
            "Total lipid (fat)": 10,  # above 6.5g threshold
            "Fatty acids, total saturated": 5,  # above 4g threshold
            "Fiber, total dietary": 0,
            "Potassium, K": 0,
        })
        # 300mg sodium is not low (<140), 0 calcium is not high (>200),
        # 10g fat is not low (<6.5), 5g sat fat is not low (<4)
        assert len(claims) == 0


class TestNutritionFactsText:
    """Nutrition Facts text formatting tests."""

    def test_basic_format(self) -> None:
        text = format_nutrition_facts_text(
            serving_size_text="1 cup (240ml)",
            calories=150,
            nutrient_lines=[
                "Total Fat 8g",
                "Sodium 240mg  10%",
                "Total Carbohydrate 12g  4%",
                "Protein 5g",
            ],
        )
        assert "Nutrition Facts" in text
        assert "Serving Size 1 cup (240ml)" in text
        assert "Calories 150" in text
        assert "Total Fat 8g" in text
        assert "2,000 calories" in text
