# Applications Analyses: Pre-Registration

**Written 2026-11-03, before running any of the three analyses below.**
No script for these analyses exists yet, and no BLR reliability, data-requirement
projection, or bootstrap interval has been computed or looked at. Every decision
rule in this document is fixed now; anything changed later goes in the
Deviations log at the bottom, with the reason, and is reported as a deviation
in the paper.

These three analyses feed the paper's Applications section. None of them
changes the primary pre-registered test (entropy vs. clutch), which is final.

## Why these three, and why now

The paper's central claim is that leverage-weighted clutch scores are too
unreliable to rank players. Three gaps stand between that claim and something a
scout, broadcaster or analyst could act on:

1. **The claim is inferred, not shown, for metrics in actual use.** All
   reliability numbers so far are for this project's own quartile clutch
   score. Its link to the field's published metric is a convergent-validity
   correlation (r = 0.793) with a *pooled* leverage ratio. Tennis Abstract's
   published Balanced Leverage Ratio (BLR) is not pooled: it is "simply the
   average of LR on serve points and LR on return points"
   (Tennis Abstract, "Roger Federer Wasn't Clutch, But He Was Almost Clutch
   Enough"). Analysis 1 measures the reliability of the faithful BLR directly.
2. **"Unreliable" has no unit a practitioner can use.** Analysis 2 converts
   reliability into the number of charted matches a player needs before a
   clutch score reaches an acceptable reliability.
3. **Reliability is a pool-level statistic; practitioners talk about named
   players.** Analysis 3 puts uncertainty intervals on individual players'
   clutch scores and ranks.

## Shared inputs (fixed)

- Raw MCP files already present locally in `results/atp/` and `results/wta/`
  (the same pulls behind every documented result; not re-fetched, so numbers
  stay comparable).
- Player pools: the existing 91 ATP and 55 WTA qualified players (≥40 charted
  matches), unchanged.
- Leverage: the existing Morris engine (`core/formulas.py`), primary variant
  p = 0.65 throughout. No other variant is used in these analyses.
- Clutch score: the existing quartile construction (`features.quartile_clutch`),
  MIN_OBS = 30, unchanged.
- Split: the existing interleaved A/B match split from
  `split_half_reliability.split_matches()`, reused unchanged, so Analysis 1's
  numbers sit on exactly the same halves as every reliability already reported.

---

## Analysis 1: Split-half reliability of Tennis Abstract's BLR

### Definitions
For a player and a role (serve or return), using p65 leverage:

- LR_role = (mean leverage of that role's points the player **won**) /
  (mean leverage of that role's points the player **lost**)
- **BLR = (LR_serve + LR_return) / 2**: the faithful Tennis Abstract
  definition. This is the primary quantity.
- **Pooled LR**: mean leverage of all points won / all points lost, serve and
  return together. This is what `features.build_clutch_features()` already
  calls `blr_combined`. Reported as a secondary row for continuity, since the
  existing r = 0.793 convergent-validity figure was computed against it.
- LR_serve and LR_return are also reported individually (secondary), because
  they are the role-matched comparison to the role-specific quartile clutch
  scores.

Sufficiency: a player's LR_role in a half is computed only if they have at
least MIN_OBS = 30 points won **and** 30 points lost in that role in that half.
BLR requires both LR_serve and LR_return. (Given every pool player has
hundreds to thousands of points per role per half, this floor is not expected
to bind; how many players it excludes will be reported.)

### Procedure
1. Same halves as `split_half_reliability.py`.
2. Compute BLR, pooled LR, LR_serve and LR_return independently on half A and
   half B.
3. Split-half Pearson r across players sufficient in both halves;
   Spearman-Brown corrected full-length reliability (`formulas.spearman_brown`).
4. 95% CI: Fisher z interval on the split-half r, endpoints then
   Spearman-Brown transformed.
5. Both tours.

### Sanity checks (must pass before results are trusted)
- In the same run, the entropy, serve-clutch and return-clutch reliabilities
  must reproduce the documented values (ATP 0.925 / 0.572 / 0.231; WTA
  entropy as documented / 0.578 / 0.055) within ±0.005. If they don't, stop
  and investigate before reporting anything.
- Full-sample pooled LR computed by the new code must match the
  `blr_combined` column of the current-run `build_clutch_features()` output
  exactly (same function, same data).
- Report the full-sample correlation between faithful BLR and pooled LR, and
  between faithful BLR and the combined quartile clutch score, so the paper
  states which "BLR" the 0.793 figure refers to.

### Interpretation, committed in advance
Thresholds on the Spearman-Brown reliability of faithful BLR (ATP, primary):

| Result | What the paper says |
|---|---|
| ≥ 0.70 | The "industry metrics are unreliable" claim is **narrowed**: career-aggregated BLR is acceptably reliable; the problem is specific to role-split, quartile-based clutch scores. The Conclusion is rewritten accordingly. |
| 0.50 – 0.70 | Claim stands, worded as "moderate reliability, below the conventional 0.70 threshold". |
| < 0.50 | Claim is **strengthened**: the field's own published metric is poorly reliable even when aggregated over a career. |

Tennis Abstract publishes BLR per match, not per career. This analysis tests
career-aggregated BLR only; the paper will say that a single match contains
far fewer points, so per-match BLR can only be less reliable, but will not
report a per-match number (none is computed here).

---

## Analysis 2: How much data a reliable clutch score needs

This is a **derived projection, not a hypothesis test**, and will be labelled
that way in the paper.

### Primary: Spearman-Brown prophecy
For a measure with full-length reliability ρ, the factor by which data must
be multiplied to reach target reliability ρ* is

  k = ρ*(1 − ρ) / (ρ(1 − ρ*))

- Target ρ* = 0.70 (primary), 0.80 (secondary).
- Inputs, per tour and role: the documented quartile reliabilities (ATP serve
  0.572, return 0.231; WTA serve 0.578, return 0.055), the documented
  shrinkage reliabilities (ATP 0.594 / 0.371; WTA 0.624 / 0.132), and the BLR
  reliabilities from Analysis 1.
- Matches required ≈ k × the median charted-match count of that tour's
  qualified pool (ATP: 74; WTA: computed from `charting-w-matches.csv` for the
  55 players, reported).
- If ρ ≤ 0, the target is reported as **not attainable by adding data**
  (more data cannot raise a reliability that is not positive).

Stated assumption: ρ is the reliability of the pool's full-length measure,
where players have unequal amounts of data; scaling by the median player is
an approximation, and the paper will say so.

### Secondary: per-player reliability under the shrinkage model
Using the full-sample (not split) clutch scores and the existing shrinkage
model from `shrinkage_reliability.py`:

- Sampling variance var_i = 0.25 (1/n_high,i + 1/n_low,i)
- Between-player variance τ² = max(0, Var(raw scores) − mean(var_i))
- Player reliability rel_i = τ² / (τ² + var_i)

Report the share of players with rel_i ≥ 0.70, by tour and role; and the
number of high-leverage-quartile points needed for rel = 0.70
(n* = 0.5 · 0.70 / (0.30 · τ²), assuming n_high = n_low = n*), converted to
matches using the tour's median high-leverage points per charted match for
that role. If τ² = 0, report "no detectable between-player variance".

Consistency check: the primary and secondary projections are expected to be
in the same order of magnitude. If they differ by more than a factor of 3,
the paper reports both and explains why, rather than choosing one.

---

## Analysis 3: Uncertainty on named players' clutch scores and ranks

### Procedure
- Tours: ATP primary, WTA secondary.
- Measures: serve and return quartile clutch (p65), and faithful BLR.
- **Player-cluster bootstrap**: for each player independently, resample their
  own charted matches with replacement (same number of matches as observed),
  recompute the measure on the resampled points (quartile thresholds
  recomputed within each replicate), B = 2,000 replicates, NumPy seed
  20261103. Leverage values are fixed per point (they depend only on score
  state) and are computed once.
- In each replicate, rank all pool players on each measure (rank 1 = most
  clutch). Players are resampled independently, so the rank distribution
  reflects every player's sampling noise at once.
- 95% percentile intervals for each player's score and rank.

### Pre-committed outputs
1. Sinner and Alcaraz (the project's face-validity pair), plus Djokovic and
   Federer: point estimate, score interval, rank interval, per measure.
2. Median width of the 95% rank interval across the pool, per measure.
3. Number of players whose 95% score interval excludes the pool mean.
4. Of the 10 players ranked highest by point estimate, how many have a 95%
   rank interval entirely within the top 20.

All four are reported whatever they show. The named-player figure goes in the
paper whichever direction the intervals point.

### Sanity checks
- A replicate with no resampling (identity weights) must reproduce the
  pipeline's point estimates exactly.
- Mean bootstrap score within ±0.002 of the point estimate for clutch scores
  (larger gaps are reported as bias, not hidden).

---

## What would change the paper

| Outcome | Change |
|---|---|
| BLR reliability ≥ 0.70 | Narrow the headline claim (see Analysis 1 table) |
| Projections show return clutch is unattainable or needs >10× current data | Stated as the main practical rule in Applications |
| Bootstrap rank intervals narrow (median width < 15 ranks) | Report that individual rankings are more stable than pool reliability suggests, and reconcile in Discussion |

## Deviations log

Logged 2026-11-09, after the first run of `src/robustness/applications_analyses.py`.
No decision rule was changed after seeing results; these are clarifications of
under-specified items, plus results that missed a pre-registered tolerance.

1. **Entropy sanity check, source.** The entropy reliability (ATP 0.925, WTA
   0.897) was checked from the committed `results/figures/split_half_raw_{tour}.csv`
   (same code and same halves), not recomputed in this run, to avoid a third slow
   entropy extraction. Reproduced within 0.001. Serve and return clutch
   reliabilities were recomputed in-run and match within 0.001.
2. **"Combined quartile clutch score"** was not defined above. Used the mean of
   the serve and return p65 quartile scores. Reported correlations: faithful BLR
   vs combined quartile r = 0.902 (ATP), 0.866 (WTA); pooled LR vs combined
   quartile r = 0.793 (ATP; this reproduces the documented figure, so the 0.793
   refers to pooled LR, not the faithful BLR), 0.808 (WTA).
3. **Median high-leverage points per match** (Analysis 2 secondary) was taken
   as the median over players of n_high,i / charted matches_i.
4. **Bootstrap bias tolerance missed.** The pre-registered tolerance (mean
   bootstrap score within +/-0.002 of the point estimate) was exceeded for the
   quartile clutch scores: mean absolute bias 0.0018 to 0.0027 across tour/role,
   maximum single-player bias 0.011 (ATP serve), 0.008 (ATP return), 0.008 (WTA
   serve), 0.007 (WTA return). Reported as bias, not corrected. Likely cause:
   quartile thresholds sit on tie clusters of discrete leverage values, so
   resampling shifts which points fall in the top/bottom quartile. Percentile
   intervals are therefore interpreted as approximate. BLR (ratio scale,
   tolerance not applicable) shows max bias 0.002 (ATP), 0.003 (WTA).
5. **Primary vs secondary projection disagree for WTA return.** 2,566 vs 377
   matches (ratio 6.8, outside the pre-registered factor of 3). Both are
   reported. The primary (Spearman-Brown on a reliability of 0.055) is
   extremely sensitive to a near-zero estimate whose own 95% CI spans zero; the
   secondary relies on the shrinkage model's variance decomposition. The paper
   states the range, not a single figure.
5b. All other consistency checks fell within the factor of 3 (ATP serve 1.07,
   ATP return 1.54, WTA serve 1.69).
6. **Rank interval width** is the 97.5th minus the 2.5th percentile of the
   bootstrap rank distribution; "entirely within the top 20" means the 97.5th
   percentile rank is <= 20.
7. A player's bootstrap match resample is shared across serve, return and BLR
   within a replicate (one draw of that player's matches per replicate).

**Outcomes against the "What would change the paper" table**
- BLR reliability: ATP 0.460 (95% CI 0.180 to 0.645), WTA 0.206. Below 0.50:
  the claim is **strengthened**, per the pre-registered rule. Note the pooled LR
  (not the faithful BLR) reaches 0.683 for ATP, near but below 0.70; the paper
  reports both rather than choosing the more favourable one.
- Data needs: ATP return needs about 575 matches (7.8x the median 74) for 0.70;
  WTA return 2,566 (40x) by the primary projection, 377 by the secondary.
  WTA return is over the 10x mark by the primary and not by the secondary.
- Rank intervals: median 95% rank-interval width is 52 to 63 ranks (ATP, of 91),
  far above the 15-rank line, so no reconciliation with pool reliability is
  needed: individual rankings are as unstable as the reliability suggests.
