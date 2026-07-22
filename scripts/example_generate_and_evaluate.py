"""End-to-end example: generate a benchmark dataset and run baselines."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from synth_bench.benchmark.evaluator import BenchmarkEvaluator
from synth_bench.pipeline.generator import DatasetGenerator, GeneratorConfig
from synth_bench.pipeline.split import split_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a small synthetic benchmark dataset and evaluate baselines.",
    )
    parser.add_argument(
        "--fndds-path",
        required=True,
        type=Path,
        help="Path to FNDDS surveyDownload.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=Path("data/example_benchmark"),
        type=Path,
        help="Output dataset directory.",
    )
    parser.add_argument("--n-samples", default=20, type=int)
    parser.add_argument("--min-ingredients", default=2, type=int)
    parser.add_argument("--max-ingredients", default=30, type=int)
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--max-workers", default=1, type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--exclude-validation-failures",
        action="store_true",
        help="Drop samples that fail final validation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = GeneratorConfig(
        fndds_path=args.fndds_path,
        n_samples=args.n_samples,
        min_ingredients=args.min_ingredients,
        max_ingredients=args.max_ingredients,
        random_seed=args.seed,
        max_workers=args.max_workers,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        include_validation_failures=not args.exclude_validation_failures,
    )

    generator = DatasetGenerator(config)
    generator.load_fndds()
    generator.select_recipes()
    results = generator.generate()

    splits = list(split_dataset(generator.samples, seed=args.seed))
    output_dir = generator.write_dataset(splits=splits)

    evaluator = BenchmarkEvaluator()
    evaluator.load_dataset(output_dir)
    parsing_report = evaluator.run_parsing_baseline()
    mapping_report = evaluator.run_mapping_baseline()

    summary: dict[str, Any] = {
        "generation": {
            "total": len(results),
            "successful": sum(1 for result in results if result.success),
            "failed": sum(1 for result in results if not result.success),
        },
        "parsing_baseline": parsing_report.summary(),
        "mapping_baseline": mapping_report.summary(),
    }
    summary_path = output_dir / "evaluation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Wrote dataset to: {output_dir}")
    print(f"Wrote evaluation summary to: {summary_path}")


if __name__ == "__main__":
    main()
