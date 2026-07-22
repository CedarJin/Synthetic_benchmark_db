"""Tests for benchmarking (parsing/mapping metrics, baselines, evaluator)."""

from __future__ import annotations

import pytest

from synth_bench.benchmark.baselines import (
    baseline_bm25_mapper,
    baseline_dictionary_mapper,
    baseline_parse_ingredients,
    build_ingredient_dictionary,
)
from synth_bench.benchmark.evaluator import (
    BenchmarkEvaluator,
    EvaluationReport,
    SampleResult,
)
from synth_bench.benchmark.metrics import (
    compute_mapping_metrics,
    compute_ordered_parsing_metrics,
    compute_parsing_metrics,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Parsing Metrics
# ═══════════════════════════════════════════════════════════════════════════════


class TestParsingMetrics:
    """Parsing metric computation."""

    def test_perfect_match(self) -> None:
        metrics = compute_parsing_metrics(
            {"FLOUR", "SUGAR", "SALT"},
            {"FLOUR", "SUGAR", "SALT"},
        )
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["exact_match"] == 1.0
        assert metrics["iou"] == 1.0

    def test_no_match(self) -> None:
        metrics = compute_parsing_metrics(
            {"FLOUR", "SUGAR"},
            {"MILK", "EGGS"},
        )
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_partial_match(self) -> None:
        metrics = compute_parsing_metrics(
            {"FLOUR", "SUGAR", "SALT"},
            {"FLOUR", "MILK"},
        )
        assert metrics["precision"] == 0.5  # 1/2
        assert metrics["recall"] == pytest.approx(1.0 / 3.0, abs=0.001)  # 1/3
        assert metrics["f1"] > 0.0
        assert metrics["iou"] == 1.0 / 4.0  # 1/4

    def test_empty_ground_truth(self) -> None:
        metrics = compute_parsing_metrics(set(), {"A"})
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_order_accuracy(self) -> None:
        metrics = compute_ordered_parsing_metrics(
            ["FLOUR", "SUGAR", "SALT"],
            ["FLOUR", "MILK", "SALT"],
        )
        assert metrics["order_accuracy"] == pytest.approx(
            2.0 / 3.0, abs=0.001
        )  # 2 of 3 correct positions
        assert metrics["order_correct_positions"] == 2

    def test_parsing_metrics_normalize_case(self) -> None:
        metrics = compute_ordered_parsing_metrics(["MILK"], ["milk"])
        assert metrics["f1"] == 1.0
        assert metrics["order_accuracy"] == 1.0

    def test_order_accuracy_empty_lists(self) -> None:
        metrics = compute_ordered_parsing_metrics([], [])
        assert metrics["order_accuracy"] == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Mapping Metrics
# ═══════════════════════════════════════════════════════════════════════════════


class TestMappingMetrics:
    """Mapping metric computation."""

    def test_perfect_mapping(self) -> None:
        metrics = compute_mapping_metrics(
            {"FLOUR": "1001", "SUGAR": "1002"},
            {"FLOUR": ["1001", "1003"], "SUGAR": ["1002", "1004"]},
            k=5,
        )
        assert metrics["recall_at_5"] == 1.0
        assert metrics["mrr"] == 1.0
        assert metrics["exact_match_rate"] == 1.0

    def test_no_mapping(self) -> None:
        metrics = compute_mapping_metrics(
            {"FLOUR": "1001"},
            {"FLOUR": ["9999", "8888"]},
            k=5,
        )
        assert metrics["recall_at_5"] == 0.0
        assert metrics["mrr"] == 0.0
        assert metrics["exact_match_rate"] == 0.0

    def test_recall_at_k(self) -> None:
        """Correct ID in 3rd position should hit Recall@5 but not Recall@1."""
        metrics = compute_mapping_metrics(
            {"FLOUR": "1001"},
            {"FLOUR": ["9999", "8888", "1001"]},
            k=5,
        )
        assert metrics["recall_at_5"] == 1.0  # found at position 3
        assert metrics["mrr"] == pytest.approx(1.0 / 3.0, abs=0.001)  # 1/3

    def test_empty_ground_truth(self) -> None:
        metrics = compute_mapping_metrics({}, {})
        assert metrics["recall_at_5"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Baseline Parser
# ═══════════════════════════════════════════════════════════════════════════════


class TestBaselineParser:
    """Baseline regex parser tests."""

    def test_simple_list(self) -> None:
        result = baseline_parse_ingredients("INGREDIENTS: FLOUR, SUGAR, SALT.")
        assert result == ["FLOUR", "SUGAR", "SALT"]

    def test_with_compound(self) -> None:
        result = baseline_parse_ingredients("INGREDIENTS: CHOCOLATE (COCOA MASS, SUGAR), FLOUR.")
        assert "CHOCOLATE" in result
        assert "FLOUR" in result
        assert len(result) == 2  # sub-ingredients not as separate items

    def test_with_two_percent_group(self) -> None:
        result = baseline_parse_ingredients(
            "INGREDIENTS: SALT, SPICES. CONTAINS 2% OR LESS OF: SILICA."
        )
        assert "SALT" in result
        assert "SPICES" in result
        assert "SILICA" in result

    def test_with_allergens(self) -> None:
        result = baseline_parse_ingredients(
            "INGREDIENTS: WHEAT FLOUR, EGGS. CONTAINS: WHEAT, EGGS."
        )
        assert "WHEAT FLOUR" in result
        assert "EGGS" in result
        assert len(result) == 2  # allergens not counted as ingredients

    def test_empty_input(self) -> None:
        assert baseline_parse_ingredients("") == []
        assert baseline_parse_ingredients(None) == []

    def test_no_ingredients_header(self) -> None:
        result = baseline_parse_ingredients("MILK, SUGAR.")
        assert result == ["MILK", "SUGAR"]


# ═══════════════════════════════════════════════════════════════════════════════
# Baseline Mapper
# ═══════════════════════════════════════════════════════════════════════════════


class TestBaselineMapper:
    """Baseline dictionary/BM25 mapper tests."""

    def test_dictionary_lookup(self) -> None:
        dictionary = {"milk": "MILK_STD", "sugar": "SUGAR_STD"}
        result = baseline_dictionary_mapper(
            ["MILK", "SUGAR"],
            dictionary=dictionary,
        )
        assert result["MILK"][0] == "MILK_STD"
        assert result["SUGAR"][0] == "SUGAR_STD"

    def test_unknown_ingredient(self) -> None:
        dictionary = {"milk": "MILK_STD"}
        result = baseline_dictionary_mapper(
            ["XYZ_UNKNOWN"],
            dictionary=dictionary,
        )
        assert result["XYZ_UNKNOWN"] == []

    def test_build_dictionary(self) -> None:
        d = build_ingredient_dictionary()
        assert len(d) > 100  # lots of entries
        # Known entries should be present
        assert "milk" in d or "milk, whole" in d

    def test_bm25_mapper(self) -> None:
        dictionary = {"milk": "MILK_STD", "whole milk": "WHOLE_MILK_STD"}
        result = baseline_bm25_mapper(
            ["WHOLE MILK"],
            dictionary=dictionary,
        )
        # Should prefer "whole milk" over "milk" due to higher overlap
        assert len(result["WHOLE MILK"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Evaluation Report
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvaluationReport:
    """EvaluationReport aggregation."""

    def test_aggregate_by_difficulty(self) -> None:
        from synth_bench.canonical.models import DifficultyLevel

        report = EvaluationReport()
        report.parsing_results = [
            SampleResult(
                sample_id="a",
                difficulty=DifficultyLevel.EASY,
                fdc_id=1,
                applied_operators=["rename"],
                parsing_metrics={"f1": 0.9, "precision": 1.0},
            ),
            SampleResult(
                sample_id="b",
                difficulty=DifficultyLevel.EASY,
                fdc_id=2,
                applied_operators=["rename"],
                parsing_metrics={"f1": 0.7, "precision": 0.8},
            ),
            SampleResult(
                sample_id="c",
                difficulty=DifficultyLevel.HARD,
                fdc_id=3,
                applied_operators=["compound", "rename"],
                parsing_metrics={"f1": 0.5, "precision": 0.6},
            ),
        ]

        by_diff = report.aggregate_parsing_by_difficulty()
        assert "EASY" in by_diff
        assert "HARD" in by_diff
        assert by_diff["EASY"]["f1"] == 0.8  # (0.9 + 0.7) / 2
        assert by_diff["HARD"]["f1"] == 0.5

    def test_summary(self) -> None:
        report = EvaluationReport(parser_name="test", mapper_name="test")
        report.parsing_results = [
            SampleResult(
                sample_id="a",
                difficulty=1,
                fdc_id=1,
                applied_operators=[],
                parsing_metrics={"f1": 0.8},
            ),
        ]
        report.mapping_results = [
            SampleResult(
                sample_id="a",
                difficulty=1,
                fdc_id=1,
                applied_operators=[],
                mapping_metrics={"recall_at_5": 0.7},
            ),
        ]
        s = report.summary()
        assert s["parsing"]["f1"] == 0.8
        assert s["mapping"]["recall_at_5"] == 0.7
        assert s["n_samples"] == 1

    def test_mapping_only_summary(self) -> None:
        from synth_bench.canonical.models import DifficultyLevel

        report = EvaluationReport(mapper_name="mapper")
        report.mapping_results = [
            SampleResult(
                sample_id="a",
                difficulty=DifficultyLevel.EASY,
                fdc_id=1,
                applied_operators=[],
                mapping_metrics={"mrr": 1.0},
            ),
        ]
        s = report.summary()
        assert s["parsing"] == {}
        assert s["mapping"]["mrr"] == 1.0
        assert s["n_mapping_samples"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Evaluator
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarkEvaluator:
    """BenchmarkEvaluator loading and evaluation."""

    def test_load_missing_raises(self) -> None:
        evaluator = BenchmarkEvaluator()
        with pytest.raises(FileNotFoundError):
            evaluator.load_dataset("/nonexistent/path")

    def test_load_from_generated_dataset(self) -> None:
        """Generate a small dataset, then load and evaluate it."""
        import shutil

        from synth_bench.pipeline.generator import DatasetGenerator, GeneratorConfig

        config = GeneratorConfig(
            fndds_path="../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json",
            n_samples=2,
            min_ingredients=3,
            max_ingredients=8,
            max_workers=1,
            output_dir="/tmp/test_eval_dataset",
            overwrite=True,
        )
        gen = DatasetGenerator(config)
        gen.load_fndds()
        gen.select_recipes()
        gen.generate()
        out_dir = gen.write_dataset()

        try:
            evaluator = BenchmarkEvaluator()
            n = evaluator.load_dataset(out_dir)
            assert n == 2

            # Run parsing baseline
            report = evaluator.run_parsing_baseline()
            assert len(report.parsing_results) == 2
            assert report.parser_name == "regex_baseline"

            # Check some parsing metrics exist
            for result in report.parsing_results:
                assert "precision" in result.parsing_metrics
                assert "recall" in result.parsing_metrics
                assert "f1" in result.parsing_metrics

            # Run mapping baseline
            mreport = evaluator.run_mapping_baseline()
            assert len(mreport.mapping_results) == 2
            assert mreport.mapper_name == "dictionary_baseline"

            # Summary should have data
            s = report.summary()
            assert "parsing" in s
            assert s["n_samples"] == 2

        finally:
            shutil.rmtree(out_dir)
