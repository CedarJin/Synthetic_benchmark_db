# Dataset Schema

Generated datasets are directory based. A dataset root contains one directory per sample
plus index and manifest files.

```text
dataset_root/
  manifest.json
  samples.csv
  generation_summary.json        # only when produced by the example script
  generation_config.json         # only when produced by the example script
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

`generation_summary.json`

Generation and validation summary produced by `scripts/generate_benchmark.py`:

- Generation total, successful, failed, and success rate.
- Validation reports, all-passed count, and failed count.
- Per-sample generation failures, if any.
- Dataset version and config path, when generated from a versioned config.

`generation_config.json`

Config snapshot produced by `scripts/generate_benchmark.py`:

- `config_path`: source config path, when provided.
- `source_config`: checked-in config values loaded from YAML.
- `effective_config`: final values after command-line overrides.

`source_config` records `ingredient_name_lexicon_version` when a dataset is generated with a
versioned ingredient-name lexicon.

## Sample Files

`canonical_food.json`

The source recipe after FNDDS loading:

- FDC ID, food code, food name, food group.
- Serving information.
- Canonical ingredients with FNDDS ingredient code, description, amount, fraction, and order.
- Nutrients per 100 g.

`ground_truth.json`

Ground truth for downstream NIP-M evaluation:

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

Final rendered ingredient label text. This is the primary text artifact handed to downstream
parsing systems.

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

## Handoff Namespace

The dataset keeps both declared label names and canonical FNDDS ingredient identifiers so NIP-M can
evaluate parsing and mapping later. This repository generates and documents those fields, but does
not define the downstream parsing or mapping algorithms.
