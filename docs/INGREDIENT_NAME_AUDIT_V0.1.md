# Ingredient Name Audit v0.1

## Purpose

The 200-sample `benchmark_v0.1` pilot showed that comma removal alone is not enough. Many FNDDS
ingredient descriptions are technically precise but too survey-like for a food label ingredient
declaration.

This audit starts the AI-assisted lexicon workflow:

1. Extract awkward FNDDS ingredient descriptions from generated pilot samples.
2. Propose concise label ingredient names.
3. Review and commit accepted mappings into a fixed versioned lexicon.
4. Keep generation deterministic by loading the reviewed lexicon, not by calling AI at generation
   time.

## Versioned Lexicon

Current reviewed lexicon:

```text
src/synth_bench/knowledge/lexicons/ingredient_names_v0.1.yaml
```

The generator loads this lexicon through `lookup_commercial_name()`. Exact lexicon mappings take
priority over the older built-in commercial-name dictionary. If no exact mapping exists, the
fallback normalizer still removes FNDDS internal commas.

## Examples Added

Representative mappings added in v0.1:

| FNDDS ingredient description | Label ingredient name |
| --- | --- |
| `Flour, wheat, all-purpose, enriched, bleached` | `ENRICHED WHEAT FLOUR` |
| `Chicken, NS as to part, rotisserie, skin not eaten` | `ROTISSERIE CHICKEN` |
| `Eggs, Grade A, Large, egg whole` | `EGGS` |
| `Eggs, Grade A, Large, egg yolk` | `EGG YOLK` |
| `Milk, nonfat, fluid, without added vitamin A and vitamin D (fat free or skim)` | `NONFAT MILK` |
| `Cream, fluid, light (coffee cream or table cream)` | `LIGHT CREAM` |
| `Beans, kidney, red, mature seeds, cooked, boiled, without salt` | `KIDNEY BEANS` |
| `Corn, sweet, yellow, frozen, kernels cut off cob, boiled, drained, without salt` | `CORN` |
| `Spices, basil, dried` | `DRIED BASIL` |
| `Soup, chicken broth, ready-to-serve` | `CHICKEN BROTH` |

## Remaining Work

The v0.1 lexicon is intentionally a reviewed starter set, not a complete FNDDS-to-label dictionary.
Next expansion should focus on:

- Meat cut descriptions with `separable lean`, `trimmed`, `all grades`, and cooking-method phrases.
- Canned/frozen vegetable descriptions with `drained`, `without salt`, and `regular pack`.
- Prepared foods such as pizza, pie crust, hash browns, and formula ingredients.
- Fruit descriptions with `canned`, `water pack`, `solids and liquids`, or ascorbic-acid clauses.
- Nuts and peanut butter descriptions with USDA distribution-program parentheticals.

## Review Criteria

Accepted lexicon entries should:

- Remove survey-only qualifiers that do not normally appear in an ingredient declaration.
- Preserve the ingredient identity needed for downstream ground truth alignment.
- Avoid inventing brand names.
- Avoid changing broad food category, allergen implications, or ingredient identity.
- Prefer concise label forms such as `ENRICHED WHEAT FLOUR`, `ROTISSERIE CHICKEN`, `GREEN BEANS`,
  and `DRIED BASIL`.
