"""Transformation engine — operators pipeline for benchmark generation.

Architecture:
  Each operator transforms a LabelState (intermediate label representation)
  and records its actions via OperatorRecord. The TransformationEngine
  chains operators in a configurable pipeline.

  Flow: CanonicalFood → [operator chain] → StructuredLabel
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from synth_bench.canonical.models import (
    AllergenDeclaration,
    BenchmarkSample,
    CanonicalFood,
    ClaimDeclaration,
    DeclaredIngredient,
    DifficultyLevel,
    GroundTruth,
    MappingEntry,
    NutritionFactsPanel,
    OperatorRecord,
    SampleMetadata,
    StructuredLabel,
    TransformationHistory,
)

# ── LabelState — flows through the pipeline ───────────────────────────────────


@dataclass
class LabelState:
    """Mutable state flowing through the operator pipeline.

    Each operator reads and modifies this state, building up the
    structured label representation incrementally.
    """

    canonical_food: CanonicalFood
    product_name: str = ""
    declared_ingredients: list[DeclaredIngredient] = field(default_factory=list)
    two_percent_group: list[DeclaredIngredient] = field(default_factory=list)
    nutrition_facts: NutritionFactsPanel | None = None
    allergens: AllergenDeclaration | None = None
    claims: list[ClaimDeclaration] = field(default_factory=list)
    raw_ingredient_text: str | None = None
    rendered_nutrition_facts: str | None = None
    operator_records: list[OperatorRecord] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_canonical_food(cls, food: CanonicalFood, **config: Any) -> LabelState:
        """Initialize LabelState from a CanonicalFood."""
        product_name = food.food_name.upper()
        ingredients = sorted(
            (ing for ing in food.ingredients if not ing.is_fortificant),
            key=lambda ing: (-ing.fraction, ing.sequence_number),
        )
        declared = [
            DeclaredIngredient(
                original_description=ing.description,
                declared_name=ing.description.upper(),
                declaration_group="main",
                original_code=ing.ingredient_code,
                original_fraction=ing.fraction,
            )
            for ing in ingredients
        ]
        return cls(
            canonical_food=food,
            product_name=product_name,
            declared_ingredients=declared,
            config=config,
        )


# ── Base Operator ─────────────────────────────────────────────────────────────


class BaseOperator(ABC):
    """Abstract base for all transformation operators.

    Each operator transforms a LabelState, appends its OperatorRecord,
    and returns the modified state. Operators are stateless — all
    configuration goes through LabelState.config.
    """

    name: str = "base"
    version: str = "1.0"

    @abstractmethod
    def apply(self, state: LabelState) -> LabelState:
        """Apply this operator to the current label state.

        Args:
            state: Current label state (modified in place or via copy).

        Returns:
            Modified label state.
        """
        ...

    def make_record(
        self,
        affected: list[str] | None = None,
        **extra: Any,
    ) -> OperatorRecord:
        """Create an OperatorRecord for this operator invocation."""
        return OperatorRecord(
            operator_name=self.name,
            operator_version=self.version,
            applied_ingredients=affected or [],
            config=extra,
        )


# ── Transformation Engine ─────────────────────────────────────────────────────


class TransformationEngine:
    """Pipeline that chains operators to transform CanonicalFood → StructuredLabel.

    The engine configures which operators are applied, in what order,
    and with what parameterization.
    """

    # Default operator pipeline (in order)
    DEFAULT_OPERATORS: list[str] = [
        "rename",
        "generic_name",
        "compound",
        "less_than_2_pct",
        "allergen",
        "claim",
        "nutrition_facts",
    ]

    # Difficulty assignment per operator
    OPERATOR_DIFFICULTY: dict[str, DifficultyLevel] = {
        "rename": DifficultyLevel.EASY,
        "generic_name": DifficultyLevel.EASY,
        "compound": DifficultyLevel.MEDIUM,
        "less_than_2_pct": DifficultyLevel.MEDIUM,
        "allergen": DifficultyLevel.EASY,
        "claim": DifficultyLevel.MEDIUM,
        "nutrition_facts": DifficultyLevel.EASY,
    }

    def __init__(self, operator_registry: dict[str, BaseOperator] | None = None) -> None:
        self._registry: dict[str, BaseOperator] = {}
        if operator_registry:
            self._registry.update(operator_registry)

    def register(self, operator: BaseOperator) -> None:
        """Register an operator by its name."""
        self._registry[operator.name] = operator

    def get_operator(self, name: str) -> BaseOperator | None:
        """Get a registered operator by name."""
        return self._registry.get(name)

    def transform(
        self,
        food: CanonicalFood,
        operators: list[str] | None = None,
        **config: Any,
    ) -> tuple[StructuredLabel, list[OperatorRecord], DifficultyLevel]:
        """Run the operator pipeline on a CanonicalFood.

        Args:
            food: Canonical food to transform.
            operators: List of operator names to apply (default: all).
            config: Configuration parameters for operators.

        Returns:
            (structured_label, operator_records, difficulty_level)
        """
        ops = self.DEFAULT_OPERATORS if operators is None else operators
        state = LabelState.from_canonical_food(food, **config)

        for op_name in ops:
            operator = self._registry.get(op_name)
            if operator is None:
                raise ValueError(
                    f"Unknown operator: '{op_name}'. Registered: {list(self._registry)}"
                )
            state = operator.apply(state)

        # Build the StructuredLabel from the final state
        label = StructuredLabel(
            product_name=state.product_name,
            ingredient_list=state.declared_ingredients,
            two_percent_group=state.two_percent_group,
            nutrition_facts=state.nutrition_facts,
            allergens=state.allergens,
            claims=state.claims,
            raw_ingredient_text=state.raw_ingredient_text,
        )

        # Determine difficulty from operators that produced a visible artifact
        # or affected at least one ingredient.
        difficulty = DifficultyLevel.EASY
        for record in state.operator_records:
            has_effect = bool(record.applied_ingredients)
            if record.operator_name == "claim":
                has_effect = has_effect or record.config.get("n_claims", 0) > 0
            elif record.operator_name == "nutrition_facts":
                has_effect = True
            if not has_effect:
                continue
            op_diff = self.OPERATOR_DIFFICULTY.get(record.operator_name, DifficultyLevel.EASY)
            if op_diff > difficulty:
                difficulty = op_diff

        return label, state.operator_records, difficulty

    def generate_sample(
        self,
        food: CanonicalFood,
        sample_id: str,
        seed: int = 42,
        operators: list[str] | None = None,
        **config: Any,
    ) -> BenchmarkSample:
        """Full pipeline: CanonicalFood → complete BenchmarkSample.

        Args:
            food: Canonical food to generate from.
            sample_id: Unique sample identifier.
            seed: Random seed for reproducibility.
            operators: Operator pipeline to use.
            config: Additional configuration.

        Returns:
            Complete BenchmarkSample with all artifacts.
        """
        label, op_records, difficulty = self.transform(food, operators=operators, **config)

        canonical_mappings = [
            MappingEntry(
                source_text=ing.description,
                target_id=str(ing.ingredient_code),
                target_namespace="usda_fndds_ingredient_code",
            )
            for ing in food.ingredients
            if not ing.is_fortificant
        ]
        target_mappings = [
            MappingEntry(
                source_text=ing.declared_name,
                target_id=ing.original_description,
                target_namespace="usda_fndds_ingredient_description",
            )
            for ing in [*label.ingredient_list, *label.two_percent_group]
        ]
        transformation_history = TransformationHistory(
            operator_names=[record.operator_name for record in op_records],
            operator_configs={record.operator_name: record.config for record in op_records},
            operator_versions={
                record.operator_name: record.operator_version for record in op_records
            },
            random_seed=seed,
        )

        # Build ground truth
        gt = GroundTruth(
            canonical_food=food,
            canonical_mappings=canonical_mappings,
            target_mappings=target_mappings,
            ingredient_amounts={
                str(ing.ingredient_code): ing.weight_g
                for ing in food.ingredients
                if not ing.is_fortificant
            },
            ingredient_fractions={
                str(ing.ingredient_code): ing.fraction
                for ing in food.ingredients
                if not ing.is_fortificant
            },
            transformation_history=transformation_history,
        )

        # Build metadata
        meta = SampleMetadata(
            sample_id=sample_id,
            operator_records=op_records,
            random_seed=seed,
            difficulty=difficulty,
            total_applied_operators=len(op_records),
        )

        return BenchmarkSample(
            metadata=meta,
            canonical_food=food,
            ground_truth=gt,
            structured_label=label,
            rendered_label_text=label.raw_ingredient_text,
            nutrition_facts_json=label.nutrition_facts,
        )
