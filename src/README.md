# src/

Shared modules and pipeline scripts, organized in layers:

```
core/
  parsing.py    -- notation, hitter-attribution, score/pressure parsing
  formulas.py    -- entropy, spearman_brown, leverage engine, stats_helpers functions
  data_io.py      -- data loading
  features.py      -- clutch/dropshot/pressure feature construction
pipeline/        -- step1_validation, step2_entropy_pipeline, run_pipeline,
                    rerun_primary_regression, step3_h2h_check, and the
                    disk-cached full-pool extraction/rebuild scripts
robustness/       -- the 10 pre-registered follow-up checks
figures/           -- the 4 export/plotting scripts
```

This replaced an earlier flat layout (one script per pipeline stage, no
subfolders, five shared modules duplicated pieces of logic across each
other). Every function and script below was checked against that original
flat version before the switch -- see the migration log. The original is
still in git history (`git log --diff-filter=D -- src/mcp_common.py` and
similar finds the commit where each old file was removed) if anything here
ever needs to be cross-checked against it.

## Migration log

| File | Consolidated from | Verified |
|---|---|---|
| `core/parsing.py` | The old `mcp_common.py`'s shot-notation, hitter-parity, category-map, serve/return, and score/pressure sections | Yes -- all constants and functions checked against the original, including `verify_hitter_parity`'s pass and fail paths |
| `core/formulas.py` | The old `mcp_common.py` (entropy math), `leverage.py` (whole engine), `stats_helpers.py` (all 6 functions). `spearman_brown()` consolidated here -- it used to be copy-pasted in `make_reliability_figure.py`, `split_half_reliability.py`, `shrinkage_reliability.py`, and `opponent_adjusted_return_clutch.py`. | Yes -- entropy, all 6 stats_helpers functions, and the full leverage engine (game/tiebreak/set/match probability + compute_leverage) checked against the originals across thousands of score-state combinations |
| `core/data_io.py` | The old `mcp_common.py` (data-loading section), `data_snapshot.py`. `entropy_extraction_stage1.py` and `stage2_assemble_features.py` were originally slated for here too, but turned out to be driver scripts depending on `step2_entropy_pipeline.py`, not reusable utilities -- they moved to `pipeline/` instead. | Yes -- all loaders and `snapshot_data_sources` checked against the originals using synthetic CSVs |
| `core/features.py` | The old `build_clutch_features.py`, plus `mcp_common.py`'s dropshot/pressure feature reduction. `rebuild_clutch_features.py` was also originally slated for here, but it's a standalone CLI tool (argparse/main()), not library code anything else imports -- moved to `pipeline/`. | Yes -- `quartile_clutch`, `compute_all_leverages`, full `build_clutch_features` (both return modes, on synthetic point data), `compute_dropshot_features`, `reduce_pressure_features` all checked against the originals |
| `pipeline/step1_validation.py` | The old `step1_validation.py`. Cleanup along the way: replaced `mcp.pd.X` (reaching pandas through the mcp_common module) with a direct `import pandas as pd`. | Yes -- ran both old and new as subprocesses against identical synthetic match/point data (hitter-parity-consistent notation strings, 3000 points); exit codes, full stdout, and the output CSV all match, except two comment lines updated to name the new module |
| `pipeline/step2_entropy_pipeline.py` | The old `step2_entropy_pipeline.py`. Also imported by `entropy_extraction_stage1.py` and `stage2_assemble_features.py` -- function names/signatures preserved exactly. | Yes -- every function checked against the original on synthetic data (6,000 points, 4 players); the `__main__` sanity-check block also run end-to-end, matching the original exactly. Re-verified again after promoting this layout to canonical, against real 2020s ATP data (Sinner/Alcaraz), reproducing the exact numbers documented in `docs/atp/02_entropy_pipeline/step2_README.md`. |
| `pipeline/run_pipeline.py` | The old `run_pipeline.py`. Orchestration only -- now calls `data_io`/`features`/`formulas` from `core/` plus the sibling `step2_entropy_pipeline.py`. | Yes -- ran both as subprocesses against identical 60,000-point synthetic data across 10 players; the qualified-pool CSV output is byte-identical, and both crash identically on a pre-existing edge case in `reduce_pressure_features` (an empty per-player pressure table has no columns) -- confirmed latent in the *original* code, not introduced by this reorganization |
| `pipeline/rerun_primary_regression.py` | The old `rerun_primary_regression.py` | Yes -- ran both as subprocesses against an identical synthetic `atp_merged.csv` (80 players); stdout byte-identical, including the TOST equivalence binary-search output |
| `pipeline/step3_h2h_check.py` | The old `step3_h2h_check.py`. A third copy of `quartile_clutch()` was found here and removed -- this file turned out to be its original source (per `build_clutch_features.py`'s own docstring), so it now imports the canonical copy from `core/features.py` instead of keeping a third copy. | Yes -- ran both as subprocesses against identical synthetic matches/leverage data (2,000 points, includes real Djokovic-Federer matchups); stdout and output CSV both byte-identical |
| `pipeline/entropy_extraction_stage1.py` | The old `entropy_extraction_stage1.py` | Yes -- ran both as subprocesses against identical synthetic 3-decade data; stdout matches modulo timing noise, and all four cached pickle outputs are exactly equal |
| `pipeline/stage2_assemble_features.py` | The old `stage2_assemble_features.py` | Yes -- ran both against identical cached pickles; everything up through per-player entropy/dropshot feature computation matches, then both crash identically on the same pre-existing `reduce_pressure_features` edge case above |
| `pipeline/rebuild_clutch_features.py` | The old `rebuild_clutch_features.py`. **A real fix, not just a rename**: this script computes `REPO_ROOT` relative to its own file location. The nesting depth changed when it moved into `pipeline/`, so the relative path had to change with it -- verified to still resolve correctly, both when the layout lived at `restructuration/pipeline/` and again after promoting it to `src/pipeline/`. | Yes -- built a full fake nested repo for both the old flat layout and the new one, ran both with `--tour atp`, and confirmed both write output to the correct `results/atp/` path with byte-identical CSV contents. Then re-verified against the **full real ATP pool** (91 players, 6,652 matches, 1,132,053 points): byte-identical to the old code's output, and reproduces the exact same already-documented ATP reconstruction gap (not a new discrepancy). Same real-data check on WTA (55 players, 3,042 matches) matched the committed `wta_clutch_features.csv` exactly (max diff = 0). |
| `robustness/secondary_predictors_regression.py`, `disattenuated_equivalence_bounds.py`, `confound_check_era_surface.py`, `shrinkage_reliability.py`, `pooled_regression.py` | Same-named files in the old flat layout. All five needed the same `REPO_ROOT` path fix as `rebuild_clutch_features.py`. | Yes -- built a shared fake nested repo and ran all five old vs. new as subprocesses; four are byte-identical, the fifth (`shrinkage_reliability.py`) differs only in a warning's file path/line number, not in any computed output |
| `robustness/split_half_reliability.py` | The old `split_half_reliability.py`. A fourth `spearman_brown()` duplicate was consolidated here (of five total found across the repo). | Yes -- ran both as subprocesses against a shared synthetic raw-data repo; stdout byte-identical |
| `robustness/continuous_slope_reliability.py` | The old `continuous_slope_reliability.py`. The fifth `spearman_brown()` instance was found and fixed here -- it wasn't even a named function, just the formula `(2*r)/(1+r)` inlined directly. | Yes -- stdout byte-identical, including the cross-check against `build_clutch_features()`'s own output |
| `robustness/opponent_adjusted_return_clutch.py` | The old `opponent_adjusted_return_clutch.py` | Yes -- stdout byte-identical against synthetic raw-data |
| `robustness/entropy_pressure_escalation.py` | The old `entropy_pressure_escalation.py` | Yes -- both crash identically on the same synthetic-data thinness artifact (confirmed harmless, identical in both versions) |
| `robustness/power_and_robustness.py` | The old `power_and_robustness.py` | Yes -- ran both as subprocesses against a full synthetic repo (all four checks); stdout byte-identical |
| `figures/export_split_half_data.py`, `export_split_half_clutch_counts.py` | Same-named files in the old flat layout | Yes -- stdout and output CSVs byte-identical |
| `figures/make_reliability_figure.py` | The old `make_reliability_figure.py`. The fifth and last `spearman_brown()` duplicate was removed here. | Yes -- stdout byte-identical and the output PNG is **MD5-identical**, not just visually similar |
| `figures/make_null_forest_figure.py` | The old `make_null_forest_figure.py` | Yes -- stdout byte-identical (including the script's own internal assertion that its recomputed pooled r/CI matches the documented values) and the output PNG is MD5-identical |
