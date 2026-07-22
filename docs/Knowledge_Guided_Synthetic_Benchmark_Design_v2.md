
# Knowledge-guided Synthetic Benchmark for Ingredient Parsing and Mapping
## Unified Project & Technical Design Document (v2)

> Scope: This document focuses on Modules 1–5 (benchmark generation, parsing and mapping). Downstream optimization and nutrient reconstruction are summarized only briefly.

---

# 1. Motivation

Current ingredient parsing and mapping methods lack objective evaluation because no existing dataset simultaneously provides realistic food labels and formulation ground truth.

| Dataset | Strengths | Limitations |
|---|---|---|
| USDA FNDDS | Complete recipe ground truth | Mainly dietary survey foods |
| USDA Branded Food Products Database | Real commercial labels | No formulation ground truth |
| Open Food Facts | Large-scale labels | Community curated, incomplete |

Our objective is not to perfectly mimic every commercial product, but to build a controlled, reproducible benchmark with known ground truth while remaining close to FDA-compliant branded labels.

---

# 2. Design Principles

1. Ground truth first.
2. Knowledge-guided generation instead of free-form generation.
3. LLMs perform only language realization.
4. Every transformation is traceable.
5. Every generated sample is automatically validated.
6. Every benchmark sample is reproducible.

---

# 3. Framework Architecture

```text
FNDDS
  │
  ▼
Module 1 Canonical Food Representation
  │
  ▼
Knowledge Base
(FDA, RACC, FoodOn, Taxonomy, Rules)
  │
  ▼
Module 2 Transformation Engine
  │
  ▼
Structured Label Representation
  │
  ▼
Module 3 LLM Surface Realization
  │
  ▼
Module 4 Validation & Repair
  │
  ▼
Synthetic Benchmark Dataset
  │
  ▼
Module 5 Parsing & Mapping Evaluation
```

LLMs are intentionally limited to natural language rendering. Knowledge and regulatory decisions originate from the rule engine.

---

# 4. Domain Gap

FNDDS is not a branded food database. Therefore the benchmark explicitly includes:

- packaged-food category filtering;
- distribution calibration using USDA Branded Foods and Open Food Facts;
- optional enrichment of commercially common additives;
- documentation of remaining representativeness limitations.

---

# Module 1. Canonical Food Representation

Every FNDDS food is converted into a Canonical Food Object.

```yaml
food_id:
food_name:
food_group:
canonical_serving:
ingredients:
nutrients:
metadata:
```

Ground truth is stored separately.

```yaml
ground_truth:
  canonical_mapping:
  target_mapping:
  ingredient_amount:
  transformation_history:
  validation_report:
```

A dedicated RACC mapper converts food categories into FDA serving-size categories before Nutrition Facts generation.

---

# Knowledge Base

Contains:

- FDA labeling regulations
- RACC table
- allergen rules
- FoodOn
- ingredient taxonomy
- synonym dictionary
- claim rules
- nutrition label templates

---

# Module 2. Knowledge-guided Transformation Engine

Generation is performed through configurable operators.

Core operators:

- RenameOperator
- GenericNameOperator
- CompoundIngredientOperator
- LessThan2PercentOperator
- AllergenOperator
- ClaimEligibilityOperator
- NutritionFactsOperator

Compound ingredient expansion is allowed only when supported by curated knowledge. Otherwise, the compound ingredient itself remains the benchmark ground truth.

---

# Module 3. LLM Surface Realization

The LLM rewrites structured labels into natural commercial language.

The LLM cannot:

- invent ingredients;
- change ingredient order;
- modify percentages;
- alter regulatory statements.

---

# Module 4. Validation & Repair

Automatic validation includes:

- ingredient preservation;
- ingredient order;
- FDA syntax;
- allergen declarations;
- Nutrition Facts consistency;
- claim eligibility;
- prohibited terminology.

Failed samples are repaired or regenerated automatically.

Difficulty is determined by applied operators rather than random probabilities.

---

# Module 5. Parsing & Mapping Benchmark

Two tasks are evaluated independently.

## Ingredient Parsing

Metrics:

- Precision
- Recall
- F1
- Exact Match

## Ingredient Mapping

Recommended target spaces:

- FoodOn
- USDA Foundation Foods / SR-compatible foods
- Project-specific canonical identifiers

Recommended baselines:

- dictionary matching;
- BM25 retrieval;
- embedding retrieval;
- LLM-based mapping.

Evaluation should cluster confidence intervals by original recipe rather than generated variants.

---

# Dataset Organization

```text
sample_x/
    canonical_food.json
    ground_truth.json
    structured_label.json
    rendered_label.txt
    nutrition_facts.json
    operators.json
    validation.json
    metadata.json
```

---

# Reproducibility

Each sample records:

- FNDDS version
- prompt version
- model snapshot
- software version
- operator versions
- random seed
- validation report

Generated artifacts are versioned directly.

---

# Future Integration

This benchmark is designed to become the standardized upstream infrastructure for downstream ingredient amount estimation, NuSol-T optimization, comprehensive nutrient reconstruction, and AI-agent workflows.
