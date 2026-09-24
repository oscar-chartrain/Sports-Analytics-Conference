# Pooled ATP+WTA Regression: Pre-Registration and Results

## Pre-registration

Written before running the pooled model or looking at its output, following
the same discipline as `step3_variable_preregistration.md` and
`wta_replication_preregistration.md`. This section commits to the model
spec and the reporting rule before seeing a single coefficient.

### Why this analysis

The ATP (n=91) and WTA (n=55) tests were each run and reported
independently and are each individually underpowered to detect a small
effect. Comparing the two point estimates by eye (ATP serve r=-0.041, WTA
serve r=-0.259) isn't a real statistical test of whether the tours differ,
it's an impression. This analysis adds two things the separate per-tour
write-ups don't provide:

1. A single, properly-powered combined test (n=146) of the primary
   hypothesis, rather than two separate, individually weaker ones.
2. A formal test of whether the entropy-clutch relationship genuinely
   differs by tour (an entropy × tour interaction term), replacing
   eyeballing two point estimates with an actual p-value on the difference.

This is an additive analysis. It does not replace, override, or
retroactively edit either the ATP write-up
(`docs/atp/04_regression_results/step4_results_writeup.md`) or the WTA
write-up (`docs/wta/wta_README.md`), both of which remain the primary,
pre-registered per-tour results.

### Model specification (fixed before running)

For each role (serve, return) independently, using each player's `{role}_clutch_p65`
as the outcome and `conditional_normalized_entropy` as the predictor:

- **Pool eligibility**: identical sufficiency gating to the existing
  per-tour regressions; a player is included only if
  `transition_entropy_sufficient` and `{role}_clutch_p65_sufficient` are
  both True. No new inclusion rule.
- **Model A (interaction test)**: `{role}_clutch_p65 ~ conditional_normalized_entropy * tour`
  (OLS, `tour` as a categorical indicator, ATP as reference level). The
  `conditional_normalized_entropy:tour[T.wta]` coefficient's p-value is
  the test of whether the slope differs by tour.
- **Model B (pooled main effect)**: `{role}_clutch_p65 ~ conditional_normalized_entropy + tour`
  (no interaction), which gives one combined slope estimate and 95% CI
  across both tours, under the assumption of a common effect (only
  interpretable if Model A's interaction is not significant).
- **Meta-analytic cross-check**: Fisher z-transform combination of the two
  independent per-tour Pearson r's (already reported) into one pooled r
  and CI, as an assumption-light complement to Model B's regression-based
  pooling. Implemented as `stats_helpers.fisher_z_meta_analysis()`.

### Reporting commitment (fixed before running)

All of the following will be reported, regardless of outcome:
- If the interaction term (Model A) is significant: the tours will be
  reported as genuinely differing, and Model B's pooled estimate will be
  flagged as not meaningfully interpretable (pooling would average over a
  real difference).
- If the interaction term is not significant: Model B's pooled estimate
  and the meta-analytic estimate become the headline combined-tour number,
  reported alongside, not instead of, the two individual per-tour results.
- No leverage variant other than p65 (the primary, pre-registered variant
  for both tours) is used in this pooled test, to avoid multiplying
  comparisons beyond what's already Bonferroni-accounted-for in the
  per-tour robustness tables.
- This section will not be edited after seeing results. Any surprise will
  be discussed in the results section's own text, not resolved by
  changing the model spec above.

## Results

Written after running `src/robustness/pooled_regression.py` exactly as specified
above. Reported in full, including the parts that don't fit a clean
narrative (the two roles behave differently under pooling), per the
reporting commitment above.

### Interaction test: do the tours genuinely differ?

| Role | Interaction β | p |
|---|---|---|
| Serve | -0.328 | 0.146 |
| Return | +0.234 | 0.207 |

Neither interaction term is significant. Despite the ATP and WTA serve
point estimates looking different by eye (-0.041 vs -0.259), there's no
statistical evidence the true entropy-clutch slope actually differs by
tour. Cochran's Q agrees (serve Q=1.64, p=0.20; return Q=1.09, p=0.30,
both homogeneous). Pooling is defensible for both roles, which is itself a
useful, non-obvious finding: it means the two per-tour write-ups'
apparently different point estimates are consistent with sampling noise
around one shared (null) effect, not evidence of two different
populations.

### Pooled main effect (n=146, common slope)

| Role | β (pooled) | p | 95% CI | n (ATP / WTA) |
|---|---|---|---|---|
| Serve | -0.128 | 0.193 | [-0.323, 0.066] | 146 (91/55) |
| Return | +0.074 | 0.364 | [-0.086, 0.233] | 146 (91/55) |

Still null at n=146: combining both tours into one properly-powered test
does not surface a relationship either role's separate test missed.

### Fisher z meta-analytic cross-check

| Role | Pooled r | 95% CI | p |
|---|---|---|---|
| Serve | -0.124 | [-0.282, 0.041] | 0.141 |
| Return | +0.084 | [-0.081, 0.245] | 0.320 |

Agrees with the regression-based pooling (Model B) in direction and
significance for both roles, using a method that doesn't require the two
samples to share a design matrix. Two independent methods reaching the
same conclusion is itself evidence the pooled null isn't an artifact of
one particular way of combining the data.

### Pooled equivalence bounds (TOST)

| Role | ATP-only bound (n=91) | Pooled bound (n=146) |
|---|---|---|
| Serve | \|r\| < 0.213 | **\|r\| < 0.174** |
| Return | \|r\| < 0.189 | \|r\| < 0.241 |

Pooling tightens the serve bound (more data, more precision, as expected)
but loosens the return bound. This isn't an error: WTA's return point
estimate (+0.196) sits further from zero than ATP's (+0.016), so the
pooled return estimate (+0.074) is itself further from zero than the
ATP-only one, and establishing equivalence around a point that isn't as
close to zero requires a wider band. Worth stating plainly rather than
only reporting the serve number: pooling more data doesn't automatically
produce a tighter null on every measure. It depends on whether the
additional data pulls the pooled estimate toward or away from zero, which
is exactly the kind of nuance a single combined analysis can surface that
two separate per-tour write-ups can't.

### Honest verdict

The primary hypothesis test remains null when properly pooled across both
tours (n=146) rather than assessed as two separate, individually
underpowered tests. The interaction test resolves the one loose thread
the per-tour write-ups left open, whether ATP and WTA's differing point
estimates reflected a real population difference, in favor of "no": both
Cochran's Q and the direct interaction term agree the two tours are
statistically indistinguishable on this relationship. This strengthens,
rather than changes, the paper's central claim: a single combined test,
not just two separate ones eyeballed side by side, still finds nothing.

### How to reproduce
```
python3 src/robustness/pooled_regression.py
```
Requires `results/atp/step2_full_pool_features.csv` + `results/atp/step3_clutch_features.csv`
(merged internally, since no `atp_merged.csv` exists) and `results/wta/wta_merged.csv`
to already be present, i.e. run this after `run_pipeline.py --tour atp` and
`--tour wta` have both been run at least once.
