# Pre-registration: clutch across all shots (serve, return and rally)

Written 2026-11-16, before any of the outcomes below were computed. Status: a
self-registered extension. It was written after every earlier result in this
project was known (the entropy null, the reliability results and the
Applications analyses), so it is pre-specified but not blind to them. The
only data inspection done before writing it was reading raw notation strings
to learn the end-of-point codes (`*` winner, `#` forced error, `@` unforced
error, trailing fault letters for double faults) and checking that the first
parsed shot token is the return of serve (the hitter-parity fix already
documented in `docs/atp/02_entropy_pipeline/step2_README.md`).

## Why

The paper's clutch outcomes treat a point as a serve point or a return point.
That is the right unit for point-win probability, but it ignores what happens
in the rally, and the entropy predictor is built from rally shots. A reviewer
can fairly ask whether the reliability problem is specific to the serve and
return roles, and whether the entropy null survives an outcome that uses every
shot. This extension answers both.

## Definitions

A point is classified by where it ended, from the point's final serve string
(second serve if present, otherwise first):

- **Serve-decided**: ace or service winner (no shot token, ends `*`), or a
  double fault (string ends in a fault letter with no `*`, `#` or `@`).
- **Return-decided**: exactly one shot token (the return was the last shot), or
  no token and ends `#` (return error forced by the serve).
- **Rally-decided**: two or more shot tokens (a third shot or later was hit).

Hitter of token i: the returner if i is even, the server if i is odd (the
documented parity fix). The player who hit the last shot made the error when
the string ends `#` or `@`, and hit the winner when it ends `*`.
Shot families: forehand drive `f`; backhand drive `b`; slice `r` and `s`;
net game `v z o p j k h i`. (Drop shots and lobs are too rare for a
family-level reliability and enter only the all-shot totals.)

Leverage and quartiles are the paper's: p = 0.65 leverage of the point
containing the shot; for each player and half, top quartile = leverage at or
above the 75th percentile of that player's points in that half, bottom quartile
= at or below the 25th (ties included), computed on the player's own points in
the half (serve and return points pooled for the outcomes below that are not
role-specific).

## Outcomes (higher always means better under pressure)

1. **R1, rally-phase point clutch**: win rate on rally-decided points,
   top quartile minus bottom quartile (at least 30 points in each bucket).
2. **R2, all-shot error clutch**: unforced errors per shot hit (return and
   rally shots, serve excluded), bottom quartile minus top quartile, so that
   fewer errors under pressure scores higher (at least 100 shots in each
   bucket).
3. **R3, all-shot winner clutch**: winners per shot hit (return and rally),
   top minus bottom.
4. **R4 to R7, error clutch by shot family** (forehand, backhand, slice, net),
   defined as R2 within the family (at least 100 shots of the family in each
   bucket, else missing).
5. **R8, serve double-fault clutch**: double faults per serve point, bottom
   minus top quartile (at least 100 serve points per bucket).
6. **R9, ace clutch**: aces per serve point, top minus bottom.

## Analyses and decision rules

A. **Reliability.** For each outcome, tour and split: split-half Pearson r
across players, Spearman-Brown corrected, on the paper's original interleaved
split and across 1,000 random balanced splits (seed 20261116). Validation
before anything is reported: the same code must reproduce the paper's serve and
return quartile clutch reliabilities on the original split to within 0.001 (ATP
0.572 and 0.231, WTA 0.578 and 0.055), or the script aborts. "Below 0.70" is
robust if at least 95% of random splits agree, as in the paper. The paper's
interpretation rule is fixed in advance: an outcome is called reliably
measured on a tour if its random-split median is at least 0.70 and at least
95% of splits are at or above 0.70.

B. **Entropy test.** Pearson correlation of conditional normalized entropy
(the paper's predictor, unchanged) with R1 (primary) and R2, R3 (secondary),
by tour. Direction: the narrative predicts that higher entropy goes with
better pressure performance, so the directional prediction is a positive
correlation, but all tests are two-sided. Family of 6 tests (3 outcomes by
2 tours), Bonferroni threshold 0.05 / 6 = 0.0083. Equivalence: the same TOST
95% bound on |r| and the same reliability correction as Section 5.2 of the
paper, using each outcome's own random-split median reliability. Outcomes
that fail A are reported with their (likely vacuous) corrected bound, not
dropped.

C. **Where clutch lives.** Report the share of points decided in each phase
(serve, return, rally) in the top and bottom leverage quartiles, so a reader
can see which shots carry the high-leverage points.

## What would change the paper's claims

- If R1 to R3 are reliable (median at least 0.70, 95% of splits at or above
  0.70) the paper's headline must be narrowed: the reliability problem is
  specific to serve and return roles, not to leverage-weighted clutch.
- If they are not, the claim is extended: it holds across the whole rally.
- Any entropy correlation surviving the 0.0083 threshold is reported as such,
  with the caveat that it is one of a larger set of tests in the project.
- No outcome, threshold or test is added after seeing results. Anything not
  listed here is reported as exploratory.
