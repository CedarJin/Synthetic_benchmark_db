"""pytest fixtures for the Synthetic Benchmark test suite."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from synth_bench.canonical.models import (
    BenchmarkSample,
    CanonicalFood,
    CanonicalIngredient,
    CanonicalServing,
    GroundTruth,
    NutrientValue,
    SampleMetadata,
    StructuredLabel,
)

# ── Tiny synthetic FNDDS subset for fast unit tests ───────────────────────────

_SYNTHETIC_FNDDS: dict[str, Any] = {
    "SurveyFoods": [
        {
            "fdcId": 2705384,
            "foodCode": "11100000",
            "description": "Milk, NFS",
            "foodNutrients": [
                {"nutrient": {"id": 1003, "number": "203", "name": "Protein", "unitName": "g"}, "amount": 3.33},
                {"nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "unitName": "g"}, "amount": 2.14},
                {"nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference", "unitName": "g"}, "amount": 4.83},
                {"nutrient": {"id": 1008, "number": "208", "name": "Energy", "unitName": "kcal"}, "amount": 52.0},
                {"nutrient": {"id": 1093, "number": "307", "name": "Sodium, Na", "unitName": "mg"}, "amount": 42.0},
            ],
            "inputFoods": [
                {"ingredientCode": 1077, "ingredientDescription": "Milk, whole, 3.25% milkfat, with added vitamin D", "ingredientWeight": 40.0, "sequenceNumber": 1, "retentionCode": 0},
                {"ingredientCode": 1079, "ingredientDescription": "Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and vitamin D", "ingredientWeight": 38.0, "sequenceNumber": 2, "retentionCode": 0},
                {"ingredientCode": 1082, "ingredientDescription": "Milk, lowfat, fluid, 1% milkfat, with added vitamin A and vitamin D", "ingredientWeight": 14.0, "sequenceNumber": 3, "retentionCode": 0},
                {"ingredientCode": 1085, "ingredientDescription": "Milk, nonfat, fluid, with added vitamin A and vitamin D (fat free or skim)", "ingredientWeight": 8.0, "sequenceNumber": 4, "retentionCode": 0},
            ],
            "foodPortions": [{"gramWeight": 2.5, "modifier": "TSP", "amount": 1}],
        },
        {
            "fdcId": 2705415,
            "foodCode": "12142000",
            "description": "Bagel, whole wheat, with raisins",
            "foodNutrients": [
                {"nutrient": {"id": 1003, "number": "203", "name": "Protein", "unitName": "g"}, "amount": 8.3},
                {"nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "unitName": "g"}, "amount": 1.4},
                {"nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference", "unitName": "g"}, "amount": 53.7},
                {"nutrient": {"id": 1008, "number": "208", "name": "Energy", "unitName": "kcal"}, "amount": 261.0},
            ],
            "inputFoods": [
                {"ingredientCode": 9199, "ingredientDescription": "Wheat flour, whole-grain", "ingredientWeight": 60.0, "sequenceNumber": 1, "retentionCode": 0},
                {"ingredientCode": 90480, "ingredientDescription": "Raisins, seedless", "ingredientWeight": 15.0, "sequenceNumber": 2, "retentionCode": 0},
                {"ingredientCode": 1123, "ingredientDescription": "Egg, whole, raw", "ingredientWeight": 10.0, "sequenceNumber": 3, "retentionCode": 0},
                {"ingredientCode": 19335, "ingredientDescription": "Sugar, granulated", "ingredientWeight": 8.0, "sequenceNumber": 4, "retentionCode": 0},
                {"ingredientCode": 1450, "ingredientDescription": "Water, tap", "ingredientWeight": 5.0, "sequenceNumber": 5, "retentionCode": 0},
                {"ingredientCode": 1001, "ingredientDescription": "Butter, salted", "ingredientWeight": 2.0, "sequenceNumber": 6, "retentionCode": 0},
            ],
            "foodPortions": [{"gramWeight": 95.0, "modifier": "MEDIUM", "amount": 1}],
        },
    ]
}


@pytest.fixture(scope="session")
def synthetic_fndds_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the synthetic FNDDS fixture to a temp JSON file."""
    path = tmp_path_factory.mktemp("fndds_fixture") / "surveyDownload.json"
    with open(path, "w") as f:
        json.dump(_SYNTHETIC_FNDDS, f)
    return path


# ── Pre-built canonical objects for model tests ───────────────────────────────


@pytest.fixture
def sample_ingredient() -> CanonicalIngredient:
    return CanonicalIngredient(
        ingredient_code=1001,
        description="Butter, salted",
        weight_g=20.0,
        fraction=0.2,
        sequence_number=1,
    )


@pytest.fixture
def sample_canonical_food(sample_ingredient: CanonicalIngredient) -> CanonicalFood:
    return CanonicalFood(
        fdc_id=99999,
        food_code="99999999",
        food_name="Test Food",
        canonical_serving=CanonicalServing(serving_size_g=100.0),
        ingredients=[
            sample_ingredient,
            CanonicalIngredient(
                ingredient_code=1002,
                description="Sugar, granulated",
                weight_g=80.0,
                fraction=0.8,
                sequence_number=2,
            ),
        ],
        nutrients=[
            NutrientValue(nutrient_id=1008, name="Energy", amount=250.0, unit="kcal"),
        ],
    )


@pytest.fixture
def sample_benchmark_sample(
    sample_canonical_food: CanonicalFood,
) -> BenchmarkSample:
    return BenchmarkSample(
        metadata=SampleMetadata(sample_id="test_001"),
        canonical_food=sample_canonical_food,
        ground_truth=GroundTruth(canonical_food=sample_canonical_food),
        structured_label=StructuredLabel(
            product_name="TEST PRODUCT",
            ingredient_list=[],
        ),
        rendered_label_text="INGREDIENTS: BUTTER, SUGAR.",
    )
