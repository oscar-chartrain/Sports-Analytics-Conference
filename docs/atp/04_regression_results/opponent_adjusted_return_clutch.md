# Opponent-Adjusted Return Clutch: Pre-Registration and Results

## Pre-registration

Written before computing a single opponent-adjusted clutch value or
looking at any resulting reliability number.

### Why this check

`split_half_reliability.md`'s verification section named a specific,
untested hypothesis for why WTA return clutch reliability is so poor
(0.055): "some of that noise could be a mix-of-opponents effect... if a
player's half-A and half-B opponents differed somewhat in serve
quality," and explicitly deferred it as "exactly the
opponent-strength-adjustment question this project has explicitly
deferred since Step 1." This check tests that specific hypothesis
directly, narrowly scoped: does adjusting return clutch for the serving
opponent's own strength improve split-half reliability, parallel to the
continuous-slope and shrinkage checks already run.

This is explicitly **not** a revision of the primary, pre-registered
clutch construction. `serve_clutch_p65` / `return_clutch_p65` remain
this project's primary outcome variables regardless of what this check
finds. This is a diagnostic, exactly like the continuous-slope and
shrinkage follow-ups, testing one more candidate explanation for the
reliability problem already documented.

### Why return clutch only

The mix-of-opponents hypothesis was raised specifically for return
clutch: when a player is *returning*, winning the point depends heavily
on the *server's* (opponent's) own serve strength on that point, a
source of variance the returner does not control. When a player is
*serving*, their own execution dominates more directly. This check is
scoped to return clutch only; a symmetric serve-side check (adjusting
for the returning opponent's own return strength) is a natural
extension but out of scope here.

### Method

Reuses `build_clutch_features(..., return_points=True)` unmodified,
already built and validated for `continuous_slope_reliability.py`, which
exposes the point-level table (`match_id`, `server`, `returner`,
`server_won_point`, `leverage_p65`) this function already computes
internally. No new parsing or hitter-attribution logic is introduced.

For a given half (A or B, computed independently, exactly as every other
split-half check in this project, no information crosses between
halves):

1. **Opponent baseline serve-win-rate, leave-one-out.** For each
   (target player, opponent) pair appearing in the target player's
   return points, compute the opponent's own serve-win-rate across
   *all their service points in that half except points against this
   specific target player*. This avoids the circularity of using an
   opponent's average serve strength to adjust a return-clutch score
   partly computed from points against that very opponent -- a real,
   if usually small, form of leakage a simple global lookup would not
   catch, but a leave-one-out estimate does.
2. **Sufficiency floor and fallback.** If fewer than `MIN_OBS` (30,
   this project's existing floor, reused unchanged) of the opponent's
   own service points remain after leave-one-out exclusion, fall back
   to that half's tour-wide empirical server point-win rate
   (`data_io.compute_empirical_p()`, the same function already used
   for the tour-specific empirical-p leverage variant) as the expected
   probability instead. This is a documented simplifying assumption:
   thin-data opponents get a population-average expectation rather
   than a player-specific one, rather than being dropped and shrinking
   the sample.
3. **Residual, not raw win indicator.** For each return point, compute
   `residual = won - expected_win`, where `expected_win = 1 -
   opponent_serve_win_rate` (the target player's expected win
   probability against that specific server, whether player-specific
   leave-one-out or the tour-wide fallback).
4. **Adjusted clutch score.** `opponent_adjusted_return_clutch =
   mean(residual | leverage_p65 in top quartile) - mean(residual |
   leverage_p65 in bottom quartile)`, using the identical quartile
   boundaries and `MIN_OBS` gating on bucket size as the primary
   construction. Only the quantity being differenced changes (residual
   vs. raw win indicator); the leverage-based bucket definition does
   not.
5. **Reliability.** Split-half Pearson r between half-A and half-B
   `opponent_adjusted_return_clutch`, across players sufficient in both
   halves, Spearman-Brown corrected, directly comparable to the
   existing quartile (ATP 0.231, WTA 0.055), continuous-slope (ATP
   0.256, WTA -0.026), and shrinkage (ATP 0.371, WTA 0.132) figures
   already in this project's docs.

### Commitment (fixed before running)

1. Reported for both tours, regardless of outcome, directly comparable
   to the three existing return-clutch reliability figures.
2. This does not replace or retroactively edit the primary, pre-registered
   `return_clutch_p65` construction, regardless of what is found.
3. The rate of opponents requiring the tour-wide fallback (insufficient
   leave-one-out data) will be reported explicitly, since a high fallback
   rate would itself be informative about how much this adjustment could
   plausibly help.
4. If this check meaningfully improves reliability, that will be
   reported as evidence the mix-of-opponents hypothesis has real
   explanatory power, a genuine, if partial, answer to a question this
   project has carried since Step 1. If it does not, that will be
   reported plainly as ruling out this specific candidate explanation,
   parallel to how the continuous-slope check ruled out "the quartile
   split is the problem."
5. This document will not be edited after seeing the computed values.

## Results

Written after running `src/robustness/opponent_adjusted_return_clutch.py` exactly
as specified above.

### Fallback rate (commitment #3)

The leave-one-out opponent baseline required the tour-wide empirical-p
fallback (opponent had fewer than `MIN_OBS` = 30 remaining service
points after excluding the target player's own matches against them) at
a modest rate on both tours: ATP 4.3% (half A) / 4.5% (half B), WTA 6.0%
/ 6.6%. The adjustment is opponent-specific for the large majority of
return points on both tours; this is not a case where the check
degenerates into the tour-wide average.

### Reliability, compared to the existing constructions

| Tour | Quartile (original) | Continuous-slope | Shrinkage | Opponent-adjusted |
|---|---|---|---|---|
| ATP | 0.231 | +0.256 | 0.371 | **0.182** |
| WTA | 0.055 | -0.026 | 0.132 | **-0.106** |

Opponent adjustment does not improve reliability on either tour. It is
worse than the original quartile construction on both: ATP falls from
0.231 to 0.182, and WTA falls from a already-poor 0.055 to -0.106, a
negative split-half correlation, meaning the two halves are actively
uncorrelated, not just noisy, the same qualitative failure mode the
continuous-slope construction produced for WTA return (-0.026).

### Honest verdict, per commitment #4

**The mix-of-opponents hypothesis, raised in `split_half_reliability.md`
as an untested possible explanation for WTA return's near-zero
reliability, is not supported by this check, and the adjustment makes
reliability worse, not better, on both tours.** This is a genuine, if
negative, answer to a question this project has carried since Step 1: it
is not simply "unresolved," it is now tested and does not hold up as an
explanation.

A plausible reason this hurts rather than helps: the opponent-strength
baseline is itself an estimate, built from a finite, sometimes thin,
sample of that opponent's own service points (hence the fallback rate
above). Subtracting a noisy covariate from an already-noisy outcome does
not reduce variance the way shrinkage's principled pooling toward a
common mean does, it can compound it, adding a second source of
estimation error on top of the existing small-sample noise in the
returner's own win rate. This is consistent with, and reinforces, this
project's now-repeated finding across three independent candidate fixes
(continuous-slope, opponent adjustment, and, more successfully,
shrinkage): return clutch's reliability problem is not primarily a fixable
construction artifact. Shrinkage remains the only one of the three that
helps, and even it does not fully solve the problem
(`shrinkage_reliability.md`).

### How to reproduce
```
python3 src/robustness/opponent_adjusted_return_clutch.py
```
Needs the raw MCP data already present locally in `results/{tour}/`; no
new data source. Same cost profile as the other split-half checks (one
clutch-only extraction pass per half, per tour).
