# Era and Surface Confound Check: Pre-Registration and Results

## Pre-registration

Written before computing a single era or surface value, and before
running a single regression.

### Why this check

A cold-read review of `paper/abstract.md` raised a specific objection
not previously tested in this project: the primary entropy-clutch null
result is reported without controlling for player era or surface mix,
either of which could in principle suppress a real relationship (if,
say, the relationship only holds on one surface, or has shifted across
generations) or bias the reliability estimates. This project's Step 1
"Key decisions" section already names selection bias in the charted-match
sample as a documented limitation; this check asks a narrower, testable
version of that concern directly: does the null result survive adding
era and surface as covariates.

### Scope decision: ranking is excluded, fixed before running

The original idea considered three confounds: era, surface, and player
ranking. Player ranking (or seed) does not appear anywhere in the Match
Charting Project's match metadata (`charting-{m,w}-matches.csv` has no
ranking or seed field). Rather than construct an unvalidated proxy for
it, ranking is out of scope for this check. This mirrors this project's
existing practice of naming a scope limitation plainly (e.g., the
pooled-disattenuation scope decision in
`disattenuated_equivalence_bounds.md`) rather than inventing a shaky
substitute.

### Data quality check performed before design (not a hypothesis test)

`Surface` is Hard/Clay/Grass for 7564/7566 ATP matches and 4071/4080 WTA
matches; the remainder are source-data corruption (e.g., a literal
umpire name, "Eva Asderaki-Moore," appearing in the Surface column, the
same class of column-shift error already documented for the `Best of`
field in `step2_calculation_derivations.md`). `Date` is present for
7566/7566 ATP matches and 4070/4080 WTA matches. Matches with an
unparseable Surface or Date are excluded from the relevant covariate's
computation for that player, not guessed at, the same standard already
used for unparseable `Best of` fields.

### Method

For each tour, using the existing qualified pool and the existing
primary predictor/outcome
(`conditional_normalized_entropy`, `{role}_clutch_p65`):

- **Era proxy**: the median year across a player's charted matches with
  a valid `Date` (parsed from the `YYYYMMDD` field). This is a simple,
  transparent proxy for which generation a player's charted sample
  represents; it is not a debut-year or peak-ranking-year measure, since
  neither is available in this data, and is named here as a
  simplification before seeing whether it matters.
- **Surface mix**: `pct_clay` and `pct_grass`, the fraction of a
  player's charted matches (with a valid Surface) played on each
  surface; Hard is the implied reference category (not included as a
  separate covariate, to avoid the standard dummy-variable trap).
- **Model**: for each tour and role, OLS regression
  `{role}_clutch_p65 ~ conditional_normalized_entropy + era_proxy
  (mean-centered) + pct_clay + pct_grass`, compared directly against the
  already-documented simple bivariate result
  (`step4_results_writeup.md` for ATP, `wta_README.md` for WTA).

This gives 4 regressions (2 tours x 2 roles).

### Commitment (fixed before running)

1. All 4 regressions reported regardless of outcome, with entropy's
   coefficient, standard error, and p-value in the multivariate model
   shown directly alongside the already-documented simple-correlation
   figure for comparison.
2. A Bonferroni correction is applied across the 4 comparisons (alpha =
   0.0125), consistent with how every other robustness-check family in
   this project is corrected.
3. This does not replace or revise the primary, pre-registered simple
   entropy-clutch test. It is an additional robustness check on whether
   that result is confounded, exactly parallel to the already-existing
   quadratic-term and match-count-weighted checks in
   `power_and_robustness.md`.
4. If entropy's coefficient or significance changes materially once era
   and surface are controlled for, that will be reported as a genuine,
   surprising finding warranting real scrutiny, not smoothed over. If it
   does not change materially, that will be reported as evidence the
   null is not an era/surface confound artifact.
5. This document will not be edited after seeing the computed values.

## Results

Written after running `src/robustness/confound_check_era_surface.py` exactly as
specified above.

### Data coverage

Every one of the 91 ATP and 55 WTA qualified players had a computable
era proxy and surface mix; no player was dropped for missing data. The
handful of source-data-corrupted Surface/Date rows identified during
design were excluded at the match level, not the player level, and
never removed a player's only data.

### Multivariate regression, entropy's coefficient before and after

| Tour | Role | n | Simple r (p) | Multivariate entropy coef (se, p) | R² |
|---|---|---|---|---|---|
| ATP | Serve | 91 | -0.041 (0.697) | -0.068 (0.120, p=0.574) | 0.025 |
| ATP | Return | 91 | +0.016 (0.877) | -0.033 (0.091, p=0.715) | 0.070 |
| WTA | Serve | 55 | -0.259 (0.056) | -0.361 (0.203, p=0.082) | 0.089 |
| WTA | Return | 55 | +0.196 (0.151) | +0.191 (0.180, p=0.293) | 0.074 |

Bonferroni-corrected alpha across the pre-registered 4-comparison
family: 0.0125. **0 of 4 survive correction.**

### Honest verdict, per commitment #4

**The null result is not an era or surface confound artifact.**
Controlling for career era and surface mix does not surface a
significant entropy effect on either tour or role; if anything, WTA
serve's p-value moves further from significance (0.056 in the simple
bivariate test to 0.082 once era and surface are included), the
opposite direction a suppressed-confound story would predict. ATP
return's coefficient sign flips (+0.016 simple, -0.033 multivariate),
but both values are trivially close to zero and this is the same kind
of sign instability near a true null already documented in
`power_and_robustness.md`'s match-count-weighted check, not a
meaningful reversal.

This closes out a specific, named objection (a cold-read review's
concern that confounds were never checked) with a real answer rather
than an assertion: era and surface were tested directly, using data
already available without any new source, and the null result holds.

### How to reproduce
```
python3 src/robustness/confound_check_era_surface.py
```
No raw MCP points data needed, only each tour's small match-metadata
file (already local) and the already-committed primary feature/clutch
files. Runs in seconds.
