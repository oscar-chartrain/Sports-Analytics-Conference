# Pre-registration: do the stable parts of clutch scores mean anything? (validity checks)

Written 2026-11-19, before `src/robustness/validity_checks.py` was run. Self-registered, written
after all earlier results were known (see `preregistration_timeline.md`). No result of these
checks had been seen when this was written. The code is first run in a validation-only mode.

## Why

The paper shows that clutch scores are noisy (low reliability) and that real differences between
players are small. A reviewer can still ask whether the stable part of a clutch score measures
anything: if two different indicators of clutch (say serve points and forehand errors) are both
partly stable, do they pick out the same players? And does a player's clutch score predict their
later clutch beyond their overall level (a clutch score that only echoes ability is not clutch)?
Section 4.4 also found that one shot type (forehand errors) is the most reliable; the paper needs to
say how reliable it is once shrunk, and how much data it needs.

## Design (ATP and WTA; paper pools of 91 and 55 players; paper definitions, p = 0.65, quartile
rule, floors)

Outcomes (all signed so that higher means better under pressure): serve-point clutch (S),
return-point clutch (Rt), rally-point clutch (R1), unforced-error clutch over all shots (R2),
winner clutch over all shots (R3), forehand errors (R4), backhand errors (R5). R6 to R9 are left
out (their reliability is about zero, so nothing can be learned).

Chronological split: each player's earlier half of charted matches (first ceil(n/2) by date) and the
later half, as in `slope_chronological.py`. Using different matches in the two halves means no
shared points, so correlations between outcomes cannot arise from the same points.

**V-A. Stability beyond ability.** For each outcome, the correlation of the early score with the late
score, and the partial correlation controlling for the early overall rate in that role (S: serve-point
win rate; Rt: return-point win rate; R1: rally-point win rate; R2: unforced errors per shot; R3:
winners per shot; R4, R5: errors per forehand or backhand shot). A clutch score that only repeats
ability would lose its stability when the overall rate is held fixed.

**V-B. Convergence across indicators.** For every pair of the 7 outcomes (21 pairs), the correlation of
the early score of one with the late score of the other, averaged over the two directions (the
cross-time correlation). Reported with the stability (same outcome, early and late) of both, and the
correlation divided by the square root of the product of the two stabilities when both are positive
(a disattenuated value, descriptive, with no interval). Fisher-z p-value for each pair;
Bonferroni threshold over the 21 pairs per tour, 0.05 / 21 = 0.0024. The mean cross-time correlation
over the 21 pairs, with a 95% player-bootstrap interval (2,000 resamples).

**V-C. The forehand follow-up.** For forehand and backhand errors: 1,000 random balanced splits of the
paper's matches (seed 20261122), raw and empirical-Bayes-shrunk median reliability and share at or
above 0.70 (the paper's shrinkage routine), the match-clustered true spread with a 2,000-resample
player bootstrap, and matches needed for reliability 0.70 (Spearman-Brown on the median). The
chronological Spearman-Brown reliability with a player bootstrap interval.

## Decision rules, fixed in advance

- "Reliably measured" is the paper's criterion: median at least 0.70 and at least 95% of splits.
- V-A: the paper reports the partial correlations and says an outcome's stable part is not just ability
  if the partial correlation keeps the sign and at least half its size and has p below 0.05 / 7 = 0.007.
  Otherwise it says the stability cannot be separated from ability.
- V-B: if at least half of the 21 pairs on a tour are below the Bonferroni threshold, the paper says
  that clutch indicators converge on that tour; if none is, that they do not converge and the stable
  parts are outcome-specific; otherwise it reports the count and the pairs.
- V-C: reported as computed. If a shrunk forehand or backhand median reaches 0.70 with at least 95% of
  splits, the paper says the criterion is met for that shot and names the pool.
No estimator, threshold, pool, seed or rule is changed after seeing results.

## Validation (the script aborts if any fails)

V1. Chronological Spearman-Brown reliability for S, Rt, R1, R2 and R3 equals the committed values in
`chronological_reliability.csv` to 0.001.
V2. The per-match sums routine for shot-type outcomes reproduces `rally_extension.sums` for R2 and R3
(per-match sums, 1e-12) and the full-sample forehand and backhand scores equal
`all_shots_analyses.evaluate` (1e-12).
V3. The overall-rate routine splits each player's totals exactly: early plus late counts equal full-sample
counts (shots, errors, points).
V4. The 21 cross-time correlations are symmetric after averaging (the matrix is built from both
orders; the script checks every pair uses both).
V5. At the shrinkage step, raw random-split medians for R2 and R3 are within 0.02 of the committed
`allshots_reliability.csv` medians (different splits; Monte Carlo error only).

## Not done

No external criterion (for example later match results or tiebreak outcomes): the check can show
whether indicators agree and persist, not that they predict winning. No new outcomes after seeing
results. No tournament, surface or opponent adjustment (the confounder check showed little to
remove). The pool is selected (Section 8).

## Disclosure recorded 2026-11-19 (before the full run)

A validation-only WTA run (40 random splits, 40 to 50 bootstrap resamples) printed its results as
well as the validation lines; they were seen. V1 to V4 passed. V5 failed in that run only because
40 splits are too few to compare medians with the committed ones (the check is now enforced in the
full run only). What was seen: WTA stability early to late of 0.25 (S), 0.06 (Rt), 0.13 (R1), 0.16 (R2),
0.43 (R3), 0.25 (R4), 0.05 (R5); 0 of 21 cross-time pairs below the Bonferroni threshold; mean
cross-time correlation -0.03; WTA forehand-error shrunk median about 0.57 and backhand 0.44 (40
splits). No pool, outcome, estimator, threshold, seed or decision rule was changed after seeing them.
