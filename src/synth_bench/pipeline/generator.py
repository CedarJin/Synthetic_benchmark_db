"""Dataset generation pipeline.

Orchestrates the full benchmark generation workflow:

  FNDDS → CanonicalFood → Transform → Validate → Render → Write to disk

Supports:
  - Configurable recipe selection (N samples, ingredient count range)
  - Configurable operator pipelines
  - Optional parallel generation
  - Validation with auto-repair
  - Label rendering (template-based or LLM)
  - Dataset directory organization
  - Full reproducibility tracking
"""

from __future__ import annotations

import csv
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from synth_bench.canonical.loader import FNDDSLoader
from synth_bench.canonical.models import BenchmarkSample
from synth_bench.llm.realizer import render_sample
from synth_bench.pipeline.split import DatasetSplit
from synth_bench.transform.engine import TransformationEngine
from synth_bench.validation.rules import (
    AllergenDeclarationRule,
    ClaimEligibilityRule,
    FDASyntaxRule,
    IngredientOrderRule,
    IngredientPreservationRule,
    NutritionFactsConsistencyRule,
    ProhibitedTerminologyRule,
)
from synth_bench.validation.validator import ValidationEngine

logger = logging.getLogger(__name__)


# ── Generator Configuration ───────────────────────────────────────────────────


@dataclass
class GeneratorConfig:
    """Configuration for the dataset generator."""

    # FNDDS data
    fndds_path: str | Path = ""
    """Path to FNDDS surveyDownload.json."""

    # Recipe selection
    n_samples: int = 200
    """Number of samples to generate."""
    min_ingredients: int = 2
    """Minimum number of ingredients per recipe."""
    max_ingredients: int = 30
    """Maximum number of ingredients per recipe."""
    random_seed: int = 42
    """Random seed for reproducibility."""

    # Operators
    operators: list[str] | None = None
    """Operator pipeline to use (None = all operators)."""
    operator_config: dict[str, Any] = field(default_factory=dict)
    """Configuration passed to operators."""

    # Validation
    enable_validation: bool = True
    """Whether to run validation after generation."""
    auto_repair: bool = True
    """Whether to attempt auto-repair on validation failure."""

    # LLM refinement
    enable_llm_refinement: bool = False
    """Whether to use LLM for label text refinement."""
    llm_api_key: str | None = None
    """LLM API key (required if llm_refinement is True)."""
    llm_model: str = "gpt-4o-mini"
    """LLM model to use."""

    # Output
    output_dir: str | Path = "data/benchmark"
    """Root output directory for the generated dataset."""
    overwrite: bool = False
    """Whether to overwrite existing output directory."""
    include_validation_failures: bool = True
    """Whether to include samples that failed validation (default: True)."""

    # Parallelism
    max_workers: int = 4
    """Number of parallel workers (1 = sequential)."""


# ── Generator Result ──────────────────────────────────────────────────────────


@dataclass
class GenerationResult:
    """Result of generating a single sample."""

    fdc_id: int
    sample_id: str
    success: bool
    sample: BenchmarkSample | None = None
    error: str | None = None
    duration_s: float = 0.0


# ── Dataset Generator ─────────────────────────────────────────────────────────


class DatasetGenerator:
    """Main dataset generator — orchestrates the full pipeline.

    Usage::

        gen = DatasetGenerator(config)
        gen.load_fndds()
        gen.generate()
        gen.write_dataset()
    """

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()
        self._fndds_loader: FNDDSLoader | None = None
        self._engine: TransformationEngine | None = None
        self._validation_engine: ValidationEngine | None = None
        self._selected_fdc_ids: list[int] = []
        self._samples: list[BenchmarkSample] = []
        self._results: list[GenerationResult] = []
        self._generation_start: float = 0.0

    # ── Initialization ────────────────────────────────────────────────────────

    def load_fndds(self, fndds_path: str | Path | None = None) -> None:
        """Load FNDDS data.

        Args:
            fndds_path: Path to FNDDS JSON (overrides config path if given).
        """
        path = fndds_path or self.config.fndds_path
        if not path:
            raise ValueError("FNDDS path not provided")
        self._fndds_loader = FNDDSLoader(Path(path))
        logger.info(
            "Loaded FNDDS: %d foods, %d with 2+ ingredients",
            len(self._fndds_loader),
            len(self._fndds_loader.get_recipe_ids(min_ingredients=2)),
        )

    def _init_engine(self) -> TransformationEngine:
        """Initialize the transformation engine with all operators."""
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

        engine = TransformationEngine()
        engine.register(RenameOperator())
        engine.register(GenericNameOperator())
        engine.register(CompoundIngredientOperator())
        engine.register(LessThan2PercentOperator())
        engine.register(AllergenOperator())
        engine.register(ClaimEligibilityOperator())
        engine.register(NutritionFactsOperator())
        self._engine = engine
        return engine

    def _init_validation_engine(self) -> ValidationEngine:
        """Initialize the validation engine with all rules."""
        ve = ValidationEngine()
        ve.add_rule(IngredientPreservationRule())
        ve.add_rule(IngredientOrderRule())
        ve.add_rule(FDASyntaxRule())
        ve.add_rule(AllergenDeclarationRule())
        ve.add_rule(ClaimEligibilityRule())
        ve.add_rule(NutritionFactsConsistencyRule())
        ve.add_rule(ProhibitedTerminologyRule())
        self._validation_engine = ve
        return ve

    # ── Recipe Selection ──────────────────────────────────────────────────────

    def select_recipes(self) -> list[int]:
        """Select FDC IDs for dataset generation.

        Returns:
            List of selected FDC IDs.
        """
        if self._fndds_loader is None:
            raise RuntimeError("FNDDS not loaded. Call load_fndds() first.")

        self._selected_fdc_ids = self._fndds_loader.sample_recipes(
            n=self.config.n_samples,
            min_ingredients=self.config.min_ingredients,
            max_ingredients=self.config.max_ingredients,
            seed=self.config.random_seed,
        )
        logger.info(
            "Selected %d recipes (ingredients: %d-%d)",
            len(self._selected_fdc_ids),
            self.config.min_ingredients,
            self.config.max_ingredients,
        )
        return self._selected_fdc_ids

    # ── Single Sample Generation ──────────────────────────────────────────────

    def _generate_one(self, fdc_id: int, seed_offset: int = 0) -> GenerationResult:
        """Generate, validate, and render a single sample.

        Args:
            fdc_id: FNDDS FDC ID.
            seed_offset: Offset added to the global seed per-sample.

        Returns:
            GenerationResult with sample or error.
        """
        t0 = time.time()
        sample_id = f"sample_{seed_offset + 1:06d}"

        try:
            # 1. Canonical Food
            assert self._fndds_loader is not None
            cf = self._fndds_loader.to_canonical_food(fdc_id)
            if cf is None:
                return GenerationResult(
                    fdc_id=fdc_id,
                    sample_id=sample_id,
                    success=False,
                    error=f"FDC ID {fdc_id} not found in FNDDS",
                )

            # 2. Generate sample (transform)
            assert self._engine is not None
            sample = self._engine.generate_sample(
                cf,
                sample_id=sample_id,
                seed=self.config.random_seed + seed_offset,
                operators=self.config.operators,
                **self.config.operator_config,
            )

            # 3. Render labels
            sample = render_sample(sample)

            # 4. LLM refinement (optional)
            if self.config.enable_llm_refinement and self.config.llm_api_key:
                from synth_bench.llm.realizer import llm_refine_label

                refined = llm_refine_label(
                    sample.rendered_label_text or "",
                    sample.rendered_nutrition_facts,
                    api_key=self.config.llm_api_key,
                    model=self.config.llm_model,
                )
                if refined:
                    sample.rendered_label_text = refined

            # 5. Validate final rendered output
            if self.config.enable_validation:
                assert self._validation_engine is not None
                sample, report = self._validation_engine.validate(
                    sample,
                    auto_repair=self.config.auto_repair,
                )
                sample.validation = report.to_dict()
                sample.ground_truth.validation_report = sample.validation

                if not report.all_passed and not self.config.include_validation_failures:
                    return GenerationResult(
                        fdc_id=fdc_id,
                        sample_id=sample_id,
                        success=False,
                        error=f"Validation failed: {report.n_failed} rule(s) failed",
                        duration_s=time.time() - t0,
                    )

            return GenerationResult(
                fdc_id=fdc_id,
                sample_id=sample_id,
                success=True,
                sample=sample,
                duration_s=time.time() - t0,
            )

        except Exception as e:
            logger.warning("Failed to generate sample for FDC %d: %s", fdc_id, e)
            return GenerationResult(
                fdc_id=fdc_id,
                sample_id=sample_id,
                success=False,
                error=str(e),
                duration_s=time.time() - t0,
            )

    # ── Full Generation ───────────────────────────────────────────────────────

    def generate(self, fdc_ids: list[int] | None = None) -> list[GenerationResult]:
        """Run the full generation pipeline.

        Args:
            fdc_ids: Optional list of FDC IDs to process. If None, uses
                     previously selected recipes.

        Returns:
            List of GenerationResults.
        """
        ids = fdc_ids if fdc_ids is not None else self._selected_fdc_ids
        if not ids:
            raise ValueError("No FDC IDs provided. Call select_recipes() first.")

        # Init engines if needed
        if self._engine is None:
            self._init_engine()
        if self._validation_engine is None and self.config.enable_validation:
            self._init_validation_engine()

        self._samples.clear()
        self._results.clear()
        self._generation_start = time.time()

        n_workers = self.config.max_workers
        if n_workers <= 1:
            # Sequential
            for i, fdc_id in enumerate(ids):
                result = self._generate_one(fdc_id, seed_offset=i)
                self._results.append(result)
                if result.success and result.sample:
                    self._samples.append(result.sample)
                if (i + 1) % 20 == 0 or i == len(ids) - 1:
                    logger.info(
                        "Progress: %d/%d (%.0f%%) — %d ok, %d failed",
                        i + 1,
                        len(ids),
                        100.0 * (i + 1) / len(ids),
                        len([r for r in self._results if r.success]),
                        len([r for r in self._results if not r.success]),
                    )
        else:
            # Parallel
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                fut_map = {
                    pool.submit(self._generate_one, fdc_id, i): (i, fdc_id)
                    for i, fdc_id in enumerate(ids)
                }
                completed = 0
                for future in as_completed(fut_map):
                    result = future.result()
                    self._results.append(result)
                    if result.success and result.sample:
                        self._samples.append(result.sample)
                    completed += 1
                    if completed % 20 == 0 or completed == len(ids):
                        logger.info(
                            "Progress: %d/%d (%.0f%%)",
                            completed,
                            len(ids),
                            100.0 * completed / len(ids),
                        )

        # Sort results by sample_id for consistent ordering
        self._results.sort(key=lambda r: r.sample_id)
        self._samples.sort(key=lambda s: s.metadata.sample_id)

        n_ok = len([r for r in self._results if r.success])
        logger.info(
            "Generation complete: %d/%d successful (%.1f%%) in %.1fs",
            n_ok,
            len(ids),
            100.0 * n_ok / len(ids) if ids else 0,
            time.time() - self._generation_start,
        )
        return self._results

    # ── Dataset Writing ───────────────────────────────────────────────────────

    def write_dataset(
        self,
        output_dir: str | Path | None = None,
        splits: list[DatasetSplit] | None = None,
    ) -> Path:
        """Write the generated dataset to disk.

        Creates the organized directory structure with each sample as a
        subdirectory and a dataset-level manifest.

        Args:
            output_dir: Output directory (overrides config if given).
            splits: Optional dataset splits (train/val/test).

        Returns:
            Path to the output directory.
        """
        out_dir = Path(output_dir or self.config.output_dir)
        if out_dir.exists():
            if self.config.overwrite:
                import shutil

                shutil.rmtree(out_dir)
            else:
                raise FileExistsError(
                    f"Output directory exists: {out_dir}. Set overwrite=True to overwrite."
                )
        out_dir.mkdir(parents=True, exist_ok=True)

        # Write each sample
        for sample in self._samples:
            sample_dir = out_dir / sample.metadata.sample_id
            sample_dir.mkdir(exist_ok=True)

            d = sample.to_dataset_dict()
            for filename, content in d.items():
                filepath = sample_dir / filename
                if filename.endswith(".json"):
                    with open(filepath, "w") as f:
                        json.dump(content, f, indent=2, default=str)
                elif filename.endswith(".txt"):
                    with open(filepath, "w") as f:
                        f.write(str(content))

        # Write dataset manifest
        manifest = self._build_manifest()
        with open(out_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2, default=str)

        # Write sample index CSV
        csv_path = out_dir / "samples.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["sample_id", "fdc_id", "food_name", "n_ingredients", "difficulty", "success"]
            )
            for r in self._results:
                if r.sample:
                    cf = r.sample.canonical_food
                    writer.writerow(
                        [
                            r.sample_id,
                            cf.fdc_id,
                            cf.food_name,
                            len(cf.ingredients),
                            r.sample.metadata.difficulty.value,
                            r.success,
                        ]
                    )
                else:
                    writer.writerow([r.sample_id, r.fdc_id, "", "", "", r.success])

        # Write splits if provided
        if splits:
            splits_dir = out_dir / "splits"
            splits_dir.mkdir(exist_ok=True)
            for split in splits:
                split_file = splits_dir / f"{split.name}.txt"
                sample_ids = [s.metadata.sample_id for s in split.samples]
                with open(split_file, "w") as f:
                    f.write("\n".join(sample_ids))

        n_ok = len(self._samples)
        logger.info(
            "Dataset written to %s (%d samples, %d failed)",
            out_dir,
            n_ok,
            len(self._results) - n_ok,
        )
        return out_dir

    def _build_manifest(self) -> dict[str, Any]:
        """Build dataset-level manifest with reproducibility info."""
        n_ok = len(self._samples)
        n_total = len(self._results)
        return {
            "dataset_name": "Knowledge-guided Synthetic Benchmark",
            "generated_at": datetime.now(UTC).isoformat(),
            "config": {
                "fndds_path": str(self.config.fndds_path),
                "n_samples": self.config.n_samples,
                "min_ingredients": self.config.min_ingredients,
                "max_ingredients": self.config.max_ingredients,
                "random_seed": self.config.random_seed,
                "operators": self.config.operators,
                "enable_validation": self.config.enable_validation,
                "max_workers": self.config.max_workers,
            },
            "summary": {
                "total_samples": n_total,
                "successful": n_ok,
                "failed": n_total - n_ok,
                "success_rate_pct": round(100.0 * n_ok / n_total, 1) if n_total else 0,
                "generation_time_s": round(time.time() - self._generation_start, 1)
                if self._generation_start
                else 0,
            },
        }

    @property
    def samples(self) -> list[BenchmarkSample]:
        """Generated samples (successful only)."""
        return list(self._samples)

    @property
    def results(self) -> list[GenerationResult]:
        """All generation results, including failures."""
        return list(self._results)
