# Pre-registration: positive control (would the pipeline detect real clutch?)

Written 2026-11-18, before `src/robustness/positive_control.py` was run. Self-registered, written
after all earlier results were known (see `preregistration_timeline.md`).

## Why

Every reliability result in the paper is "the observed score is not reliable." A critic can reply that
the pipeline itself (quartile score, 30-point floor, split-half, Spearman-Brown) may be unable to
return a high reliability even when stable clutch differences exist. A positive control answers
that: plant stable clutch differences of known size in the real design (same players, points,
leverage, matches, splits) and ask how large they must be before the pipeline reports a reliable score.

## Design (ATP and WTA; outcomes S, Rt, R1; paper pool of 91 and 55 players)

For each player and outcome, redraw every point's outcome as Bernoulli with the player's own
full-sample win rate on that role's points (rally points for R1), plus a planted shift d_j on the
points in the player's top leverage quartile for that role (top quartile and rally-decided for R1),
d_j ~ N(0, s) independently across players. No match-level, opponent or surface effect is
included, so the simulated noise is binomial only; real data have extra match-to-match variance,
so the simulated reliability is an upper bound at a given s.

Grid of planted spreads s (pp): 0, 1, 2, 3, 4, 6, plus the paper's own estimated true spread for the
cell (Table 3: ATP S 2.15, Rt 1.22, R1 1.62; WTA S 1.88, Rt 1.31, R1 1.06). For each s: 40 planted
draws x 25 random balanced splits of the paper's matches = 1,000 reliability values (seed 20261121 +
offsets), the paper's reliability routine (`rx.sums`, `rx.diff_se`, `rx.rel_from`).

Reported: median, 2.5th and 97.5th percentile and share at or above 0.70 of the split reliabilities
per cell and s; the smallest grid s at which the paper's criterion (median at least 0.70 and at
least 95% of splits at least 0.70) is met; the ratio of that s to the cell's estimated true spread.

## Decision rules, fixed in advance

- Validation V1 (null): at s = 0 the median reliability must be within 0.15 of 0 (|median| <= 0.15)
  in every cell, i.e. the pipeline does not manufacture reliability from noise.
- V2 (consistency): at s = the paper's estimated true spread, the simulated median must lie within
  0.15 of the observed random-split median (S 0.53 / 0.41, Rt 0.24 / 0.27, R1 0.44 / 0.25 for
  ATP / WTA). If it does not, the paper does not use the positive control to argue that the
  estimated spread explains the observed reliability, and says so.
- V3: the simulated top-quartile membership and halves use the same arrays as the paper's
  analysis (the script asserts the real-data original-split reliability is reproduced to 0.001 before
  any simulation).
- Interpretation: if the criterion is met at some s the paper reports that s (the planted spread
  the pipeline needs) next to the estimated spread. If it is met at no grid s up to 6 pp, the paper
  reports that the pipeline cannot reach the criterion at plausible spreads and says the
  pipeline, not only the data, limits reliability.
No grid, threshold, seed or rule is changed after seeing results.

## Not done

No match-level variance in the simulation; no planted effects on rally error and winner outcomes
(R2, R3); no variation in the player's number of matches.

## Amendment recorded 2026-11-18 (before the full run)

The plan first said 4 planted draws x 50 splits. A validation-only WTA run (1 draw x 8 splits;
the null V1 check was not enforced in that mode) showed that splits within one planted draw share
that draw's chance pattern: one cell's null median was +0.27, by luck. It also printed some grid
results (WTA serve: median 0.03 / -0.10 / 0.39 / 0.56 / 0.82 / 0.90 at s = 0 / 1 / 2 / 3 / 4 / 6 pp;
return null +0.27). The sample sizes were raised to 40 draws x 25 splits so draw-to-draw luck
averages out. No grid, threshold, seed rule or decision rule was changed; the original-split check
(V3) passed in that run.
