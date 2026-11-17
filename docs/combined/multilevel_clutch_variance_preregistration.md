# Pre-registration: a direct estimate of true clutch variance

Written 2026-11-16, before `src/robustness/multilevel_clutch_variance.py` was
run on the full data. Self-registered, and written after all earlier results
were known (see `preregistration_timeline.md`). Before writing it, one model
fit on ATP serve points (a feasibility test of the software, not an analysis)
showed the model runs in seconds; its output was seen (true SD about 2.0
points) and is the reason the decision rule below is written around the
earlier estimates.

## Why

The paper's reliability results come from split-half correlations, and its
"true spread of clutch" comes from a variance decomposition that assumes
binomial sampling noise. A reviewer can fairly say that this shows the paper's
tools cannot see clutch, not that clutch cannot be seen, and that clustering of
points within matches could make the noise larger than the binomial assumes.
This analysis estimates the between-player variance of clutch directly.

## Outcome and sample

Per tour and role (serve, return): every point the player played in that role
whose p = 0.65 leverage is in the player's own top or bottom quartile
(career-level quartiles, ties included), with `high` = 1 for top, 0 for bottom,
and `won` = the player's point result. The target quantity is tau, the standard
deviation across players of the top-minus-bottom win-rate difference, in
percentage points.

## Estimators

- **M1, multilevel linear model.** `won ~ high` with a random intercept and a
  random slope on `high` for each player (REML, statsmodels MixedLM). tau is the
  square root of the random-slope variance. 95% interval from 200 player
  bootstrap refits (seed 20261116).
- **M2, cluster-robust two-stage estimator.** Each player's top-minus-bottom
  difference with a standard error that clusters points within matches (the
  sandwich estimator over matches, with the M/(M-1) correction). tau-squared =
  variance of the differences minus the mean squared standard error, floored at
  zero. 95% interval from 2,000 player bootstrap resamples (same seed).
- A model adding a random intercept for match within player was tried on ATP
  serve as a feasibility test and ran for more than 10 minutes without
  finishing. It is reported as not feasible in this software and not used.

## Reported quantities and decision rules

1. **True SD (tau) by M1 and M2** per tour and role, beside the paper's earlier
   variance-method and half-split estimates.
2. **Robustness rule.** The earlier estimates are called robust to the
   estimator and to the binomial assumption if, for ATP serve and ATP return,
   both M1 and M2 lie within 25% of the earlier variance-method point estimate
   or inside its bootstrap interval. Otherwise the new estimates replace them
   in the paper's main text and the paper says the earlier ones were off.
3. **Implied reliability of a career-length score** = tau-squared /
   (tau-squared + mean squared standard error), from M2. If it is at or above
   0.70 in any tour-role cell, the paper must say so; otherwise it states that
   the model-based reliability agrees with the split-half results.
4. **Is clutch variance distinguishable from zero?** Likelihood-ratio test of
   the random slope variance and covariance in M1 (ML fits, 50:50 mixture of
   chi-squared with 1 and 2 degrees of freedom), reported per cell with its p.

Nothing else is tested, and no estimator or threshold is added after seeing
results.
