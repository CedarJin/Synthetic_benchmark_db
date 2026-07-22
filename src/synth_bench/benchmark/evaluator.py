"""Benchmark evaluator — run evaluation of parsers and mappers.

Usage::

    evaluator = BenchmarkEvaluator()
    evaluator.load_dataset("data/benchmark")
    results = evaluator.evaluate_parsing(my_parser_fn)
    results = evaluator.evaluate_mapping(my_mapper_fn)
    evaluator.print_report()
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from synth_bench.benchmark.baselines import (
    baseline_dictionary_mapper,
    baseline_parse_ingredients,
)
from synth_bench.benchmark.metrics import (
    compute_mapping_metrics,
    compute_ordered_parsing_metrics,
)
from synth_bench.canonical.models import BenchmarkSample, DifficultyLevel

logger = logging.getLogger(__name__)


@dataclass
class SampleResult:
    """Evaluation result for a single sample."""

    sample_id: str
    difficulty: DifficultyLevel
    fdc_id: int
    applied_operators: list[str]
    parsing_metrics: dict[str, float] = field(default_factory=dict)
    mapping_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Aggregated evaluation results across all samples."""

    parsing_results: list[SampleResult] = field(default_factory=list)
    mapping_results: list[SampleResult] = field(default_factory=list)

    # Aggregated
    parser_name: str = ""
    mapper_name: str = ""

    def aggregate_parsing_by_difficulty(self) -> dict[str, dict[str, float]]:
        """Aggregate parsing metrics by difficulty level."""
        return _aggregate_by(
            self.parsing_results,
            key_fn=lambda r: r.difficulty.name,
            metric_fn=lambda r: r.parsing_metrics,
        )

    def aggregate_parsing_by_operators(self) -> dict[str, dict[str, float]]:
        """Aggregate parsing metrics by operator type."""
        return _aggregate_by(
            self.parsing_results,
            key_fn=lambda r: ",".join(sorted(r.applied_operators)),
            metric_fn=lambda r: r.parsing_metrics,
        )

    def aggregate_mapping_by_difficulty(self) -> dict[str, dict[str, float]]:
        """Aggregate mapping metrics by difficulty level."""
        return _aggregate_by(
            self.mapping_results,
            key_fn=lambda r: r.difficulty.name,
            metric_fn=lambda r: r.mapping_metrics,
        )

    def summary(self) -> dict[str, Any]:
        """Compute summary statistics."""
        avg_parsing = _average_metrics(
            [r.parsing_metrics for r in self.parsing_results if r.parsing_metrics],
        )
        avg_mapping = _average_metrics(
            [r.mapping_metrics for r in self.mapping_results if r.mapping_metrics],
        )
        return {
            "parsing": avg_parsing,
            "mapping": avg_mapping,
            "n_parsing_samples": len(self.parsing_results),
            "n_mapping_samples": len(self.mapping_results),
            "n_samples": max(len(self.parsing_results), len(self.mapping_results)),
            "parser": self.parser_name,
            "mapper": self.mapper_name,
        }


def _aggregate_by(
    results: list[SampleResult],
    key_fn: Callable[[SampleResult], str],
    metric_fn: Callable[[SampleResult], dict[str, float]],
) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict[str, float]]] = {}
    for r in results:
        key = key_fn(r)
        m = metric_fn(r)
        if not m:
            continue
        if key not in groups:
            groups[key] = []
        groups[key].append(m)

    return {k: _average_metrics(v) for k, v in groups.items()}


def _average_metrics(metrics_list: list[dict[str, float]]) -> dict[str, float]:
    if not metrics_list:
        return {}
    keys = metrics_list[0].keys()
    averaged: dict[str, float] = {}
    for key in keys:
        values = [m.get(key, 0.0) for m in metrics_list]
        averaged[key] = round(sum(values) / len(values), 4)
    return averaged


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Evaluator
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkEvaluator:
    """Run and report parsing/mapping evaluations on the benchmark.

    Evaluates:
      1. Ingredient parsing: label text → structured ingredient list
      2. Ingredient mapping: ingredient name → standard identifier
    """

    def __init__(self) -> None:
        self._samples: list[BenchmarkSample] = []

    def load_dataset(self, dataset_path: str | Path) -> int:
        """Load a generated benchmark dataset from disk.

        Args:
            dataset_path: Path to the dataset directory.

        Returns:
            Number of samples loaded.
        """
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        self._samples.clear()
        for sample_dir in sorted(path.iterdir()):
            if not sample_dir.is_dir():
                continue
            if not sample_dir.name.startswith("sample_"):
                continue

            # Load the sample from individual JSON files
            sample = _load_sample_from_dir(sample_dir)
            if sample is not None:
                self._samples.append(sample)

        logger.info("Loaded %d samples from %s", len(self._samples), path)
        return len(self._samples)

    # ── Parsing Evaluation ────────────────────────────────────────────────────

    def evaluate_parsing(
        self,
        parser_fn: Callable[[str], list[str]],
        parser_name: str = "custom",
    ) -> EvaluationReport:
        """Evaluate a parser function against all loaded samples.

        Args:
            parser_fn: Function that takes label text and returns ingredient list.
            parser_name: Name for the parser (for reporting).

        Returns:
            EvaluationReport with per-sample and aggregated results.
        """
        report = EvaluationReport(parser_name=parser_name)

        for sample in self._samples:
            ground_truth = [
                ing.declared_name for ing in sample.structured_label.ingredient_list
            ] + [ing.declared_name for ing in sample.structured_label.two_percent_group]

            label_text = sample.rendered_label_text or ""
            predicted = parser_fn(label_text)

            metrics = compute_ordered_parsing_metrics(
                ground_truth,
                predicted,
            )

            report.parsing_results.append(
                SampleResult(
                    sample_id=sample.metadata.sample_id,
                    difficulty=sample.metadata.difficulty,
                    fdc_id=sample.canonical_food.fdc_id,
                    applied_operators=[op.operator_name for op in sample.metadata.operator_records],
                    parsing_metrics=metrics,
                )
            )

        return report

    # ── Mapping Evaluation ────────────────────────────────────────────────────

    def evaluate_mapping(
        self,
        mapper_fn: Callable[[list[str]], dict[str, list[str]]],
        mapper_name: str = "custom",
    ) -> EvaluationReport:
        """Evaluate a mapper function against all loaded samples.

        Args:
            mapper_fn: Function that takes ingredient names and returns
                       {name: [ranked_candidate_ids]}.
            mapper_name: Name for the mapper (for reporting).

        Returns:
            EvaluationReport with per-sample and aggregated results.
        """
        report = EvaluationReport(mapper_name=mapper_name)

        for sample in self._samples:
            # Ground truth: declared ingredient → canonical FNDDS description.
            # This matches the namespace returned by the built-in dictionary
            # baseline while numeric ingredient codes remain in GroundTruth.
            ingredients = [
                *sample.structured_label.ingredient_list,
                *sample.structured_label.two_percent_group,
            ]
            name_counts: dict[str, int] = {}
            ground_truth: dict[str, str] = {}
            ingredient_names: list[str] = []
            key_to_name: dict[str, str] = {}
            for ing in ingredients:
                name_counts[ing.declared_name] = name_counts.get(ing.declared_name, 0) + 1
                key = (
                    ing.declared_name
                    if name_counts[ing.declared_name] == 1
                    else f"{ing.declared_name}#{name_counts[ing.declared_name]}"
                )
                ground_truth[key] = ing.original_description
                key_to_name[key] = ing.declared_name
                ingredient_names.append(ing.declared_name)

            raw_predictions = mapper_fn(ingredient_names)
            predictions = {key: raw_predictions.get(name, []) for key, name in key_to_name.items()}

            metrics = compute_mapping_metrics(ground_truth, predictions, k=5)

            report.mapping_results.append(
                SampleResult(
                    sample_id=sample.metadata.sample_id,
                    difficulty=sample.metadata.difficulty,
                    fdc_id=sample.canonical_food.fdc_id,
                    applied_operators=[op.operator_name for op in sample.metadata.operator_records],
                    mapping_metrics=metrics,
                )
            )

        return report

    # ── Run Baselines ─────────────────────────────────────────────────────────

    def run_parsing_baseline(self) -> EvaluationReport:
        """Run the baseline regex parser on all loaded samples."""
        return self.evaluate_parsing(
            baseline_parse_ingredients,
            parser_name="regex_baseline",
        )

    def run_mapping_baseline(self) -> EvaluationReport:
        """Run the baseline dictionary mapper on all loaded samples."""
        return self.evaluate_mapping(
            baseline_dictionary_mapper,
            mapper_name="dictionary_baseline",
        )

    @property
    def samples(self) -> list[BenchmarkSample]:
        return list(self._samples)

    @property
    def n_samples(self) -> int:
        return len(self._samples)


def _load_sample_from_dir(sample_dir: Path) -> BenchmarkSample | None:
    """Load a single BenchmarkSample from its directory."""
    try:
        from synth_bench.canonical.models import (
            CanonicalFood,
            GroundTruth,
            NutritionFactsPanel,
            SampleMetadata,
            StructuredLabel,
        )

        with open(sample_dir / "canonical_food.json") as f:
            cf = CanonicalFood(**json.load(f))
        with open(sample_dir / "ground_truth.json") as f:
            gt = GroundTruth(**json.load(f))
        with open(sample_dir / "structured_label.json") as f:
            sl = StructuredLabel(**json.load(f))
        with open(sample_dir / "metadata.json") as f:
            meta = SampleMetadata(**json.load(f))

        nf = None
        nf_path = sample_dir / "nutrition_facts.json"
        if nf_path.exists():
            nf_data = json.loads(nf_path.read_text())
            if nf_data:  # non-empty
                nf = NutritionFactsPanel(**nf_data)

        rendered_text = ""
        rt_path = sample_dir / "rendered_label.txt"
        if rt_path.exists():
            rendered_text = rt_path.read_text()

        return BenchmarkSample(
            metadata=meta,
            canonical_food=cf,
            ground_truth=gt,
            structured_label=sl,
            rendered_label_text=rendered_text,
            nutrition_facts_json=nf,
        )
    except Exception as e:
        logger.warning("Failed to load sample %s: %s", sample_dir.name, e)
        return None
