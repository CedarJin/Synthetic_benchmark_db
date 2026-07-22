# Synthetic Benchmark DB

Knowledge-guided synthetic benchmark dataset generation.

This repository is scoped to producing benchmark dataset artifacts from FNDDS survey
food records. It converts source records into canonical recipe objects, applies
label-style transformations, renders ingredient and Nutrition Facts text, validates the
result, and writes sample directories with ground truth. Parser, mapper, model, and
downstream benchmark evaluation work belongs in the later NIP-M workflow.

## Repository Layout

- `src/synth_bench/canonical/`: FNDDS loading and canonical data models.
- `src/synth_bench/knowledge/`: FDA, claim, allergen, and ingredient knowledge.
- `src/synth_bench/knowledge/lexicons/`: versioned ingredient-name lexicons.
- `src/synth_bench/transform/`: transformation engine and label operators.
- `src/synth_bench/llm/`: deterministic label rendering and optional LLM refinement.
- `src/synth_bench/validation/`: validation rules and report generation.
- `src/synth_bench/pipeline/`: dataset generation and splitting.
- `src/synth_bench/benchmark/`: reference-only baseline utilities for development smoke checks.
- `configs/benchmark_v0.1.yaml`: versioned generation config for the first pilot dataset.
- `scripts/generate_benchmark.py`: end-to-end dataset generation example.
- `docs/DATASET_SCHEMA.md`: generated dataset file layout.
- `docs/SMOKE_TEST.md`: latest real-FNDDS smoke test notes.
- `docs/PROJECT_SCOPE.md`: current project boundary and next priorities.
- `docs/INGREDIENT_NAME_AUDIT_V0.1.md`: ingredient-name normalization audit.

## Requirements

- Python 3.12+
- `uv`
- A sibling checkout of `NuSol-T` at `../NuSol-T`
- FNDDS survey JSON, usually `surveyDownload.json`

The local dependency layout is currently:

```text
parent/
  NuSol-T/
  Synthetic_benchmark_db/
```

## Install

```bash
uv sync --all-groups
```

If you use the existing local virtual environment:

```bash
.venv/bin/pytest -q
```

## Quality Checks

```bash
uv run ruff check src tests scripts
uv run mypy src scripts --no-error-summary
uv run pytest -q
```

GitHub Actions runs the same checks on `main` and pull requests.

## Generate a Small Dataset

Use the example script with an FNDDS survey JSON:

```bash
uv run python scripts/generate_benchmark.py \
  --config configs/benchmark_v0.1.yaml \
  --overwrite
```

Command-line options such as `--n-samples`, `--output-dir`, and `--fndds-path` can override config
values for local smoke runs.

The script:

1. Loads FNDDS.
2. Selects recipes.
3. Generates and validates benchmark samples.
4. Writes sample directories and `samples.csv`.
5. Creates train/validation/test split files.
6. Writes `generation_summary.json`.
7. Writes `generation_config.json` with the source and effective config.

## Programmatic Usage

```python
from synth_bench.pipeline.generator import DatasetGenerator, GeneratorConfig

config = GeneratorConfig(
    fndds_path="../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json",
    n_samples=20,
    min_ingredients=2,
    max_ingredients=30,
    max_workers=1,
    output_dir="data/example_benchmark",
    overwrite=True,
)

generator = DatasetGenerator(config)
generator.load_fndds()
generator.select_recipes()
generator.generate()
generator.write_dataset()
```

## Output Schema

Each sample is written as a directory:

```text
sample_000001/
  canonical_food.json
  ground_truth.json
  structured_label.json
  rendered_label.txt
  nutrition_facts.json
  operators.json
  validation.json
  metadata.json
```

See `docs/DATASET_SCHEMA.md` for field-level details and dataset-level files.
See `docs/SMOKE_TEST.md` for the latest real-FNDDS smoke test result.

## Known Limitations

- FDA claim logic is simplified and should not be treated as legal compliance advice.
- Nutrition Facts values use simplified rounding and nutrient-name mappings.
- Allergen detection is keyword/ontology based, not a full ingredient derivation parser.
- Optional LLM refinement is guarded, but deterministic template rendering is the default.
- Reference baseline parser/mapper utilities are not a project deliverable; they are retained only
  for local smoke checks. NIP-M owns parsing, mapping, and downstream model evaluation.
