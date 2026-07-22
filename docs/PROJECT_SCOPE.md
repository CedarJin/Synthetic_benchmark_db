# Project Scope Review

## Current Boundary

This repository should be treated as a benchmark dataset generator.

Its responsibility is to produce validated dataset artifacts from FNDDS survey records:

- Load FNDDS survey foods into canonical recipe objects.
- Apply knowledge-guided label transformations.
- Render ingredient declarations, allergen declarations, claims, and Nutrition Facts text.
- Validate rendered samples against the current rule set.
- Write reproducible dataset artifacts, splits, manifests, summaries, and ground truth files.

Parser development, ingredient mapping systems, model comparison, and downstream benchmark
evaluation are NIP-M responsibilities. This repository should only prepare the data that those
systems consume later.

## In Scope

- Canonical FNDDS loading and canonical food models.
- Knowledge rules needed for synthetic label generation.
- Transformation operators that produce realistic label variants.
- Deterministic label and Nutrition Facts rendering.
- Validation rules that protect dataset quality.
- Dataset writing, splits, manifests, schema documentation, and release packaging.
- Ground truth fields needed for downstream NIP-M evaluation.

## Out of Scope

- Improving parsing algorithms.
- Improving ingredient mapping algorithms.
- Training or evaluating NIP-M models.
- Leaderboards or comparative model reports.
- Treating baseline parser/mapper scores as success criteria for this project.

The existing `src/synth_bench/benchmark/` package can remain as reference-only development tooling,
but it should not drive this repository's roadmap.

## Re-Assessment

The core generation pipeline is in a good state for the current scope:

- Real FNDDS smoke generation works.
- Dataset directories include the expected canonical, rendered, validation, metadata, and ground
  truth files.
- Validation now runs after final rendering.
- The latest 50-sample smoke run passed all current validation rules.
- Local linting, typing, and unit tests pass.

The previous weak baseline parser/mapping metrics are no longer a blocker for this repository.
They only show that the reference baselines are simple. The benchmark dataset can still be useful
for NIP-M as long as the generated artifacts and ground truth are stable and well documented.

## Remaining Risks

- The dataset release process is not yet formalized with versioned configs, checksums, and data
  cards.
- Only small real-FNDDS smoke runs have been inspected so far.
- FDA-style claim, rounding, and allergen rules are simplified and need another publication-readiness
  review.
- The local `../NuSol-T` dependency is still a fragile setup assumption.
- The `ground_truth.json` contract needs to be frozen before NIP-M consumes it.

## Recommended Next Work

1. Generate and inspect a larger real-FNDDS pilot dataset using `configs/benchmark_v0.1.yaml`.
2. Add a dataset card documenting source data, generation settings, validation coverage, and known
   limitations.
3. Add regression fixtures for representative generated samples.
4. Stabilize the ground-truth schema for the NIP-M handoff.
5. Package a release artifact with manifest, schema version, and checksums.
