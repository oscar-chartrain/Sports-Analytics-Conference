# Shrinkage-Estimator Reliability: Pre-Registration and Results

## Pre-registration

Written before computing a single shrunk clutch value or looking at any
shrinkage-based reliability number.

### Why this check

`split_half_reliability.md` found the clutch score's split-half
reliability poor to moderate (0.23-0.58 depending on tour/role, 0.055 for
WTA return), and its own follow-up ruled out one candidate fix (a
continuous-slope construction using 100% of a player's points instead of
a quartile split made reliability equal or worse, not better). That
follow-up's conclusion was that the limitation is more likely a
genuinely small true effect relative to per-point noise than a fixable
construction choice, but it only tested one alternative construction.
This check tests a second, different candidate fix: **shrinkage**
(partial pooling toward the pool mean, weighted by how much data backs
each player's own estimate), the standard statistical remedy when a set
of noisy per-unit estimates is known to vary in how much data supports
each one, exactly the situation here (Federer's clutch score rests on
far more points than Nakashima's).

If shrinkage improves reliability, that's a genuine, reportable fix,
upgrading the paper's contribution from "here is a diagnosed
measurement problem" to "here is a diagnosed problem and a working
correction." If it doesn't, that's a further, independent piece of
evidence for the "genuinely small effect, high per-point noise"
explanation already favored by the continuous-slope check, since two
different, well-motivated fixes will have failed the same way for two
different reasons.

### Method

For a given tour, role, and half (A or B independently, no information
crosses between halves, exactly as every other split-half check in this
project), let `n_high_i` and `n_low_i` be player `i`'s point counts in
the high- and low-leverage quartile buckets (the same counts already
gating sufficiency, `n_{role}_high_leverage` / `n_{role}_low_leverage`
in `step3_clutch_features.csv`), and let `raw_i` be that player's
observed quartile clutch score on that half (`high['won'].mean() -
low['won'].mean()`, unchanged from the primary construction).

**Step 1 -- per-player sampling variance.** Approximate the sampling
variance of `raw_i` (a difference of two sample proportions) as:

```
Var_i ~= 0.25 * (1/n_high_i + 1/n_low_i)
```

This uses `p(1-p) = 0.25`, the maximum value `p(1-p)` can take (at `p =
0.5`), as a stand-in for each bucket's true win probability, rather than
each player's own observed `high['won'].mean()` / `low['won'].mean()`.
This is a deliberate simplification: the point counts already exported
give `n_high_i` / `n_low_i` directly, but not the two bucket win rates
separately (only their difference, `raw_i`, is exported), and recovering
them would require re-deriving point-level data already computed once
at real cost. Because tennis point-win probabilities in these buckets
are generally not far from 0.5 (serve win rates cluster around 0.55-0.65
tour-wide, per `docs/atp/03_leverage_clutch/empirical_p_variant.md`),
`p(1-p)` is not far below its 0.25 ceiling in practice, so this is a
mild, not severe, approximation, and it is conservative in the specific
sense that it can only overstate each player's sampling variance,
never understate it, which if anything biases this check toward
under-shrinking, not over-shrinking, relative to the true optimal
amount.

**Step 2 -- between-player variance.** Estimate the true (non-sampling)
variance in clutch score across players via a simple method-of-moments
estimator, in the spirit of DerSimonian-Laird:

```
tau^2 = max(0, Var(raw_i across players) - mean(Var_i across players))
```

Floored at zero: if the observed spread across players is no larger
than sampling noise alone would produce, the best estimate of the real
between-player variance is zero, meaning every player's true clutch
score is indistinguishable from the pool mean given this data, itself
an informative, reportable possibility, not a failure of the method.

**Step 3 -- shrinkage weight and shrunk estimate.**

```
B_i = tau^2 / (tau^2 + Var_i)
shrunk_i = mean(raw) + B_i * (raw_i - mean(raw))
```

`B_i` is close to 1 (little shrinkage) for players with large `n_high_i`
/ `n_low_i` (low `Var_i`), and close to 0 (heavy shrinkage toward the
pool mean) for thin-data players. If `tau^2 = 0`, every player is
shrunk all the way to the pool mean regardless of their own data volume.

**Step 4 -- reliability.** Identical to every other measure in
`split_half_reliability.md`: Pearson r between `shrunk_i` on half A and
half B, across players sufficient in both halves, Spearman-Brown
corrected to project full-length reliability. Steps 1-3 are performed
independently on half A and half B (separate `mean(raw)`, separate
`tau^2`, separate `Var_i`), exactly paralleling how entropy and the raw
clutch score are already computed independently per half elsewhere in
this project, so no information leaks from one half to the other.

### Commitment (fixed before running)

1. Reported for both tours and both roles (4 combinations), regardless
   of outcome, directly comparable to the existing quartile (0.572 /
   0.578 / 0.231 / 0.055) and continuous-slope (0.465 / 0.256 / 0.542 /
   -0.026) reliability figures in `split_half_reliability.md`.
2. This is a reliability check only. It does not rerun the primary
   entropy-clutch hypothesis test with a shrunk outcome variable, and it
   does not retroactively replace the pre-registered quartile clutch
   score as the primary outcome even if reliability improves. A
   meaningful improvement would be reported as a candidate secondary
   measure for a future check, per the same discipline already applied
   to the continuous-slope construction.
3. The p=0.5 conservative-variance simplification (Step 1) is named
   here, before running, as a limitation of this specific check, not
   introduced after seeing whether it helped or hurt the result.
4. This section will not be edited after seeing the computed values.

## Results

Written after running `src/robustness/shrinkage_reliability.py` exactly as
specified above. Cross-checked first: recomputing the raw quartile
`r_full` from the same (tour, role, half) data used here reproduces
`split_half_reliability.md`'s documented figures exactly in all four
cases, confirming this check's data pipeline is aligned with the
established one before trusting the shrinkage numbers built on top of
it.

| Tour | Role | Quartile r_full | Continuous-slope r_full | Shrinkage r_full | Delta (shrinkage vs. quartile) |
|---|---|---|---|---|---|
| ATP | Serve | 0.572 | 0.465 | 0.594 | +0.022 |
| ATP | Return | 0.231 | 0.256 | 0.371 | +0.140 |
| WTA | Serve | 0.578 | 0.542 | 0.624 | +0.046 |
| WTA | Return | 0.055 | -0.026 | 0.132 | +0.077 |

Unlike the continuous-slope construction, which improved reliability in
none of the four cases (equal or worse in three of four), shrinkage
improves it in **all four**, and the improvement is largest exactly
where the problem was worst: ATP return climbs from "poor" (0.231)
toward, though still below, acceptable (0.371), and WTA return more than
doubles (0.055 to 0.132).

**This is a genuine, if partial, positive result.** It is the first
candidate fix tested in this project that actually helps rather than
leaving reliability unchanged or making it worse. That is worth
reporting plainly, per the same discipline as every other check here.

**It does not solve the problem.** None of the four shrunk reliability
figures clear the pre-registered 0.70 "acceptable" threshold. Serve
clutch, already borderline, edges closer to acceptable but does not
reach it (0.594, 0.624). Return clutch, the more severe case, improves
substantially in relative terms but remains "poor" for ATP (0.371) and
still far below any usable threshold for WTA (0.132). The headline
conclusion of `split_half_reliability.md` is therefore essentially
unchanged: return-side clutch scores, particularly for WTA, should
still be read as measured too imprecisely to bear much evidentiary
weight. Shrinkage narrows the gap; it does not close it.

**A caveat worth naming plainly, not smoothed over.** Part of any
shrinkage-based reliability improvement is a structural, close to
mechanical, consequence of the method itself: pulling noisy estimates
toward a common mean compresses variance in the "noise" direction,
which tends to increase agreement between two independently shrunk
halves whenever there is *any* real signal (`tau^2 > 0`) to anchor the
shrinkage target. This is the intended, legitimate mechanism behind why
shrinkage estimators are used at all (the same statistical principle
behind the well-known Stein's-paradox result), not a computational bug,
but it means the *size* of the improvement should be read as suggestive
of a real, if modest, reduction in noise, not as a precisely-calibrated
estimate of how much true signal exists. Combined with this check's own
pre-registered simplification (Step 1's `p=0.5` variance approximation,
and a simple, non-REML method-of-moments estimator for `tau^2`), the
specific improvement numbers above should be treated as a first-pass
demonstration that shrinkage helps at all, not as a final, optimized
reliability figure.

### How to reproduce
```
python3 src/figures/export_split_half_clutch_counts.py
python3 src/robustness/shrinkage_reliability.py
```
The first script needs `results/figures/split_half_raw_{atp,wta}.csv`
already produced by `export_split_half_data.py`, and adds the
leverage-bucket point counts those files were missing. Both need the raw
MCP data already present locally in `results/{tour}/`.
