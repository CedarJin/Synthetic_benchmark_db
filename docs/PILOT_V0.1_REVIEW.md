# Benchmark v0.1 Pilot Review

## Run

The 200-sample pilot was generated with the checked-in config:

```bash
.venv/bin/python scripts/generate_benchmark.py \
  --config configs/benchmark_v0.1.yaml \
  --overwrite
```

Output directory:

```text
data/benchmark_v0.1
```

The `data/` directory is git-ignored, so the generated pilot dataset is a local artifact rather
than a repository commit.

## Result

- FNDDS records loaded: 5,432 foods.
- Recipes with 2+ ingredients: 3,829.
- Samples requested: 200.
- Samples generated: 200.
- Generation failures: 0.
- Samples with all validation rules passing: 200/200.
- Split counts: 140 train, 30 validation, 30 test.
- Unique split sample IDs: 200.
- Duplicate split sample IDs: 0.

Aggregate artifact checks:

- Sample directories: 200.
- `samples.csv` rows: 200.
- Ingredient count range: 2-16.
- Mean ingredient count: 4.14.
- Validation failures: 0.
- Bad source-claim patterns found after fixes: 0.
- Lettuce mismatches after fixes: 0.
- Non-compound declared ingredient names with internal commas after fixes: 0.
- Labels with comma-attached allergen declarations after fixes: 0.

## Issues Found And Fixed

Three data-quality issues surfaced during inspection.

First, the generic-name operator could map `Butter oil, anhydrous` to `LETTUCE`. The root cause was
an ambiguous single-word mapping, `Butter -> LETTUCE`, combined with unconstrained word-level
genericization. The fix removed dangerous single-word variety mappings and changed
`GenericNameOperator` so single-word substitutions are only accepted when the declared name also
contains the target ingredient category.

Second, source claims were generated for nutrients that should not be promoted as positive
`GOOD SOURCE OF` or `EXCELLENT SOURCE OF` claims, such as sodium, cholesterol, total lipid, fatty
acids, and carbohydrate. The fix restricts source claims to a whitelist of suitable display
nutrients: protein, dietary fiber, vitamin D, calcium, iron, and potassium.

Third, FNDDS ingredient descriptions with internal commas were being used directly as label
ingredient names, making text such as `YOGURT, GREEK, PLAIN, NONFAT` look like four separate
ingredients. The fix added comma-free label-safe ingredient normalization, expanded exact commercial
name mappings for common FNDDS descriptions, and renders allergen declarations as separate
sentences instead of comma-attached ingredient-list items.

Regression tests were added for these issues.

## Remaining Observations

- All 200 samples currently have difficulty value `2`, so difficulty may not yet be informative for
  dataset stratification.
- `structured_label.json` uses `allergens: null` when no allergen declaration is present. This is
  acceptable for now, but the release schema should state the nullable behavior explicitly.
- Health-claim frequency is high in this pilot. The next quality pass should decide whether claims
  should be capped or sampled to improve label diversity.
- Some fallback-normalized FNDDS ingredient names may still be long and survey-like. More exact
  commercial-name mappings may be needed before release.

## Verification

Local checks after fixes:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/mypy src scripts --no-error-summary
.venv/bin/pytest -q
```

Latest result:

- `ruff`: passed.
- `mypy`: passed.
- `pytest`: 233 passed.
