# TODO

## Now

- [ ] Add GitHub Actions CI for `ruff`, `mypy`, and `pytest`.
- [ ] Verify CI-compatible dependency layout for sibling `../NuSol-T`.
- [ ] Push CI setup to GitHub.

## Next

- [ ] Expand `README.md` with install, test, generation, and evaluation examples.
- [ ] Add a small end-to-end example script for dataset generation and baseline evaluation.
- [ ] Run a real FNDDS smoke generation with 20-50 samples and inspect outputs.
- [ ] Add a dataset schema reference for generated sample directories.
- [ ] Add known limitations for FDA claim logic, Nutrition Facts rounding, and allergen rules.

## Later

- [ ] Add regression fixtures for generated sample JSON/text outputs.
- [ ] Add benchmark report examples under `docs/`.
- [ ] Decide whether to replace the local path dependency on `../NuSol-T` with a package or Git dependency.
- [ ] Re-review FDA rule coverage against the benchmark publication requirements.
