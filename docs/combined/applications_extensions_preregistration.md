# Robustness Extensions: Pre-Registration

**Written 2026-11-11, before any script for these analyses existed.** Nothing
below has been computed or looked at. Decision rules are fixed now; anything
changed afterwards goes in the Deviations log at the bottom, with date and
reason, and is reported as a deviation in the paper.

These three analyses extend the reliability finding in
`applications_preregistration.md` (Analyses 1 to 3 there). They address three
objections a reviewer could raise: (A) the headline reliabilities come from a
single, arbitrary split of the data; (B) the clutch statistics broadcasters
actually quote are break-point conversion and save rates, not leverage ratios;
(C) "unreliable" says nothing about how large the true differences between
players are. None of them changes the primary pre-registered test.

## Shared inputs (fixed)

- Raw MCP files and player pools exactly as in the earlier pre-registration
  (91 ATP, 55 WTA), p = 0.65 leverage, MIN_OBS = 30, same cached point table.
- "The original split" is the existing interleaved A/B assignment from
  `split_half_reliability.split_matches()`. Reliability = Spearman-Brown
  corrected split-half correlation across players, `formulas.spearman_brown`.

---

## Analysis A: Reliability across many random splits

### Procedure
1. For each tour, take the globally date-sorted list of relevant matches (the
   one `split_matches()` uses). For each of R = 1,000 replicates, randomly
   permute that list and assign alternate positions to half A and half B
   (so halves are balanced in match count, exactly as in the original, but the
   assignment is random). NumPy seed 20261111.
2. In each replicate compute, independently per half and per player: serve
   quartile clutch, return quartile clutch, LR serve, LR return, faithful BLR
   (mean of the two LRs) and pooled LR, using the same sufficiency floors as
   before. Compute split-half r and Spearman-Brown reliability across players.
3. Report, per tour and measure: the reliability from the original split, the
   median over random splits, the 2.5th and 97.5th percentiles, and the share
   of random splits with reliability < 0.70.
4. Entropy is **not** re-split: its extraction is slow, and its reliability is
   not the contested claim. This is stated as a limitation.

### Validation (must pass before results are trusted)
Applying the *original* alternating assignment through this new vectorised
code must reproduce the already-reported original-split reliabilities
(`results/applications/a1_blr_reliability.csv`) within 0.001 for every measure
and tour. If it does not, stop and investigate before reporting anything.

### Decision rules, committed in advance
- A headline statement of the form "measure X has reliability below 0.70" is
  called **robust to the split** if at least 95% of random splits give
  reliability < 0.70. Otherwise the paper says the statement is
  split-dependent and gives the share.
- The original split is called **typical** if its value lies inside the
  2.5th to 97.5th percentile range of the random splits. If it lies outside,
  that is disclosed in the paper as an unusual draw.
- The paper reports the random-split median and range next to the original
  value in the reliability tables whichever way this comes out.

---

## Analysis B: Reliability of break-point conversion and save rates

### Definitions (fixed)
- A **break point** is any point for which `parsing.get_game_situation` returns
  `'break_point'` (returner one point from winning a standard game).
  Tiebreak points are not break points.
- **Baseline points**: standard-game points in the same role that are not break
  points (situations `normal`, `approaching_break_point`, `deuce`,
  `game_point_server`). Tiebreak points are excluded from baselines.
- **BP conversion** (return role): share of the player's break-point return
  points that the player won. **BP save** (serve role): share of the player's
  break-point serve points that the player won.
- **Baseline rate**: same share over baseline points in that role.
- **Clutch differential** = BP rate minus baseline rate, per role. This is the
  clutch-specific component: it removes the part of the raw rate that merely
  reflects overall serving or returning ability.

### Procedure
1. Same halves as every other split-half result (original split).
2. Per player, per half, per role: BP rate, baseline rate, differential.
   Sufficiency: at least 30 break points in that role in that half.
3. Spearman-Brown reliability with Fisher-based 95% CI, for the raw BP rate
   and the differential, by tour and role.
4. Full-sample correlation across players between the raw BP rate and the
   baseline rate, by role, to show how much of the raw statistic is general
   skill.
5. Report the number of players excluded by the sufficiency floor.

### Interpretation, committed in advance
| Raw BP rate | Differential | What the paper says |
|---|---|---|
| >= 0.70 | < 0.70 | Break-point stats are reliable as skill measures but not as clutch measures: the reliability problem extends to the clutch-specific component. |
| >= 0.70 | >= 0.70 | The reliability problem is specific to leverage-weighted construction; the paper narrows its claim to that metric family. |
| < 0.70 | < 0.70 | The claim extends to break-point statistics themselves. |
| < 0.70 | >= 0.70 | Reported as it stands, with the sufficiency counts, and not interpreted beyond what the numbers show. |

Reported per tour and role; if roles or tours fall in different rows, each is
described separately. Caveat stated in the paper: break-point situations are
not randomly assigned (a server facing break points is more often in a weak
state), so the differential is a descriptive contrast, not a causal estimate
of clutch.

---

## Analysis C: How large is the true spread of clutch?

### Definitions
Using the full-sample p65 quartile clutch scores and bucket sizes, per tour and
role (the same shrinkage model as `shrinkage_reliability.py` and Analysis 2):

- Sampling variance of player i: var_i = 0.25 (1/n_high,i + 1/n_low,i).
- True between-player variance: tau^2 = max(0, Var(raw scores) - mean(var_i)).
- **True SD** = sqrt(tau^2). **Noise SD** = sqrt(mean(var_i)).
- **Signal-to-noise** = tau^2 / mean(var_i).
- Second, independent estimate: the across-player covariance between the
  original-split half-A and half-B scores, an estimate of the true variance
  that does not use the binomial variance assumption. True SD = sqrt of that
  covariance if positive; otherwise reported as "no detectable true spread".

### Procedure
1. Compute all quantities above, by tour and role, in percentage points.
2. 95% interval on tau^2 and on the true SD by player bootstrap (resample
   players with replacement, B = 2,000, seed 20261111; the covariance estimator
   is bootstrapped over the same player draws).
3. Report the typical per-player standard error (mean of sqrt(var_i)) beside
   the true SD, so the reader can compare the spread between players with the
   noise on each player.

### Committed reporting
- If the two estimators disagree by more than a factor of 2, both are reported
  and the paper states the range rather than a single figure.
- If tau^2 = 0 or the bootstrap interval includes zero, the paper says "no
  detectable stable difference between players", not "small difference".
- The binomial variance assumption (win rates are not exactly 0.5) is named as
  an approximation in the paper.

---

## What would change the paper

| Outcome | Change |
|---|---|
| Fewer than 95% of random splits give reliability < 0.70 for a measure | That statement is reworded as split-dependent, with the share |
| Original split outside the random-split range | Disclosed as an unusual draw; random-split median becomes the headline |
| Break-point differential reliable (>= 0.70) | Claim narrowed to leverage-weighted metrics (see table) |
| True SD interval includes zero for a role | "No detectable stable differences" replaces "small differences" for that role |

## Deviations log

(None yet. Any change to the procedures above after this date is recorded here
with date and reason.)
