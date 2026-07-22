"""Tests for the FNDDSLoader (with synthetic fixture)."""

from __future__ import annotations

from pathlib import Path

import pytest

from synth_bench.canonical.loader import FNDDSLoader


class TestFNDDSLoader:
    """FNDDSLoader with the synthetic fixture."""

    def test_load_synthetic_fixture(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        assert loader.is_loaded
        assert len(loader) == 2  # 2 foods in fixture

    def test_require_loaded_raises(self) -> None:
        loader = FNDDSLoader()
        with pytest.raises(RuntimeError, match="not loaded"):
            loader.get_recipe_ids()

    def test_get_recipe_ids_filter(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        # All recipes
        all_ids = loader.get_recipe_ids(min_ingredients=1)
        assert len(all_ids) == 2

        # ≥4 ingredients
        ids_ge_4 = loader.get_recipe_ids(min_ingredients=4)
        assert len(ids_ge_4) == 2  # both have 4+ ingredients

        # ≥5 ingredients
        ids_ge_5 = loader.get_recipe_ids(min_ingredients=5)
        assert len(ids_ge_5) == 1  # only bagel has 6

        # ≥7 ingredients
        ids_ge_7 = loader.get_recipe_ids(min_ingredients=7)
        assert len(ids_ge_7) == 0

    def test_sample_recipes(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        sampled = loader.sample_recipes(n=2, min_ingredients=2, seed=42)
        assert len(sampled) == 2
        assert all(isinstance(i, int) for i in sampled)

    def test_sample_too_many_raises(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        with pytest.raises(ValueError, match="cannot sample"):
            loader.sample_recipes(n=99, min_ingredients=2)

    def test_to_canonical_food_milk(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        cf = loader.to_canonical_food(2705384)
        assert cf is not None
        assert cf.fdc_id == 2705384
        assert cf.food_code == "11100000"
        assert cf.food_name == "Milk, NFS"
        assert len(cf.ingredients) == 4

        # Check first ingredient
        ing = cf.ingredients[0]
        assert ing.description == "Milk, whole, 3.25% milkfat, with added vitamin D"
        assert ing.ingredient_code == 1077
        assert ing.weight_g == 40.0
        assert ing.fraction == pytest.approx(0.4, abs=0.01)
        assert ing.sequence_number == 1

        # Check nutrients
        assert len(cf.nutrients) == 5
        energy = next(n for n in cf.nutrients if n.name == "Energy")
        assert energy.nutrient_id == 1008
        assert energy.amount == 52.0

        # Check serving
        assert cf.canonical_serving.serving_size_g == 2.5
        assert cf.canonical_serving.serving_size_label == "TSP"

    def test_to_canonical_food_bagel(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        cf = loader.to_canonical_food(2705415)
        assert cf is not None
        assert cf.food_name == "Bagel, whole wheat, with raisins"
        assert len(cf.ingredients) == 6

        # Check total fraction sums to ~1.0
        total_frac = sum(ing.fraction for ing in cf.ingredients)
        assert total_frac == pytest.approx(1.0, abs=0.01)

    def test_to_canonical_food_missing(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        cf = loader.to_canonical_food(99999999)
        assert cf is None

    def test_to_canonical_foods_multiple(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        result = loader.to_canonical_foods([2705384, 2705415])
        assert len(result) == 2
        assert 2705384 in result
        assert 2705415 in result

    def test_recipe_statistics(self, synthetic_fndds_path: Path) -> None:
        loader = FNDDSLoader(synthetic_fndds_path)
        stats = loader.recipe_statistics()
        assert stats["total_foods"] == 2
        assert stats["recipes_with_ingredients"] == 2
        assert stats["recipes_ge_2_ingredients"] == 2
        assert stats["recipes_ge_5_ingredients"] == 1
