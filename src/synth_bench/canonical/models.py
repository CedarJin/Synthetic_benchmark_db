"""Core data models for the Synthetic Benchmark.

These models define the canonical food representation (Module 1),
the structured label output (Module 2), and supporting types used
throughout the synthetic benchmark pipeline.
"""

# ruff: noqa: E501

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── Nutrient ──────────────────────────────────────────────────────────────────


class NutrientValue(BaseModel):
    """A single nutrient amount with unit and provenance."""

    nutrient_id: int = Field(..., description="USDA nutrient ID (e.g. 1008 for Energy)")
    name: str = Field(..., description="Standard nutrient name (e.g. 'Energy')")
    amount: float = Field(..., description="Numeric value per 100g")
    unit: str = Field(..., description="Unit of measurement (e.g. 'kcal', 'g', 'mg')")


# ── Canonical Ingredient ──────────────────────────────────────────────────────


class CanonicalIngredient(BaseModel):
    """An ingredient in canonical representation — ground truth form."""

    ingredient_code: int = Field(..., description="FNDDS ingredient code (NDB or FNDDS range)")
    description: str = Field(..., description="FNDDS standard ingredient description")
    weight_g: float = Field(..., ge=0.0, description="Weight in grams per 100g finished product")
    fraction: float = Field(..., ge=0.0, le=1.0, description="Mass fraction (weight_g / total)")
    sequence_number: int = Field(..., ge=0, description="Position in the ingredient list (1-based)")
    retention_code: int = Field(default=0, description="USDA retention factor code")
    is_fortificant: bool = Field(default=False, description="Whether this is a fortificant (code 999xxx)")
    is_compound: bool = Field(default=False, description="Whether this is a compound ingredient")
    sub_ingredients: list[CanonicalIngredient] = Field(default_factory=list, description="Expanded sub-ingredients if compound")


# ── Canonical Serving ─────────────────────────────────────────────────────────


class CanonicalServing(BaseModel):
    """Serving size information from FNDDS."""

    serving_size_g: float = Field(default=100.0, gt=0.0, description="Serving size in grams")
    serving_size_label: str = Field(default="", description="Human-readable serving description")
    household_serving: str | None = Field(default=None, description="Household measure (e.g. '1 cup')")


# ── Canonical Food ────────────────────────────────────────────────────────────


class CanonicalFood(BaseModel):
    """Full canonical representation of an FNDDS food (Module 1 output)."""

    fdc_id: int = Field(..., description="USDA FDC ID")
    food_code: str = Field(default="", description="FNDDS 8-digit food code")
    food_name: str = Field(..., description="FNDDS food description")
    food_group: str | None = Field(default=None, description="FNDDS food group / category")
    canonical_serving: CanonicalServing = Field(default_factory=CanonicalServing)
    ingredients: list[CanonicalIngredient] = Field(..., description="All ingredients with ground truth fractions")
    nutrients: list[NutrientValue] = Field(default_factory=list, description="Final product nutrient values per 100g")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata (FNDDS version, etc.)")


# ── Ground Truth ──────────────────────────────────────────────────────────────


class MappingEntry(BaseModel):
    """A single mapping from ingredient description to a target identifier."""

    source_text: str = Field(..., description="Original ingredient text")
    target_id: str = Field(..., description="Target identifier (FoodOn ID, USDA FDC ID, etc.)")
    target_namespace: str = Field(..., description="Namespace (e.g. 'foodon', 'usda_fndds', 'usda_sr_legacy')")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TransformationHistory(BaseModel):
    """Record of all transformations applied to a sample."""

    operator_names: list[str] = Field(default_factory=list, description="Names of applied operators in order")
    operator_configs: dict[str, Any] = Field(default_factory=dict, description="Operator-specific configurations")
    operator_versions: dict[str, str] = Field(default_factory=dict, description="Version of each operator")
    random_seed: int = Field(default=42, description="Random seed used for reproducibility")


class GroundTruth(BaseModel):
    """Complete ground truth record for a benchmark sample."""

    canonical_food: CanonicalFood = Field(..., description="The original canonical food")
    canonical_mappings: list[MappingEntry] = Field(default_factory=list, description="Canonical → standard ID mappings")
    target_mappings: list[MappingEntry] = Field(default_factory=list, description="Canonical → target space mappings")
    ingredient_amounts: dict[str, float] = Field(default_factory=dict, description="Ingredient → exact amount (g per 100g)")
    ingredient_fractions: dict[str, float] = Field(default_factory=dict, description="Ingredient → exact mass fraction")
    transformation_history: TransformationHistory = Field(default_factory=TransformationHistory)
    validation_report: dict[str, Any] | None = Field(default=None, description="Validation report after generation")


# ── Structured Label (after transformation) ────────────────────────────────────


class AllergenDeclaration(BaseModel):
    """An allergen declaration line."""

    allergens: list[str] = Field(default_factory=list, description="List of allergens (e.g. ['milk', 'wheat'])")
    declaration_text: str = Field(default="", description="Full declaration text")


class ClaimDeclaration(BaseModel):
    """A single claim that can appear on a label."""

    claim_text: str = Field(..., description="Full claim text")
    claim_type: str = Field(..., description="Type of claim: 'nutrient_content', 'health', 'structure_function'")
    evidence: str | None = Field(default=None, description="Basis for the claim")


class DeclaredIngredient(BaseModel):
    """An ingredient as it appears in the structured label after transformation."""

    original_description: str = Field(..., description="Original FNDDS description")
    declared_name: str = Field(..., description="Name as declared on the label")
    declaration_group: str = Field(default="main", description="'main' or 'two_percent_or_less'")
    declared_percentage: float | None = Field(default=None, description="Declared percentage if applicable")
    is_compound: bool = Field(default=False)
    sub_ingredients: list[str] = Field(default_factory=list, description="Declared sub-ingredient names")

    # For ground truth tracking
    original_code: int = Field(default=0, description="Original FNDDS ingredient code")
    original_fraction: float = Field(default=0.0, description="Original mass fraction")


class NutritionFactsPanel(BaseModel):
    """Structured Nutrition Facts panel data."""

    serving_size: str = Field(default="", description="Serving size declaration")
    servings_per_container: str | None = Field(default=None, description="Servings per container")
    calories: float = Field(default=0.0, description="Calories per serving label value")
    total_fat: float | None = Field(default=None)
    saturated_fat: float | None = Field(default=None)
    trans_fat: float | None = Field(default=None)
    cholesterol: float | None = Field(default=None)
    sodium: float | None = Field(default=None)
    total_carbohydrate: float | None = Field(default=None)
    dietary_fiber: float | None = Field(default=None)
    total_sugars: float | None = Field(default=None)
    added_sugars: float | None = Field(default=None)
    protein: float | None = Field(default=None)
    vitamin_d: float | None = Field(default=None)
    calcium: float | None = Field(default=None)
    iron: float | None = Field(default=None)
    potassium: float | None = Field(default=None)
    daily_values: dict[str, float] = Field(default_factory=dict, description="% Daily Values for each nutrient")


class StructuredLabel(BaseModel):
    """The structured label representation after Module 2 transformation."""

    product_name: str = Field(default="", description="Product name for the label")
    ingredient_list: list[DeclaredIngredient] = Field(default_factory=list, description="Ingredients as declared on label, in order")
    two_percent_group: list[DeclaredIngredient] = Field(default_factory=list, description="≤2% group ingredients")
    nutrition_facts: NutritionFactsPanel | None = Field(default=None)
    allergens: AllergenDeclaration | None = Field(default=None)
    claims: list[ClaimDeclaration] = Field(default_factory=list)
    raw_ingredient_text: str | None = Field(default=None, description="Final ingredient declaration text after LLM rendering")


# ── Operator Record ───────────────────────────────────────────────────────────


class OperatorRecord(BaseModel):
    """Record of a single operator applied during transformation."""

    operator_name: str = Field(..., description="Operator class name")
    operator_version: str = Field(default="1.0", description="Operator version")
    applied_ingredients: list[str] = Field(default_factory=list, description="Ingredients affected")
    config: dict[str, Any] = Field(default_factory=dict, description="Configuration used")


class DifficultyLevel(int, Enum):
    """Difficulty level based on applied operators."""

    EASY = 1
    MEDIUM = 2
    HARD = 3


# ── Full Sample ───────────────────────────────────────────────────────────────


class SampleMetadata(BaseModel):
    """Reproducibility metadata for a generated sample."""

    sample_id: str = Field(..., description="Unique sample identifier")
    fndds_version: str = Field(default="2024-10-31", description="FNDDS version used")
    software_version: str = Field(default="0.1.0", description="synth-bench version")
    operator_records: list[OperatorRecord] = Field(default_factory=list)
    random_seed: int = Field(default=42)
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.EASY)
    prompt_template_version: str | None = Field(default=None, description="LLM prompt template version if used")
    total_applied_operators: int = Field(default=0, ge=0)


class BenchmarkSample(BaseModel):
    """Complete benchmark sample wrapping all output artifacts."""

    metadata: SampleMetadata
    canonical_food: CanonicalFood
    ground_truth: GroundTruth
    structured_label: StructuredLabel
    rendered_label_text: str | None = Field(default=None, description="Final LLM-rendered ingredient label text")
    rendered_nutrition_facts: str | None = Field(default=None, description="Final rendered Nutrition Facts text")
    nutrition_facts_json: NutritionFactsPanel | None = Field(default=None)
    validation: dict[str, Any] | None = Field(default=None)

    def to_dataset_dict(self) -> dict[str, Any]:
        """Serialize to the standard dataset directory format."""
        return {
            "canonical_food.json": self.canonical_food.model_dump(),
            "ground_truth.json": self.ground_truth.model_dump(),
            "structured_label.json": self.structured_label.model_dump(),
            "rendered_label.txt": self.rendered_label_text or "",
            "nutrition_facts.json": self.nutrition_facts_json.model_dump() if self.nutrition_facts_json else {},
            "operators.json": [op.model_dump() for op in self.metadata.operator_records],
            "validation.json": self.validation or {},
            "metadata.json": self.metadata.model_dump(),
        }
