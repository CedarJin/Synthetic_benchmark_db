"""Tests for the core canonical data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from synth_bench.canonical.models import (
    BenchmarkSample,
    CanonicalFood,
    CanonicalIngredient,
    DifficultyLevel,
    GroundTruth,
    MappingEntry,
    NutritionFactsPanel,
    OperatorRecord,
    SampleMetadata,
    StructuredLabel,
)


class TestCanonicalIngredient:
    """CanonicalIngredient model validation."""

    def test_minimal(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1001,
            description="Flour",
            weight_g=50.0,
            fraction=0.5,
            sequence_number=1,
        )
        assert ing.description == "Flour"
        assert ing.fraction == 0.5
        assert not ing.is_fortificant
        assert not ing.is_compound

    def test_negative_fraction_raises(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalIngredient(
                ingredient_code=1001,
                description="Bad",
                weight_g=-1.0,
                fraction=-0.1,
                sequence_number=0,
            )

    def test_fraction_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalIngredient(
                ingredient_code=1001,
                description="Bad",
                weight_g=200.0,
                fraction=1.5,
                sequence_number=0,
            )

    def test_fortificant_flag(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=999328,
            description="Vitamin D as ingredient",
            weight_g=0.01,
            fraction=0.0001,
            sequence_number=5,
            is_fortificant=True,
        )
        assert ing.is_fortificant


class TestCanonicalFood:
    """CanonicalFood model validation."""

    def test_minimal(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1001, description="Flour",
            weight_g=100.0, fraction=1.0, sequence_number=1,
        )
        food = CanonicalFood(
            fdc_id=12345,
            food_name="Test Bread",
            ingredients=[ing],
        )
        assert food.fdc_id == 12345
        assert len(food.ingredients) == 1
        assert food.canonical_serving.serving_size_g == 100.0  # default

    def test_default_serving(self) -> None:
        ing = CanonicalIngredient(
            ingredient_code=1001, description="Salt",
            weight_g=100.0, fraction=1.0, sequence_number=1,
        )
        food = CanonicalFood(
            fdc_id=99999,
            food_name="Salt Only",
            ingredients=[ing],
        )
        assert food.canonical_serving.serving_size_g == 100.0

    def test_full_construction(self, sample_canonical_food: CanonicalFood) -> None:
        cf = sample_canonical_food
        assert len(cf.ingredients) == 2
        assert len(cf.nutrients) == 1
        assert cf.nutrients[0].name == "Energy"


class TestGroundTruth:
    """GroundTruth model."""

    def test_minimal(self, sample_canonical_food: CanonicalFood) -> None:
        gt = GroundTruth(canonical_food=sample_canonical_food)
        assert gt.canonical_food.fdc_id == 99999
        assert len(gt.canonical_mappings) == 0

    def test_with_mappings(self, sample_canonical_food: CanonicalFood) -> None:
        gt = GroundTruth(
            canonical_food=sample_canonical_food,
            canonical_mappings=[
                MappingEntry(
                    source_text="Butter, salted",
                    target_id="01145",
                    target_namespace="usda_sr_legacy",
                ),
            ],
            ingredient_fractions={"Butter, salted": 0.2, "Sugar, granulated": 0.8},
        )
        assert len(gt.canonical_mappings) == 1
        assert gt.ingredient_fractions["Butter, salted"] == 0.2


class TestBenchmarkSample:
    """Full BenchmarkSample model."""

    def test_minimal(self, sample_benchmark_sample: BenchmarkSample) -> None:
        bs = sample_benchmark_sample
        assert bs.metadata.sample_id == "test_001"
        assert bs.canonical_food.food_name == "Test Food"
        assert bs.rendered_label_text == "INGREDIENTS: BUTTER, SUGAR."

    def test_to_dataset_dict(self, sample_benchmark_sample: BenchmarkSample) -> None:
        d = sample_benchmark_sample.to_dataset_dict()
        assert "canonical_food.json" in d
        assert "ground_truth.json" in d
        assert "structured_label.json" in d
        assert "rendered_label.txt" in d
        assert d["rendered_label.txt"] == "INGREDIENTS: BUTTER, SUGAR."
        assert "metadata.json" in d
        assert d["metadata.json"]["sample_id"] == "test_001"

    def test_nutrition_facts_in_output(self, sample_canonical_food) -> None:
        nf = NutritionFactsPanel(
            serving_size="1 cup (240ml)",
            calories=150,
            total_fat=3.0,
            sodium=120,
            total_carbohydrate=30.0,
            protein=5.0,
        )
        bs = BenchmarkSample(
            metadata=SampleMetadata(sample_id="test_nf"),
            canonical_food=sample_canonical_food,
            ground_truth=GroundTruth(canonical_food=sample_canonical_food),
            structured_label=StructuredLabel(product_name="NF TEST"),
            nutrition_facts_json=nf,
        )
        d = bs.to_dataset_dict()
        assert d["nutrition_facts.json"]["calories"] == 150

    def test_difficulty_default(self) -> None:
        assert DifficultyLevel.EASY == 1
        assert DifficultyLevel.HARD == 3


class TestOperatorRecord:
    """OperatorRecord model."""

    def test_minimal(self) -> None:
        op = OperatorRecord(
            operator_name="RenameOperator",
            applied_ingredients=["Butter, salted"],
        )
        assert op.operator_name == "RenameOperator"
        assert op.operator_version == "1.0"  # default
