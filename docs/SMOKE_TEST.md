# Real FNDDS Smoke Test

Smoke test run from local FNDDS survey data:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_benchmark.py \
  --fndds-path ../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json \
  --output-dir /tmp/synth_bench_smoke_50 \
  --n-samples 50 \
  --max-workers 1 \
  --overwrite
```

## Result

- FNDDS records loaded: 5,432 foods.
- Recipes with 2+ ingredients: 3,829.
- Samples requested: 50.
- Samples generated: 50.
- Generation failures: 0.
- Samples with all validation rules passing: 50/50.
- Samples with at least one validation failure: 0/50.
- Output directory: `/tmp/synth_bench_smoke_50`.

The output directory contained the expected dataset-level files and per-sample files:

- `manifest.json`
- `samples.csv`
- `generation_summary.json`
- `splits/train.txt`, `splits/val.txt`, `splits/test.txt`
- `sample_*/canonical_food.json`
- `sample_*/ground_truth.json`
- `sample_*/structured_label.json`
- `sample_*/rendered_label.txt`
- `sample_*/nutrition_facts.json`
- `sample_*/operators.json`
- `sample_*/validation.json`
- `sample_*/metadata.json`

## Reference-Only Baseline Summary

These numbers came from the older development smoke workflow. They are not success criteria for
this repository because parsing and mapping are downstream NIP-M responsibilities.

Parsing baseline:

- Mean F1: 0.1246.
- Mean precision: 0.0849.
- Mean recall: 0.2442.
- Exact match: 0.0.

Mapping baseline:

- Recall@5: 0.2357.
- MRR: 0.2346.
- Exact match rate: 0.2341.

## Validation Fixes From Smoke Testing

Initial 20-sample smoke testing exposed several validation failures. The current run validates
cleanly after these fixes:

- Ingredient labels are initialized in descending ingredient-fraction order instead of trusting
  FNDDS sequence order.
- Ingredient-order validation now checks label fraction order and two-percent grouping, not raw
  FNDDS sequence order.
- Nutrition Facts validation uses the same serving-size selection and FDA rounding path as
  generation.
- Claim validation distinguishes `SATURATED FAT FREE` from total-fat `FAT FREE`.
- Allergen validation uses structured allergen declarations before parsing declaration text, so
  `CRUSTACEAN SHELLFISH` no longer implies `fish`.
- Over-broad prohibited-term checks for ingredient descriptors such as `fresh` and `imitation`
  were removed.

## Interpretation

The smoke test confirms the end-to-end pipeline runs on real FNDDS data, writes the expected
dataset structure, and passes the current validation rules on a 50-sample real-data run.
