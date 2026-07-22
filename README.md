# Synthetic Benchmark DB

Knowledge-guided synthetic benchmark generation for ingredient parsing and mapping.

The project converts FNDDS survey food records into canonical recipe objects, applies
label-style transformations, renders ingredient and Nutrition Facts text, validates the
result, and writes benchmark samples with ground truth for parsing and mapping tasks.

## Repository Layout

- `src/synth_bench/canonical/`: FNDDS loading and canonical data models.
- `src/synth_bench/knowledge/`: FDA, claim, allergen, and ingredient knowledge.
- `src/synth_bench/transform/`: transformation engine and label operators.
- `src/synth_bench/llm/`: deterministic label rendering and optional LLM refinement.
- `src/synth_bench/validation/`: validation rules and report generation.
- `src/synth_bench/pipeline/`: dataset generation and splitting.
- `src/synth_bench/benchmark/`: baseline parsers/mappers and evaluation metrics.
- `scripts/example_generate_and_evaluate.py`: end-to-end generation and evaluation example.
- `docs/DATASET_SCHEMA.md`: generated dataset file layout.
- `docs/SMOKE_TEST.md`: latest real-FNDDS smoke test notes.

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

## Generate and Evaluate a Small Dataset

Use the example script with an FNDDS survey JSON:

```bash
uv run python scripts/example_generate_and_evaluate.py \
  --fndds-path ../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json \
  --output-dir data/example_benchmark \
  --n-samples 20 \
  --max-workers 1 \
  --overwrite
```

The script:

1. Loads FNDDS.
2. Selects recipes.
3. Generates and validates benchmark samples.
4. Writes sample directories and `samples.csv`.
5. Creates train/validation/test split files.
6. Runs regex parsing and dictionary mapping baselines.
7. Writes `evaluation_summary.json`.

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
- Mapping evaluation currently targets canonical FNDDS ingredient descriptions for the
  built-in baselines, while numeric ingredient codes are retained in `ground_truth.json`.
