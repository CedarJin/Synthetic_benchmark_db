"""FNDDS data loader — wraps nusol FNDDSDataAdapter to produce CanonicalFood objects.

This module provides the bridge between the NuSol-T FNDDS data adapter
(which handles raw USDA JSON) and our synthetic benchmark's canonical
representation (``CanonicalFood``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from nusol.data.fndds import FNDDSDataAdapter

from synth_bench.canonical.models import (
    CanonicalFood,
    CanonicalIngredient,
    CanonicalServing,
    NutrientValue,
)

FORTIFICANT_CODES: frozenset[str] = frozenset({
    "999301", "999303", "999328", "999401",
    "999431", "999418", "999001", "999291",
})


class FNDDSLoader:
    """Loads FNDDS data and converts to canonical representations.

    Args:
        fndds_path: Path to the FNDDS JSON file (surveyDownload.json).
        config: Optional configuration dict.
    """

    def __init__(
        self,
        fndds_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._config = config or {}
        self._adapter = FNDDSDataAdapter(config)
        self._loaded = False
        self._fndds_path: Path | None = None
        if fndds_path is not None:
            self.load(fndds_path)

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self, fndds_path: str | Path) -> None:
        """Load FNDDS JSON data from disk.

        Args:
            fndds_path: Path to surveyDownload.json or equivalent FNDDS JSON.
        """
        self._fndds_path = Path(fndds_path)
        self._adapter.load(fndds_path)
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def require_loaded(self) -> None:
        """Raise RuntimeError if no data has been loaded."""
        if not self._loaded:
            raise RuntimeError(
                "FNDDS data not loaded. Call .load(path) or pass fndds_path to the constructor."
            )

    # ── Recipe discovery ──────────────────────────────────────────────────────

    def get_recipe_ids(
        self,
        min_ingredients: int = 2,
        max_ingredients: int = 50,
    ) -> list[int]:
        """Return FDC IDs filtered by ingredient count.

        Args:
            min_ingredients: Minimum number of ingredients (default 2).
            max_ingredients: Maximum number of ingredients (default 50).

        Returns:
            List of FDC IDs matching the criteria.
        """
        self.require_loaded()
        return self._adapter.get_recipes_with_ingredients(
            min_ingredients=min_ingredients,
            max_ingredients=max_ingredients,
        )

    def sample_recipes(
        self,
        n: int,
        min_ingredients: int = 2,
        max_ingredients: int = 50,
        seed: int = 42,
    ) -> list[int]:
        """Sample N recipe IDs from the available pool.

        Args:
            n: Number of recipes to sample.
            min_ingredients: Minimum ingredient filter.
            max_ingredients: Maximum ingredient filter.
            seed: Random seed for reproducibility.

        Returns:
            List of N sampled FDC IDs.
        """
        all_ids = self.get_recipe_ids(
            min_ingredients=min_ingredients,
            max_ingredients=max_ingredients,
        )
        if len(all_ids) < n:
            raise ValueError(
                f"Only {len(all_ids)} recipes match the filter, "
                f"cannot sample {n}."
            )
        rng = np.random.default_rng(seed)
        selected = rng.choice(all_ids, size=n, replace=False)
        return sorted(selected.tolist())

    # ── Conversion to CanonicalFood ───────────────────────────────────────────

    def to_canonical_food(self, fdc_id: int) -> CanonicalFood | None:
        """Convert a single FNDDS recipe to a CanonicalFood.

        Args:
            fdc_id: FNDDS FDC ID.

        Returns:
            CanonicalFood instance, or None if the FDC ID was not found.
        """
        self.require_loaded()
        recipe = self._adapter.get_recipe(fdc_id)
        if recipe is None:
            return None

        # ── Serving size ──────────────────────────────────────────────────
        servings = recipe.get("food_portions", [])
        if servings:
            gram_weight = servings[0].get("gramWeight", 100.0)
            serving_label = servings[0].get("modifier", "")
            household = servings[0].get("amount", "")
            if household:
                household = f"{household} {serving_label}".strip()
        else:
            gram_weight = 100.0
            serving_label = ""
            household = None

        canonical_serving = CanonicalServing(
            serving_size_g=max(gram_weight, 1.0),
            serving_size_label=serving_label,
            household_serving=household or None,
        )

        # ── Ingredients ───────────────────────────────────────────────────
        total_weight = sum(
            ing.get("weight_g", 0.0) for ing in recipe["ingredients"]
        )
        canonical_ingredients: list[CanonicalIngredient] = []
        for ing in recipe["ingredients"]:
            code = ing.get("ingredient_code", 0) or 0
            weight = ing.get("weight_g", 0.0)
            frac = weight / total_weight if total_weight > 0 else 0.0
            code_str = str(code)

            canonical_ingredients.append(CanonicalIngredient(
                ingredient_code=code,
                description=ing.get("description", ""),
                weight_g=weight,
                fraction=frac,
                sequence_number=ing.get("sequence_number", 0),
                retention_code=ing.get("retention_code", 0),
                is_fortificant=code_str in FORTIFICANT_CODES,
                is_compound=False,
                sub_ingredients=[],
            ))

        # ── Nutrients ─────────────────────────────────────────────────────
        final_nutrients = recipe.get("final_nutrients")
        nutrients: list[NutrientValue] = []
        if final_nutrients is not None:
            for nr in final_nutrients.nutrients:
                nutrients.append(NutrientValue(
                    nutrient_id=nr.nutrient_id,
                    name=nr.name,
                    amount=nr.amount,
                    unit=nr.unit,
                ))

        return CanonicalFood(
            fdc_id=fdc_id,
            food_code=recipe.get("food_code", ""),
            food_name=recipe.get("description", ""),
            food_group=recipe.get("data_type", None),
            canonical_serving=canonical_serving,
            ingredients=canonical_ingredients,
            nutrients=nutrients,
            metadata={
                "publication_date": recipe.get("publication_date", ""),
                "data_type": recipe.get("data_type", ""),
            },
        )

    def to_canonical_foods(
        self,
        fdc_ids: list[int],
    ) -> dict[int, CanonicalFood]:
        """Convert multiple FDC IDs to CanonicalFood objects.

        Args:
            fdc_ids: List of FDC IDs.

        Returns:
            Dict mapping FDC ID → CanonicalFood (skipped IDs omitted).
        """
        result: dict[int, CanonicalFood] = {}
        for fdc_id in fdc_ids:
            cf = self.to_canonical_food(fdc_id)
            if cf is not None:
                result[fdc_id] = cf
        return result

    # ── Statistics ────────────────────────────────────────────────────────────

    def recipe_statistics(self) -> dict[str, Any]:
        """Return summary statistics about the loaded FNDDS data.

        Returns:
            Dict with counts and distributions.
        """
        self.require_loaded()
        all_ids = self.get_recipe_ids(min_ingredients=1)
        n_ids = [2, 3, 5, 10, 15]
        stats: dict[str, Any] = {
            "total_foods": len(self._adapter),
            "recipes_with_ingredients": len(all_ids),
        }
        for n in n_ids:
            stats[f"recipes_ge_{n}_ingredients"] = len(
                self.get_recipe_ids(min_ingredients=n)
            )
        return stats

    def __len__(self) -> int:
        if not self._loaded:
            return 0
        return self._adapter.__len__()
