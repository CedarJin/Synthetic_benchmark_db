# Dataset Schema

Generated datasets are directory based. A dataset root contains one directory per sample
plus index and manifest files.

```text
dataset_root/
  manifest.json
  samples.csv
  evaluation_summary.json        # only when produced by the example script
  splits/
    train.txt
    val.txt
    test.txt
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

## Dataset-Level Files

`manifest.json`

- `dataset_name`: dataset label.
- `generated_at`: UTC timestamp.
- `config`: generator configuration used for the run.
- `summary`: total, successful, failed, success rate, and generation time.

`samples.csv`

- `sample_id`
- `fdc_id`
- `food_name`
- `n_ingredients`
- `difficulty`
- `success`

`splits/*.txt`

Each line is a `sample_id`. Splits are grouped by original FDC ID to avoid leakage.

## Sample Files

`canonical_food.json`

The source recipe after FNDDS loading:

- FDC ID, food code, food name, food group.
- Serving information.
- Canonical ingredients with FNDDS ingredient code, description, amount, fraction, and order.
- Nutrients per 100 g.

`ground_truth.json`

Ground truth used for benchmark evaluation:

- Original canonical food.
- Canonical mappings to numeric FNDDS ingredient codes.
- Target mappings from declared label names to canonical FNDDS ingredient descriptions.
- Ingredient amounts and fractions keyed by ingredient code.
- Transformation history.
- Validation report, when validation is enabled.

`structured_label.json`

Structured label data after transformation:

- Product name.
- Declared ingredient list and two-percent-or-less group.
- Nutrition Facts panel.
- Allergen declaration.
- Claims.

`rendered_label.txt`

Final rendered ingredient label text. This is the primary input for parsing systems.

`nutrition_facts.json`

Structured Nutrition Facts panel values used to render the text panel.

`operators.json`

Ordered transformation records, including operator name, version, affected ingredients, and
configuration.

`validation.json`

Validation report with per-rule pass/fail status, repair metadata, and regeneration flag.

`metadata.json`

Sample ID, random seed, software version, generation timestamp, difficulty, and operator
records.

## Difficulty

Difficulty is assigned from operators that actually changed ingredients or produced label
artifacts. A sample with no effective transformations remains `EASY`.

## Evaluation Namespace

Parsing evaluation uses declared ingredient names. Mapping evaluation for built-in baselines
uses canonical FNDDS ingredient descriptions as targets. Numeric ingredient codes remain
available through `ground_truth.canonical_mappings`.
