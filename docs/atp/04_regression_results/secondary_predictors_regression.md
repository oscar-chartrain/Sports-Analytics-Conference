# Secondary Predictors vs. Clutch: Pre-Registration and Results

## Pre-registration

Written before computing a single correlation between these predictors
and clutch score.

### Why this check

`step3_variable_preregistration.md` pre-registered
`net_play_escalation_delta`, `wide_serve_escalation_delta`,
`return_depth_shift_delta`, and `dropshot_rate` as secondary/exploratory
predictors, deliberately deciding their role before seeing whether they
related to clutch performance. They have been computed for the full
qualified pool, on both tours, since Step 2, but never actually
correlated against clutch score. This closes that gap for two reasons:
it is a real, standing question this project pre-registered and then
left untested, and `paper/application_and_impact.md`'s claim that this
project's infrastructure is a "reusable toolkit... for testing any
candidate style predictor against this same rigorously-built clutch
outcome" has so far been a promise, not a demonstration. This is the
first actual test of that claim.

### Predictors and their already-committed roles

From `step3_variable_preregistration.md`, restated here for completeness,
not revised:

- `net_play_escalation_delta`: proposed as a control variable, not a
  second primary predictor.
- `wide_serve_escalation_delta`: proposed as exploratory/robustness only.
- `return_depth_shift_delta`: proposed as exploratory, flagged with a
  known thin-sample caveat at the top of the pressure ladder in the
  original Sinner/Alcaraz sanity-check pair specifically, not the full
  pool, which is fully sufficient (see below).
- `dropshot_rate`: proposed as exploratory/secondary control.

None of these were ever proposed as replacing
`conditional_normalized_entropy` as the primary predictor, and this
check does not revisit that. This is a survey of secondary predictors,
not a new primary hypothesis test.

### Method

For each of the 4 predictors, each of 2 roles (`serve_clutch_p65`,
`return_clutch_p65`), and each of 2 tours (ATP, WTA): Pearson correlation
`r` and its p-value, using the full qualified pool where both the
predictor's own sufficiency flag and the clutch score's sufficiency flag
are `True`. Coverage was checked before writing this document (a data
availability fact, not a hypothesis test) and confirmed at 100% (91/91
ATP, 55/55 WTA) for all four predictors, so no player is dropped for any
of these tests. Predictor and outcome values are taken directly from
each tour's primary feature files
(`step2_full_pool_features.csv`/`wta_full_pool_features.csv` and
`step3_clutch_features.csv`/`wta_clutch_features.csv`), not any
reconstructed file, to avoid the ATP reconstruction-provenance gap
already disclosed in `empirical_p_variant.md`.

This gives 4 predictors x 2 roles x 2 tours = 16 comparisons.

### Commitment (fixed before running)

1. All 16 comparisons will be reported, regardless of outcome, in one
   table.
2. A single Bonferroni correction is applied across all 16 comparisons
   together (alpha = 0.05/16 ≈ 0.003125), not per-predictor or per-tour
   subfamilies, since all 16 are being tested in this same batch from
   this same pre-registration document. This is the more conservative
   choice and avoids any appearance of drawing family boundaries after
   seeing which grouping would look best.
3. None of these predictors will be treated as a replacement for, or a
   second primary test alongside, `conditional_normalized_entropy`,
   regardless of what is found. Their pre-registered role
   (control/exploratory) stands unchanged by this check's results.
4. If any of the 16 comparisons survives correction, that will be
   reported as a real, reportable secondary finding, and as validating
   evidence for the reusable-infrastructure claim in
   `application_and_impact.md`, not folded into or confused with the
   paper's primary null result.
5. If none survive correction, that will also be reported plainly: a
   further null across this project's full set of style-related
   predictors, on top of the primary entropy result, using
   infrastructure that clearly works end to end (100% sufficiency, zero
   new data extraction needed) rather than failing for a data-coverage
   reason.
6. This document will not be edited after seeing the computed
   correlations.

## Results

Written after running `src/robustness/secondary_predictors_regression.py` exactly
as specified above.

| Tour | Predictor | Role | n | r | p |
|---|---|---|---|---|---|
| ATP | net_play_escalation_delta | serve | 91 | +0.160 | 0.129 |
| ATP | net_play_escalation_delta | return | 91 | +0.165 | 0.118 |
| ATP | wide_serve_escalation_delta | serve | 91 | +0.018 | 0.867 |
| ATP | wide_serve_escalation_delta | return | 91 | +0.002 | 0.988 |
| ATP | return_depth_shift_delta | serve | 91 | +0.121 | 0.254 |
| ATP | return_depth_shift_delta | return | 91 | +0.095 | 0.371 |
| ATP | dropshot_rate | serve | 91 | +0.261 | 0.013 |
| ATP | dropshot_rate | return | 91 | +0.205 | 0.052 |
| WTA | net_play_escalation_delta | serve | 55 | +0.047 | 0.735 |
| WTA | net_play_escalation_delta | return | 55 | -0.136 | 0.323 |
| WTA | wide_serve_escalation_delta | serve | 55 | -0.103 | 0.455 |
| WTA | wide_serve_escalation_delta | return | 55 | -0.000 | 0.998 |
| WTA | return_depth_shift_delta | serve | 55 | +0.312 | 0.020 |
| WTA | return_depth_shift_delta | return | 55 | -0.027 | 0.844 |
| WTA | dropshot_rate | serve | 55 | -0.072 | 0.603 |
| WTA | dropshot_rate | return | 55 | +0.140 | 0.307 |

Bonferroni-corrected alpha across the pre-registered 16-comparison
family: 0.003125. **0 of 16 comparisons survive correction.**

Two are nominally close at the uncorrected p < 0.05 level: ATP dropshot
rate vs. serve clutch (r = +0.261, p = 0.013) and WTA return-depth shift
vs. serve clutch (r = +0.312, p = 0.020). Neither clears the
pre-registered corrected threshold by a wide margin, and per commitment
#3, neither is being elevated to a primary or second-primary predictor
regardless. Reported here because the pre-registration committed to
reporting the full table plainly, not just the comparisons that turned
out uninteresting.

### Honest verdict

A further null, on top of the primary entropy result: none of this
project's four secondary style predictors, tested for the first time
here against clutch performance, survive correction on either tour or
role. This is not a data-coverage failure, every one of the 16
comparisons used the full qualified pool (100% sufficiency, both tours),
so the null cannot be attributed to thin data the way an earlier finding
might invite. It is also the first real demonstration, not just an
assertion, that the reusable-infrastructure claim in
`paper/application_and_impact.md` is genuine: these four predictors were
computed once, in Step 2, using shared parsing and pressure-classification
logic, and testing them against the clutch outcome here required zero new
data extraction, only a merge and a correlation. The toolkit works
end to end; it simply did not surface a second relationship this time.

### How to reproduce
```
python3 src/robustness/secondary_predictors_regression.py
```
Needs only the already-committed primary feature and clutch files for
both tours (`results/{atp,wta}/step2_full_pool_features.csv` or
`wta_full_pool_features.csv`, and `step3_clutch_features.csv` or
`wta_clutch_features.csv`); no raw MCP data or re-extraction required.
