# Dataset Card: synthetic_benchmark_db_v0.1

## Summary

`synthetic_benchmark_db_v0.1` is a generated benchmark dataset for food-label ingredient
declarations and Nutrition Facts artifacts. It is produced from FNDDS survey food records and is
intended as input data for downstream NIP-M parsing, mapping, and reconstruction workflows.

This repository generates the dataset. It does not train parsers, build mappers, or report model
leaderboards.

## Source Data

Primary source:

- FNDDS survey JSON: `surveyDownload.json`
- Local path used for pilot generation:
  `../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json`
- FNDDS publication date in the inspected source entries: `10/31/2024`

The generator loads FNDDS survey foods, input-food ingredient weights, portions, and nutrient values
into canonical recipe objects before transformation.

## Generation Configuration

Checked-in config:

```text
configs/benchmark_v0.1.yaml
```

Key settings:

- `dataset_version`: `0.1`
- `dataset_name`: `synthetic_benchmark_db_v0.1`
- `ingredient_name_lexicon_version`: `0.1`
- `n_samples`: `200`
- `min_ingredients`: `2`
- `max_ingredients`: `30`
- `random_seed`: `42`
- `enable_validation`: `true`
- `auto_repair`: `true`
- `include_validation_failures`: `false`
- `enable_llm_refinement`: `false`

The default v0.1 workflow is deterministic. It uses fixed code, a fixed config, and a reviewed
ingredient-name lexicon. It does not call an LLM during dataset generation.

## Ingredient Name Lexicon

Reviewed lexicon:

```text
src/synth_bench/knowledge/lexicons/ingredient_names_v0.1.yaml
```

Purpose:

- Convert FNDDS ingredient descriptions into concise label ingredient names.
- Remove survey-only qualifiers where possible.
- Preserve ingredient identity for downstream ground truth alignment.
- Avoid invented brand names.

Example mappings:

| FNDDS ingredient description | Label ingredient name |
| --- | --- |
| `Flour, wheat, all-purpose, enriched, bleached` | `ENRICHED WHEAT FLOUR` |
| `Chicken, NS as to part, rotisserie, skin not eaten` | `ROTISSERIE CHICKEN` |
| `Eggs, Grade A, Large, egg yolk` | `EGG YOLK` |
| `Spices, basil, dried` | `DRIED BASIL` |

If no exact lexicon or built-in commercial-name mapping exists, the fallback normalizer removes
FNDDS internal commas and uppercases the result.

## Generated Artifacts

Each dataset root contains:

- `manifest.json`
- `samples.csv`
- `generation_summary.json`
- `generation_config.json`
- `splits/train.txt`
- `splits/val.txt`
- `splits/test.txt`
- one `sample_*` directory per generated sample

Each sample directory contains:

- `canonical_food.json`
- `ground_truth.json`
- `structured_label.json`
- `rendered_label.txt`
- `nutrition_facts.json`
- `operators.json`
- `validation.json`
- `metadata.json`

See `docs/DATASET_SCHEMA.md` for file-level details.

## Validation Coverage

The generator validates final rendered outputs after transformation and label rendering.

Current validation areas:

- Ingredient preservation.
- Ingredient order and two-percent grouping.
- FDA-style syntax checks.
- Allergen declaration consistency.
- Claim eligibility.
- Nutrition Facts consistency.
- Prohibited terminology checks.

Latest pilot result:

- Samples requested: 200.
- Samples generated: 200.
- Generation failures: 0.
- Samples with all validation rules passing: 200/200.
- Split counts: 140 train, 30 validation, 30 test.

See `docs/PILOT_V0.1_REVIEW.md` for the pilot inspection record.

## Intended Use

This dataset is intended for:

- NIP-M downstream parser development.
- NIP-M downstream ingredient mapping evaluation.
- Ground-truth-aware testing of label-to-canonical-food workflows.
- Regression testing for synthetic benchmark generation changes.

## Out Of Scope

This dataset card does not claim:

- Legal compliance with FDA labeling regulations.
- Coverage of all branded-food label styles.
- A complete commercial ingredient-name dictionary.
- Production-grade parser or mapper performance.
- Model ranking or leaderboard validity.

## Known Limitations

- FDA claim logic and Nutrition Facts rounding are simplified.
- Health-claim frequency is high in the v0.1 pilot and may need capping or sampling.
- Some fallback-normalized ingredient names remain long or survey-like.
- `structured_label.json` may use `allergens: null` when no allergen declaration is present.
- Difficulty values are not yet useful for stratification; the v0.1 pilot produced all samples at
  difficulty value `2`.
- The project currently assumes a sibling `../NuSol-T` checkout for the local `nusol` dependency.
- Generated dataset artifacts are local under `data/` and are not committed to the repository.

## Reproducibility

To regenerate the v0.1 pilot locally:

```bash
.venv/bin/python scripts/generate_benchmark.py \
  --config configs/benchmark_v0.1.yaml \
  --overwrite
```

The output directory is:

```text
data/benchmark_v0.1
```

The generated `generation_config.json` records the source config and final effective config.

## Handoff To NIP-M

The key downstream handoff files are:

- `rendered_label.txt`: primary label text for downstream parsers.
- `structured_label.json`: structured declared ingredient names, two-percent grouping, claims,
  allergens, and Nutrition Facts.
- `ground_truth.json`: canonical mappings, target mappings, ingredient amounts/fractions,
  transformation history, and validation report.
- `canonical_food.json`: source canonical representation derived from FNDDS.

NIP-M should treat this repository as the dataset producer and own parsing, mapping, model
evaluation, and reporting downstream.
