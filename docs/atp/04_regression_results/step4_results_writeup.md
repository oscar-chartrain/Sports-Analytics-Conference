# Step 4: ATP Primary Regression — Results

Written to close a documentation gap: the ATP result existed only as
`run_pipeline.py` console output, with no write-up parallel to
`docs/wta/wta_README.md`. Rerun fresh, not copied from an earlier run,
before writing anything below; see "How to reproduce" for the exact
command.

## Primary result

| Role | Pearson r | p | β (OLS) | 95% CI (β) | R² |
|---|---|---|---|---|---|
| Serve | -0.0413 | 0.6972 | -0.0447 | [-0.272, 0.183] | 0.0017 |
| Return | +0.0164 | 0.8774 | +0.0138 | [-0.163, 0.191] | 0.0003 |

n = 91 (100% of the qualified ATP pool, no players dropped for
insufficiency).

Conditional shot-selection entropy does not predict clutch performance on
either serve or return. Both effect sizes are close to zero and nowhere
near conventional significance.

## Equivalence bounds (TOST)
Rather than only reporting "failed to reject the null," a two-one-sided
equivalence test gives a precise, positive claim about how small the true
effect must be:

- Serve: rules out |r| > 0.213 at 95% confidence
- Return: rules out |r| > 0.189 at 95% confidence

This is a materially stronger statement than the p-value alone: it bounds
the true effect rather than merely failing to detect one.

## Robustness across leverage-weighting variants

| Variant | Serve r (p) | Return r (p) |
|---|---|---|
| p60 | -0.0502 (0.6363) | -0.0314 (0.7677) |
| p65 (primary) | -0.0413 (0.6972) | +0.0164 (0.8774) |
| p70 | -0.0471 (0.6577) | -0.0449 (0.6727) |
| tiered | -0.0378 (0.7221) | +0.0126 (0.9060) |

The null is stable across every leverage-weighting specification, not just
the primary p=0.65 choice.

## A caveat that applies unevenly to serve vs. return

Split-half reliability testing (`docs/atp/04_regression_results/split_half_reliability.md`)
found `conditional_normalized_entropy` highly reliable (0.925,
Spearman-Brown corrected) but the clutch score much less so: serve clutch
reliability is 0.572 (below the conventional 0.70 "acceptable"
threshold), and return clutch is 0.231 (poor). The serve-side null above
involves two moderately-measured quantities; the return-side null
involves a reliable predictor paired with a poorly-measured outcome, so it
carries less evidentiary weight and should be described as more
inconclusive than confirmatory in the paper.

## Fifth variant: tour-specific empirical p (added later, different provenance)

A fifth leverage variant, p set to ATP's own observed server point-win
rate (0.6440) rather than a hand-picked constant, was added later; see
`docs/atp/03_leverage_clutch/empirical_p_variant.md` for the full
pre-registration and write-up. It isn't included in the table above
because it can't be: computing it required rebuilding ATP's clutch
features from scratch, and that rebuild doesn't exactly reproduce this
table's frozen source file (`step3_clutch_features.csv`), a real,
previously-unquantified provenance gap the empirical-p work surfaced (see
that doc for the full diff). The empirical-p result itself (serve
r=-0.041, p=0.697; return r=+0.023, p=0.828) is materially identical to
the p65 row above, since ATP's empirical p (0.6440) landed almost exactly
on 0.65, but it should be cited with the reconstruction caveat the
empirical-p doc describes, not with this table's confidence.

## Additional robustness (from the original methodology audit)
- Spearman rank correlation confirms the null under a nonparametric test
  (no non-linear/monotonic relationship missed by OLS)
- Cook's-distance outlier check: null survives removal of the most
  influential players on each side
- Quadratic term: no non-linear (U-shaped) relationship detected
- Heteroskedasticity (Breusch-Pagan): none detected
- BLR convergent-validity check: entropy also shows no relationship with
  the independent, field-standard Balanced Leverage Ratio (r=-0.101,
  p=0.340), corroborating that the null isn't an artifact of this
  project's specific clutch-score construction

## How to reproduce
```
python3 src/pipeline/run_pipeline.py --tour atp
```
Or, to reproduce just the numbers above from an existing `atp_merged.csv`
(no data fetch): see `src/pipeline/rerun_primary_regression.py` (a minimal
script containing exactly the computation above, no orchestration). Note:
this write-up was originally drafted expecting that script to live under
`docs/step4/`; it was relocated to `src/` instead so executable code stays
alongside the other pipeline modules it imports (`src/core/formulas.py`)
rather than inside `docs/`.

## Reference
See `docs/atp/02_entropy_pipeline/step2_calculation_derivations.md` for the
entropy formula derivation and `docs/atp/03_leverage_clutch/step3_README.md`
for the leverage/clutch construction. This document covers only the
regression itself.
