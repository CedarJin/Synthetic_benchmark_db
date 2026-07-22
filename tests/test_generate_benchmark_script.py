"""Tests for the dataset generation script configuration helpers."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_benchmark.py"
    spec = importlib.util.spec_from_file_location("generate_benchmark", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_generation_config_reads_yaml(tmp_path: Path) -> None:
    module = _load_script_module()
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(
        """
dataset_version: "0.1"
n_samples: 200
include_validation_failures: false
""".strip(),
        encoding="utf-8",
    )

    config = module.load_generation_config(config_path)

    assert config["dataset_version"] == "0.1"
    assert config["n_samples"] == 200
    assert config["include_validation_failures"] is False


def test_build_generator_config_applies_cli_overrides() -> None:
    module = _load_script_module()
    args = argparse.Namespace(
        config=None,
        fndds_path=Path("override/surveyDownload.json"),
        output_dir=None,
        n_samples=50,
        min_ingredients=None,
        max_ingredients=None,
        seed=99,
        max_workers=None,
        overwrite=True,
        include_validation_failures=True,
    )
    file_config = {
        "fndds_path": "from-config/surveyDownload.json",
        "output_dir": "data/benchmark_v0.1",
        "n_samples": 200,
        "random_seed": 42,
        "include_validation_failures": False,
    }

    config = module.build_generator_config(args, file_config)

    assert config.fndds_path == Path("override/surveyDownload.json")
    assert config.output_dir == "data/benchmark_v0.1"
    assert config.n_samples == 50
    assert config.random_seed == 99
    assert config.overwrite is True
    assert config.include_validation_failures is True
