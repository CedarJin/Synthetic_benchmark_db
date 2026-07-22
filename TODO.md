# TODO

## Now

- [x] Add GitHub Actions CI for `ruff`, `mypy`, and `pytest`.
- [x] Verify CI-compatible dependency layout for sibling `../NuSol-T`.
- [x] Push CI setup to GitHub.
- [x] Re-scope this repository as benchmark dataset generation only.
- [x] Replace the default example workflow with generation and validation summary output.
- [x] Add a versioned generation config under `configs/`.

## Next

- [x] Expand `README.md` with install, test, generation, output, and limitation examples.
- [x] Add a small end-to-end example script for dataset generation.
- [x] Run a real FNDDS smoke generation with 20-50 samples and inspect outputs.
- [x] Add a dataset schema reference for generated sample directories.
- [x] Add known limitations for FDA claim logic, Nutrition Facts rounding, and allergen rules.
- [x] Generate a larger real-FNDDS pilot dataset and inspect artifact quality.
- [ ] Add a dataset card with source, generation settings, validation coverage, and limitations.
- [ ] Add regression fixtures for representative generated JSON/text outputs.

## Later

- [x] Add benchmark report examples under `docs/`.
- [ ] Decide whether to replace the local path dependency on `../NuSol-T` with a package or Git dependency.
- [ ] Re-review FDA rule coverage against the benchmark publication requirements.
- [ ] Stabilize the `ground_truth.json` contract for NIP-M handoff.
- [ ] Package a release dataset artifact with manifest, schema version, and checksums.
- [ ] Hand off parsing, mapping, and downstream evaluation work to NIP-M.
