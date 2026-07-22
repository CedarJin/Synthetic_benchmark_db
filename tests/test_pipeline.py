"""Tests for the dataset generation pipeline and split logic."""

# ruff: noqa: E501

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from synth_bench.canonical.models import (
    BenchmarkSample,
    CanonicalFood,
    CanonicalIngredient,
    GroundTruth,
    SampleMetadata,
    StructuredLabel,
)
from synth_bench.pipeline.generator import DatasetGenerator, GeneratorConfig
from synth_bench.pipeline.split import DatasetSplit, split_dataset

# ═══════════════════════════════════════════════════════════════════════════════
# DatasetSplit
# ═══════════════════════════════════════════════════════════════════════════════


class TestDatasetSplit:
    """DatasetSplit basic functionality."""

    def test_empty_split(self) -> None:
        split = DatasetSplit(name="test")
        assert len(split) == 0

    def test_with_samples(self) -> None:
        ing = CanonicalIngredient(ingredient_code=1, description="X", weight_g=100.0, fraction=1.0, sequence_number=1)
        food = CanonicalFood(fdc_id=1, food_name="Test", ingredients=[ing])
        sample = BenchmarkSample(
            metadata=SampleMetadata(sample_id="s1"),
            canonical_food=food,
            ground_truth=GroundTruth(canonical_food=food),
            structured_label=StructuredLabel(),
        )
        split = DatasetSplit(name="train", samples=[sample])
        assert len(split) == 1
        assert split.fdc_ids == {1}


# ═══════════════════════════════════════════════════════════════════════════════
# split_dataset
# ═══════════════════════════════════════════════════════════════════════════════


class TestSplitDataset:
    """Dataset splitting by FDC ID."""

    @pytest.fixture
    def samples(self) -> list[BenchmarkSample]:
        """10 samples from 4 unique FDC IDs."""
        result = []
        for i, fdc_id in enumerate([101, 101, 102, 102, 103, 103, 104, 104, 105, 105]):
            ing = CanonicalIngredient(ingredient_code=i, description=f"Ing{i}", weight_g=100.0, fraction=1.0, sequence_number=1)
            food = CanonicalFood(fdc_id=fdc_id, food_name=f"Food{fdc_id}", ingredients=[ing])
            result.append(BenchmarkSample(
                metadata=SampleMetadata(sample_id=f"s{i:03d}"),
                canonical_food=food,
                ground_truth=GroundTruth(canonical_food=food),
                structured_label=StructuredLabel(),
            ))
        return result

    def test_split_preserves_all_samples(self, samples: list[BenchmarkSample]) -> None:
        train, val, test = split_dataset(samples)
        total = len(train) + len(val) + len(test)
        assert total == len(samples)

    def test_no_fdc_overlap(self, samples: list[BenchmarkSample]) -> None:
        train, val, test = split_dataset(samples)
        # No FDC ID should appear in two splits
        assert train.fdc_ids.isdisjoint(val.fdc_ids)
        assert train.fdc_ids.isdisjoint(test.fdc_ids)
        assert val.fdc_ids.isdisjoint(test.fdc_ids)

    def test_split_fixed_seed(self, samples: list[BenchmarkSample]) -> None:
        """Same seed → same split."""
        t1, v1, te1 = split_dataset(samples, seed=42)
        t2, v2, te2 = split_dataset(samples, seed=42)
        assert set(s.metadata.sample_id for s in t1.samples) == set(s.metadata.sample_id for s in t2.samples)
        assert set(s.metadata.sample_id for s in v1.samples) == set(s.metadata.sample_id for s in v2.samples)

    def test_split_ratios(self, samples: list[BenchmarkSample]) -> None:
        train, val, test = split_dataset(samples, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        assert len(train) > len(val)
        assert len(test) > 0

    def test_invalid_ratios(self, samples: list[BenchmarkSample]) -> None:
        with pytest.raises(ValueError, match="must sum"):
            split_dataset(samples, train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# GeneratorConfig
# ═══════════════════════════════════════════════════════════════════════════════


class TestGeneratorConfig:
    """GeneratorConfig defaults."""

    def test_defaults(self) -> None:
        config = GeneratorConfig()
        assert config.n_samples == 200
        assert config.min_ingredients == 2
        assert config.random_seed == 42
        assert config.max_workers == 4
        assert config.enable_validation

    def test_custom(self) -> None:
        config = GeneratorConfig(n_samples=10, random_seed=123, max_workers=2)
        assert config.n_samples == 10
        assert config.random_seed == 123
        assert config.max_workers == 2


# ═══════════════════════════════════════════════════════════════════════════════
# DatasetGenerator — with synthetic FNDDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDatasetGenerator:
    """DatasetGenerator with synthetic FNDDS fixture."""

    def test_load_fndds(self, synthetic_fndds_path: Path) -> None:
        config = GeneratorConfig(fndds_path=str(synthetic_fndds_path), n_samples=2)
        gen = DatasetGenerator(config)
        gen.load_fndds()
        assert gen._fndds_loader is not None
        assert len(gen._fndds_loader) == 2

    def test_select_recipes(self, synthetic_fndds_path: Path) -> None:
        config = GeneratorConfig(fndds_path=str(synthetic_fndds_path), n_samples=2)
        gen = DatasetGenerator(config)
        gen.load_fndds()
        ids = gen.select_recipes()
        assert len(ids) == 2
        assert all(isinstance(i, int) for i in ids)

    def test_select_recipes_too_many_raises(self, synthetic_fndds_path: Path) -> None:
        """Only 2 recipes available, requesting 5 should raise."""
        config = GeneratorConfig(fndds_path=str(synthetic_fndds_path), n_samples=5)
        gen = DatasetGenerator(config)
        gen.load_fndds()
        with pytest.raises(ValueError, match="cannot sample"):
            gen.select_recipes()

    def test_generate_small(self, synthetic_fndds_path: Path) -> None:
        """Generate 2 samples from synthetic fixture."""
        config = GeneratorConfig(
            fndds_path=str(synthetic_fndds_path),
            n_samples=2,
            max_workers=1,
            output_dir="/tmp/test_synth_bench",
            overwrite=True,
        )
        gen = DatasetGenerator(config)
        gen.load_fndds()
        gen.select_recipes()
        results = gen.generate()

        assert len(results) == 2
        assert all(r.success for r in results)
        assert len(gen.samples) == 2

    def test_generate_output_files(self, synthetic_fndds_path: Path) -> None:
        """Verify output files for generated samples."""
        config = GeneratorConfig(
            fndds_path=str(synthetic_fndds_path),
            n_samples=2,
            max_workers=1,
            output_dir="/tmp/test_synth_files",
            overwrite=True,
        )
        gen = DatasetGenerator(config)
        gen.load_fndds()
        gen.select_recipes()
        gen.generate()
        out_dir = gen.write_dataset()

        try:
            # Check sample directories
            sample_dirs = sorted([d for d in out_dir.iterdir() if d.is_dir()])
            assert len(sample_dirs) == 2

            for sd in sample_dirs:
                expected_files = {
                    "canonical_food.json", "ground_truth.json", "structured_label.json",
                    "rendered_label.txt", "nutrition_facts.json", "operators.json",
                    "validation.json", "metadata.json",
                }
                actual_files = {f.name for f in sd.iterdir() if f.is_file()}
                assert expected_files.issubset(actual_files), f"Missing files in {sd.name}: {expected_files - actual_files}"

                # Check that JSON files are valid
                for jf in ["canonical_food.json", "metadata.json", "structured_label.json"]:
                    with open(sd / jf) as f:
                        data = json.load(f)
                    assert data is not None, f"Invalid JSON in {sd.name}/{jf}"

                # Check rendered_label.txt
                with open(sd / "rendered_label.txt") as f:
                    text = f.read()
                assert len(text) > 0

            # Check manifest
            with open(out_dir / "manifest.json") as f:
                manifest = json.load(f)
            assert manifest["summary"]["successful"] == 2
            assert manifest["summary"]["total_samples"] == 2
            assert manifest["config"]["random_seed"] == 42

            # Check samples.csv
            csv_path = out_dir / "samples.csv"
            assert csv_path.exists()
            csv_content = csv_path.read_text()
            assert "sample_id,fdc_id,food_name" in csv_content
            assert csv_content.count("\n") == 3  # header + 2 samples

        finally:
            shutil.rmtree(out_dir)

    def test_overwrite_flag(self, synthetic_fndds_path: Path) -> None:
        """Without overwrite, writing to existing dir should fail."""
        out_dir = Path("/tmp/test_overwrite")
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            config = GeneratorConfig(
                fndds_path=str(synthetic_fndds_path),
                n_samples=2, max_workers=1,
                output_dir=str(out_dir),
                overwrite=False,
            )
            gen = DatasetGenerator(config)
            gen.load_fndds()
            gen.select_recipes()
            gen.generate()

            with pytest.raises(FileExistsError):
                gen.write_dataset()
        finally:
            shutil.rmtree(out_dir)

    def test_generate_with_fdc_ids(self, synthetic_fndds_path: Path) -> None:
        """Generate directly from FDC IDs without select_recipes()."""
        config = GeneratorConfig(
            fndds_path=str(synthetic_fndds_path),
            max_workers=1,
        )
        gen = DatasetGenerator(config)
        gen.load_fndds()
        results = gen.generate(fdc_ids=[2705384])
        assert len(results) == 1
        assert results[0].success
        assert results[0].fdc_id == 2705384

    def test_missing_fndds_raises(self) -> None:
        config = GeneratorConfig()
        gen = DatasetGenerator(config)
        with pytest.raises(RuntimeError, match="not loaded"):
            gen.select_recipes()
