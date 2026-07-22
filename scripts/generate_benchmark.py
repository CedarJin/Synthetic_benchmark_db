"""Generate a synthetic benchmark dataset from FNDDS records."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from synth_bench.pipeline.generator import (
    DatasetGenerator,
    GenerationResult,
    GeneratorConfig,
)
from synth_bench.pipeline.split import split_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic benchmark dataset.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to a versioned YAML generation config.",
    )
    parser.add_argument(
        "--fndds-path",
        type=Path,
        help="Path to FNDDS surveyDownload.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output dataset directory.",
    )
    parser.add_argument("--n-samples", type=int)
    parser.add_argument("--min-ingredients", type=int)
    parser.add_argument("--max-ingredients", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--overwrite", action="store_true")
    validation_group = parser.add_mutually_exclusive_group()
    validation_group.add_argument(
        "--include-validation-failures",
        dest="include_validation_failures",
        action="store_true",
        default=None,
        help="Keep samples that fail final validation.",
    )
    validation_group.add_argument(
        "--exclude-validation-failures",
        dest="include_validation_failures",
        default=None,
        action="store_false",
        help="Drop samples that fail final validation.",
    )
    return parser.parse_args()


def load_generation_config(config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}

    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config_data is None:
        return {}
    if not isinstance(config_data, dict):
        raise ValueError(f"Generation config must contain a mapping: {config_path}")
    return dict(config_data)


def build_generator_config(
    args: argparse.Namespace,
    file_config: dict[str, Any],
) -> GeneratorConfig:
    config_data = dict(file_config)

    cli_overrides = {
        "fndds_path": args.fndds_path,
        "output_dir": args.output_dir,
        "n_samples": args.n_samples,
        "min_ingredients": args.min_ingredients,
        "max_ingredients": args.max_ingredients,
        "random_seed": args.seed,
        "max_workers": args.max_workers,
        "include_validation_failures": args.include_validation_failures,
    }
    if args.overwrite:
        cli_overrides["overwrite"] = True

    for key, value in cli_overrides.items():
        if value is not None:
            config_data[key] = value

    config_data.setdefault("fndds_path", "")
    config_data.setdefault("output_dir", "data/example_benchmark")
    config_data.setdefault("n_samples", 20)
    config_data.setdefault("min_ingredients", 2)
    config_data.setdefault("max_ingredients", 30)
    config_data.setdefault("random_seed", 42)
    config_data.setdefault("max_workers", 1)
    config_data.setdefault("include_validation_failures", True)

    generator_keys = GeneratorConfig.__dataclass_fields__.keys()
    generator_config = {key: value for key, value in config_data.items() if key in generator_keys}

    config = GeneratorConfig(**generator_config)
    if not config.fndds_path:
        raise ValueError("FNDDS path not provided. Use --fndds-path or a config file.")
    return config


def build_summary(results: list[GenerationResult]) -> dict[str, Any]:
    successful = [result for result in results if result.success]
    failed = [result for result in results if not result.success]
    validation_reports = [
        result.sample.validation
        for result in successful
        if result.sample is not None and result.sample.validation is not None
    ]
    validation_passed = sum(1 for report in validation_reports if report.get("all_passed"))

    return {
        "generation": {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": round(len(successful) / len(results), 4) if results else 0.0,
        },
        "validation": {
            "reports": len(validation_reports),
            "all_passed": validation_passed,
            "failed": len(validation_reports) - validation_passed,
        },
        "failures": [
            {
                "sample_id": result.sample_id,
                "fdc_id": result.fdc_id,
                "error": result.error,
            }
            for result in failed
        ],
    }


def build_config_snapshot(
    config: GeneratorConfig,
    source_config: dict[str, Any],
    config_path: Path | None,
) -> dict[str, Any]:
    return {
        "config_path": str(config_path) if config_path is not None else None,
        "source_config": source_config,
        "effective_config": {
            "fndds_path": str(config.fndds_path),
            "n_samples": config.n_samples,
            "min_ingredients": config.min_ingredients,
            "max_ingredients": config.max_ingredients,
            "random_seed": config.random_seed,
            "operators": config.operators,
            "operator_config": config.operator_config,
            "enable_validation": config.enable_validation,
            "auto_repair": config.auto_repair,
            "enable_llm_refinement": config.enable_llm_refinement,
            "llm_model": config.llm_model,
            "output_dir": str(config.output_dir),
            "overwrite": config.overwrite,
            "include_validation_failures": config.include_validation_failures,
            "max_workers": config.max_workers,
        },
    }


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    file_config = load_generation_config(args.config)
    config = build_generator_config(args, file_config)

    generator = DatasetGenerator(config)
    generator.load_fndds()
    generator.select_recipes()
    results = generator.generate()

    splits = list(split_dataset(generator.samples, seed=config.random_seed))
    output_dir = generator.write_dataset(splits=splits)

    summary = build_summary(results)
    if args.config is not None:
        summary["config_path"] = str(args.config)
    if "dataset_version" in file_config:
        summary["dataset_version"] = file_config["dataset_version"]

    summary_path = output_dir / "generation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    config_snapshot_path = output_dir / "generation_config.json"
    config_snapshot = build_config_snapshot(config, file_config, args.config)
    config_snapshot_path.write_text(json.dumps(config_snapshot, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Wrote dataset to: {output_dir}")
    print(f"Wrote generation summary to: {summary_path}")
    print(f"Wrote generation config snapshot to: {config_snapshot_path}")


if __name__ == "__main__":
    main()
