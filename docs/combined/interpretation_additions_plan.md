# Interpretation additions: plan (self-registered, written 2026-11-20 before the script exists)

Status: written before `src/robustness/interpretation_additions.py` and `src/figures/make_interpretation_figure.py`
were created. Like the other plans it is self-registered; its order cannot be independently verified
(`docs/combined/preregistration_timeline.md`). These are descriptive additions that make the committed results easier to
read for a tennis audience. No new hypothesis test is added and no committed number changes.

## Parts

**A. Empirical repeat check (model-free companion to Table S21).** For each tour and each of five outcomes (serve clutch,
return clutch, all-shot unforced-error clutch R2, all-shot winner clutch R3, forehand-error clutch R4) and each of 1,000
random balanced half-splits (the committed design, seed 20261124): take the players placed in the top quartile of the
outcome on half A (quartile threshold among players with a defined score on both halves) and record the share of them
that are in the top quartile on half B. Report the median and 2.5th to 97.5th percentile over splits (chance is 25%).
For comparison report the model's projection for records of the same (half) length, computed from the same split's raw
half-versus-half correlation with the exact bivariate-normal formula of `label_accuracy.py` (median over splits).
Interpretation rule fixed in advance: the empirical median is described as consistent with the projection if it lies
within the projection's 2.5th to 97.5th percentile range; otherwise the difference is reported as a limit of the
normal-model projection.

**B. Points per match.** For each player the number of serve and return points per charted match in the top leverage
quartile (quartile thresholds from the player's serve points, or return points, as in the paper). Report the median over
players, and the product with the committed true spread (ext_c_true_spread.csv, variance estimator) as the points per
match one true standard deviation of clutch is worth if all of it came from the top quartile: true SD (as a proportion)
times top-quartile points per match.

**C. Calibration against ordinary ability.** The standard deviation across players of the overall serve-point and
return-point win rate (percentage points), raw and corrected for sampling noise (raw variance minus the mean binomial
variance p(1-p)/n), next to the committed true clutch spread (serve 2.15, return 1.22 for ATP; 1.88 and 1.31 for WTA)
and the 4-point planted spread of the positive control.

**D. Noise in tennis terms.** The median number of top-leverage-quartile serve and return points per player over the
charted record, and the binomial standard error of a win rate on that many points (percentage points).

## Figure

One two-panel figure for Section 6. (a) Bootstrap rank intervals (committed `a3c_cluster_bootstrap_players.csv`, no new
analysis) for the nine most charted players in the ATP pool, serve and return; the selection rule (most charted) is
fixed here so the panel is not cherry-picked. (b) How often a top-quartile label is right (committed
`label_accuracy.csv`): ATP and WTA bars for serve, return, all-shot errors and all-shot winners, plus the 0.70 and 0.90
reference cases, 25% chance line, whiskers for the 2.5th to 97.5th percentile of the reliability estimate.

## Validation before writing (abort if any fails)

Hitter parity; the serve and return original-split reliabilities reproduce the paper's within 0.001; the half-A and
half-B values reproduce `allshots_reliability.csv` serve and return original-split reliabilities; the point counts per
player equal the committed `n_serve_high_leverage` style counts (serve bucket sizes) in order of magnitude.

## What would change the paper

If the empirical repeat share is below the projection's range, the label-accuracy paragraph says so. If it is above, the
paragraph says the projection is conservative. Either way both numbers are reported. Nothing is dropped.

## Not done

No new outcomes, no new quartile definitions, no tests of significance.
