# Tour-Specific Empirical p: Pre-Registration and Results

## Pre-registration

Written before computing either tour's empirical point-win probability or
looking at the resulting clutch scores/correlations, following the same
discipline as `step3_variable_preregistration.md` and
`wta_replication_preregistration.md`.

### The gap this closes

The leverage engine's `p` (in `src/core/formulas.py`) is deliberately a
single fixed constant, uniform across every point, to avoid the
circularity of a player- or match-specific p (see that module's docstring, and
`step3_README.md`'s "Related work" section). The existing
p60/p65/p70/tiered variants are all ATP-calibrated constants, and the WTA
replication reused them unchanged ("identical pipeline, only the
population changed," see `wta_README.md`). That's methodologically fine
for testing whether the *relationship* replicates, but it leaves one
thing unchecked: women's professional tennis has a genuinely different
average service-hold rate than men's, so applying ATP-shaped constants to
WTA data is an untested assumption, not a verified one.

### What "empirical p" means here, precisely

For a given tour, `p_empirical` = the observed fraction of points won by
the server, computed once across every point in that tour's
qualified-pool match set (the same point set `build_clutch_features`
already receives, not the full unfiltered MCP dataset, and not filtered
further). This is:

- Still a single, tour-wide scalar, not player- or match-specific, so it
  doesn't reintroduce the circularity the fixed-p design was built to
  avoid. It only replaces "a constant someone picked" with "a constant
  this tour's own data implies," while keeping the same "leverage is a
  pure function of score state" property for every player within that tour.
- Computed once per tour, passed through the same unmodified leverage
  engine as a fifth scalar input, exactly parallel to how p60/p65/p70/
  tiered are each "just a different scalar input" per `build_clutch_features()`'s
  existing docstring (in `src/core/features.py`).
- Implemented as `data_io.compute_empirical_p()` (in `src/core/data_io.py`).

### Commitment (fixed before running)

1. The actual empirical p value found for each tour will be reported as a
   standalone fact (interesting on its own, a direct, checkable read of
   real service dominance by tour) regardless of what the correlation
   analysis shows.
2. The resulting `serve_clutch_empirical` / `return_clutch_empirical`
   columns and their correlation with `conditional_normalized_entropy`
   will be added as a fifth row to each tour's existing
   p60/p65/p70/tiered robustness table (`step4_results_writeup.md` for
   ATP, `wta_README.md` for WTA), not presented as a replacement for the
   primary p65 result.
3. Any Bonferroni correction covering the robustness family will be
   recomputed to include this fifth variant (10 comparisons instead of 8),
   not reported alongside the old 8-comparison threshold as if nothing
   changed.
4. If `p_empirical` happens to land very close to one of the existing
   fixed constants (a real possibility, the constants were chosen to
   bracket a plausible range), that will be reported plainly as a sanity
   check that the fixed constants were well-chosen, not treated as making
   this variant redundant after the fact.
5. This section will not be edited after seeing the computed p values or
   the correlation results.

## Results

Written after running the analysis pre-registered above. Reported in
full, including a real provenance finding this analysis surfaced that
wasn't previously known.

### The empirical p values themselves (a standalone fact, per commitment #1)

| Tour | Empirical p (observed server point-win rate) | Nearest existing fixed constant |
|---|---|---|
| ATP | 0.6440 | 0.65 (off by 0.006) |
| WTA | 0.5725 | 0.60 (off by 0.028) |

ATP's empirically-observed service dominance lands almost exactly on the
primary p=0.65 constant already in use: direct, data-driven confirmation
that the original constant was well-calibrated, not an arbitrary round
number (per commitment #4). WTA's is meaningfully lower than any of the
existing fixed constants (0.60/0.65/0.70), consistent with the real,
well-documented difference in service dominance between the tours. This is
exactly the untested assumption this analysis set out to check, and it
turns out to matter more for WTA than for ATP.

### Correlation results, added as a fifth row to each tour's existing table

| Tour | Role | r (empirical p) | p |
|---|---|---|---|
| ATP | Serve | -0.041 | 0.697 |
| ATP | Return | +0.023 | 0.828 |
| WTA | Serve | -0.266 | 0.050 |
| WTA | Return | +0.260 | 0.055 |

ATP's empirical-p result is essentially identical to its p65 result
(r=-0.041/+0.023 vs -0.041/+0.016), unsurprising given how close the two p
values are. WTA's empirical-p serve result (p=0.050) is the smallest
nominal p-value in WTA's now-10-comparison family, but it isn't an outlier
or a new departure from the existing pattern: it sits alongside WTA's p70
serve result (p=0.017, already the most extreme existing variant) and the
already-reported tiered/p65/p60 borderline values. Recomputing the
family-wise Bonferroni correction across all 5 variants x 2 roles = 10
comparisons (per commitment #3) gives a corrected alpha of 0.0050 for both
tours, and nothing survives correction for either tour. Same conclusion as
before this variant was added, now on a properly-expanded comparison
family.

### A provenance finding this analysis surfaced

Computing the empirical p required rebuilding each tour's clutch features
from scratch via `src/pipeline/rebuild_clutch_features.py` (re-fetching matches and
points and calling `build_clutch_features()` directly, without re-running
entropy extraction). Doing this for both tours turned up something not
previously checked:

- WTA: the rebuild reproduces the committed `wta_clutch_features.csv`
  exactly, max diff = 0 across all 13 shared numeric columns. Expected and
  reassuring, since that file has always been this script's own output.
- ATP: the rebuild does not exactly reproduce the committed
  `step3_clutch_features.csv`. Clutch scores differ by up to ~0.005 and
  per-player quartile-bucket point counts differ by up to 136 (concentrated
  in high-volume players like Federer), even though the aggregate
  relevant-match/relevant-point counts match exactly (6,652 matches,
  1,132,053 points, both matching `step3_README.md`'s documented figures,
  which rules out upstream MCP data drift as the explanation).

This is a newly-quantified instance of an already-disclosed gap, not a new
bug: `build_clutch_features()`'s own module docstring has always stated
the original ATP script that produced `step3_clutch_features.csv` is "not
recoverable," and that this file is a reconstruction, previously checked
only against a handful of spot-check numbers (Sinner/Alcaraz clutch
values, the BLR convergent-validity correlation), never a full-table diff.
This is the first time a full-table diff has actually been run, and it
shows the reconstruction, while methodologically faithful (same leverage
engine, same MIN_OBS gating, same quartile-split logic), doesn't reproduce
the lost original byte-for-byte.

In practice, `results/atp/step3_clutch_features.csv` (the primary,
historical ATP file) is left completely untouched by this work; none of
the numbers quoted in `step4_results_writeup.md` or elsewhere change. The
empirical-p analysis above, and any other new leverage variant added going
forward, is necessarily computed on the reconstructed engine's fresh
output (`step3_clutch_features_reconstructed.csv`,
`atp_merged_reconstructed.csv`), since new variants can't be retroactively
added to a frozen historical CSV. That means ATP's empirical-p numbers now
carry the same "reconstruction, not verified-identical to the lost
original" caveat that previously only applied to WTA's tiered variant, and
that caveat should be stated explicitly wherever the ATP empirical-p
result is cited in the paper.

### How to reproduce
```
python3 src/pipeline/rebuild_clutch_features.py --tour atp
python3 src/pipeline/rebuild_clutch_features.py --tour wta
```
Both print a diff summary against the tour's existing primary file, so the
finding above (identical for WTA, not for ATP) is visible on every rerun,
not just this one.
