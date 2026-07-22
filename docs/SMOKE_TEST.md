# Real FNDDS Smoke Test

Smoke test run from local FNDDS survey data:

```bash
PYTHONPATH=src .venv/bin/python scripts/example_generate_and_evaluate.py \
  --fndds-path ../db/FoodData_Central_survey_food_json_2024-10-31/surveyDownload.json \
  --output-dir /tmp/synth_bench_smoke \
  --n-samples 20 \
  --max-workers 1 \
  --overwrite
```

## Result

- FNDDS records loaded: 5,432 foods.
- Recipes with 2+ ingredients: 3,829.
- Samples requested: 20.
- Samples generated: 20.
- Generation failures: 0.
- Output directory: `/tmp/synth_bench_smoke`.

The output directory contained the expected dataset-level files and per-sample files:

- `manifest.json`
- `samples.csv`
- `evaluation_summary.json`
- `splits/train.txt`, `splits/val.txt`, `splits/test.txt`
- `sample_*/canonical_food.json`
- `sample_*/ground_truth.json`
- `sample_*/structured_label.json`
- `sample_*/rendered_label.txt`
- `sample_*/nutrition_facts.json`
- `sample_*/operators.json`
- `sample_*/validation.json`
- `sample_*/metadata.json`

## Baseline Summary

Parsing baseline:

- Mean F1: 0.1637.
- Mean precision: 0.1131.
- Mean recall: 0.3134.
- Exact match: 0.0.

Mapping baseline:

- Recall@5: 0.2878.
- MRR: 0.2878.
- Exact match rate: 0.2878.

## Validation Summary

- Samples with all validation rules passing: 3/20.
- Samples with at least one validation failure: 17/20.

Failure counts by rule:

- `ingredient_order`: 13.
- `nutrition_facts_consistency`: 7.
- `claim_eligibility`: 3.
- `fda_syntax`: 1.
- `prohibited_terminology`: 1.

Observed failure modes:

- Real FNDDS ingredient sequences do not always align with fraction/order assumptions after
  transformations, triggering ingredient-order failures.
- Calories differ by simplified rounding tolerance in several real samples.
- Some generated `FAT FREE` claims remain invalid for foods with nonzero fat per serving.
- Food names or labels containing terms such as `fresh` can trigger the conservative prohibited
  terminology rule.

## Interpretation

The smoke test confirms the end-to-end pipeline runs on real FNDDS data and writes the expected
dataset structure. It also shows that the validation rules are stricter than the current
transformation logic for a sizeable fraction of real samples. Before publishing a benchmark release,
the next technical focus should be calibration of ingredient order, Nutrition Facts tolerance, and
claim eligibility behavior on real FNDDS samples.
