# Pre-registration: does clutch predict winning when it matters? (external criterion)

Written 2026-11-19, before `src/robustness/decider_validity.py` was run. Self-registered, written
after all earlier results were known (see `preregistration_timeline.md`). No relationship between any
clutch score and any match result had been looked at when this was written. Before writing it, only
counts were inspected (pool names found in the tour results, deciding sets per player, charted
matches located in the tour results; see "Feasibility counts").

## Question

Table S17 shows that the stable part of some clutch scores is more than ability, but that is
agreement and persistence, not winning. The external question: if a clutch score measures something
real, players with higher scores should win more of the matches and sets that are decided under
pressure than their general strength predicts. We test that on results that are not in the charted
sample, so the score and the criterion share no points and no matches.

## Data

- Predictors: the paper's full-sample scores from the charted matches for the pools of 91 ATP and 55 WTA
  players: serve clutch (S), return clutch (Rt), rally-point clutch (R1), unforced-error clutch (R2),
  winner clutch (R3), forehand-error clutch (R4), backhand-error clutch (R5), signed so that higher means
  better under pressure, plus a composite (below). Nothing is recomputed: the same scores as Table S17.
- Criterion data: tour-level match results (winner, loser, set scores, best-of, tournament date) for the
  same players, ATP and WTA, 1968 to 2026-05-25, from Jeff Sackmann's `tennis_atp` and `tennis_wta`
  (CC BY-NC-SA 4.0). The upstream repositories are no longer reachable at `github.com/JeffSackmann`,
  so the files are fetched from an archival mirror
  (`github.com/Aneeshers/tennis-sackmann-archive`, commit `83733587353df8a41f2fd4f516147d5aa83f5a8d`,
  made 2026-06-25 from upstream commits of June 2026), pinned by commit and checked by SHA-256 in
  `DATA_MANIFEST.csv`. The mirror's integrity is tested against the charted data (V2).
- Excluded from the criterion: every tour match that is also charted (same two players, tournament start
  date to 21 days later, i.e. any tour match between the pair within that window of a charted match), so
  the criterion shares no match with the predictor.

## Criteria

**C1 (primary): deciding-set matches.** Complete tour matches (score parses; no retirement, walkover or
default) whose set count equals the best-of (3 or 5), so the last set decides. y = 1 if the pool
player won the match. Players need at least 30 such matches (floor).

**C2 (secondary): tiebreaks.** Every set decided by a tiebreak (score of the form 7-6(x) or 6-7(x),
including deciding sets played to a tiebreak) in matches with a parseable score. y = 1 if the pool player
won the set.

## Strength control (so that a strong player's wins are not mistaken for clutch)

Pre-match Elo ratings for every player in the tour file, by tour, computed chronologically (tournament
date, then match number) from SET results only, using sets that are neither the deciding set nor a
tiebreak set (so no criterion result enters a rating): initial 1500, scale 400, K = 20, update after
each such set (ratings change set by set within a match). The ratings used to predict a match are those from before it.
d = (R_player - R_opponent) * ln(10) / 400 (log-odds per set). The expected win probability is
sigma(b * d), with b fitted by maximum likelihood across every league-wide match of that type (no
intercept, so the model is antisymmetric: the two players' probabilities sum to 1), separately for best-of-3 and
best-of-5 deciders and for tiebreaks. For each pool player i with n_i matches of a type:
excess_i = mean over those matches of (y - expected). Sensitivity: K = 10 and K = 30.

## Tests

Player-level weighted least squares (weights n_i; heteroskedasticity-robust HC3 standard errors):
excess_i = a + b * z_i + c * abar_i, where z_i is the standardized predictor over the pool and abar_i is the
player's mean d over the matches in the criterion (average strength advantage). b is the change in
win probability, in percentage points, per standard deviation of the observed score. Also the Spearman
correlation of z_i with excess_i (unweighted) and a 95% player-bootstrap interval for b (2,000
resamples).

Composite: the mean of a player's available z-scores over the seven indicators (at least five),
re-standardized. The paper's indicators do not converge (Table S17), so the composite is a convenience,
not a latent trait.

**Primary tests (4):** C1 with serve clutch (S) and with the composite, on ATP and WTA. Threshold 0.05 / 4 = 0.0125,
two-sided. **Secondary tests (28):** C1 with the six other indicators (6 x 2 tours = 12) and C2 with all eight predictors
(8 x 2 tours = 16). Threshold 0.05 / 28 = 0.0018.

## Criterion reliability (diagnostic, not a test)

For C1 and C2, the split-half reliability of excess_i: 1,000 random splits of each player's matches into
halves (Spearman-Brown), median and 2.5th to 97.5th percentile. The ceiling for any observed correlation is
sqrt(reliability of the score x reliability of the criterion). The score reliabilities are the chronological
ones in Table S17.

## What a real effect would look like (benchmark and power)

1. First-order sensitivity: with an asymmetric set model (both players' serve and return point
probabilities, tiebreak at 6-6, starting server averaged), the change in set-win probability, in percentage
points, per one percentage point shift in the focal player's point-win probability on every point
(serve and return), at 65% serve-point win probability for both (k).
2. Benchmark for serve clutch: one true SD of serve clutch is 2.15 (ATP) and 1.88 (WTA) points (Table 2).
Applied to the deciding set, where most points are high leverage, the implied change in win probability per true SD
is between k * 0.5 * SD (the top-minus-bottom difference split evenly around the player's mean) and k * SD (all
on the top quartile). Per SD of the observed score it is multiplied by the square root of the score's
reliability.
3. Pipeline positive control: draw y ~ Bernoulli(clip(expected + theta * t_i)) for each real criterion match,
with t_i the true clutch (SD 1) and the observed score z = sqrt(rel) * t_i + sqrt(1 - rel) * e, rel the
chronological reliability; theta (pp of win probability per true SD) in {0, 1, 2, 4, 8}; 1,000 simulated
datasets per cell on each tour's real n_i and expected values. Reports the estimator's mean slope against
theta * sqrt(rel) and the share of datasets significant at 0.0125 (power), and the smallest grid theta with at
least 80% power (the minimum detectable true effect).

## Decision rules, fixed in advance

- A primary test below 0.0125 with a positive b: the paper says the score predicts winning decisive
  sets, with b and its interval, and says how it compares with the benchmark.
- A primary test below 0.0125 with a negative b: the paper reports it as a reversed association and does
  not call it clutch.
- No primary test below 0.0125: the paper reports that the score does not predict decisive-set wins, with
  the interval for b, the minimum detectable effect, and the benchmark, and says whether the interval excludes
  the lower benchmark (k * 0.5 * SD * sqrt(rel)).
- If the criterion's reliability (median) is below 0.10 on a tour, the paper says no score could be validated
  against it on that tour and does not interpret that tour's tests.
- Secondary tests are described, with a count below 0.0018 and their signs; none can change the primary reading.
- No predictor, criterion, rating setting, floor or threshold is changed after seeing results.

## Validation (the script aborts if any fails; `--validate-only` runs these without the predictors)

V1. Every pool player's name is found in the tour file after normalization (accents removed, hyphens as
spaces); each tour has at least 90% of pool players with at least 30 criterion matches.
V2. Mirror integrity and matching: among charted matches located uniquely in the tour file whose tour score is
complete, those whose chart reaches match point (the state before the chart's last point, sets and games, equals the state
before the last point implied by the tour score; incomplete charts that stop mid-match are not used) must be at least 85%,
and in them the winner of the last charted point must be the tour-file winner in at least 99%. The located share is reported.
V3. Score parsing: in complete matches the winner won more sets than the loser, set counts are consistent
with the best-of, and set scores are valid tennis scores (6-0 to 6-4, 7-5, 7-6, or longer advantage sets); anomalies
counted and reported.
V4. Elo: a hand-calculated two-player example is reproduced; no deciding set or tiebreak set updates a
rating (counter checked); the sum of rating changes is zero.
V5. Calibration: b is positive, and across deciles of the expected probability the observed win rate is within
2 percentage points of the expected one league-wide.
V6. League-wide the expected probabilities of the two players sum to 1 in every match, so the league-wide mean
excess is zero.
V7. Simulation: at theta = 0 the mean slope is within 3 standard errors of zero and the rejection rate at 0.05 is
between 0.02 and 0.08; at theta > 0 the mean slope is within 15% of theta * sqrt(rel) (checked on S).

## Feasibility counts (seen before writing this plan)

ATP: 199,389 tour matches 1968 to 2026-05-25; all 91 pool names found; median 566 tour matches and 180
deciding-set matches per pool player (one player below 30); 7,040 of 7,565 charted matches (93.1%) have a same-year
same-pair tour match. WTA: 162,182 tour matches; all 55 names found; median 438 matches and 141 deciding-set matches
(one player below 30); 3,727 of 4,073 charted matches (91.5%) located. About 30% of complete matches reach the deciding
set. No result about clutch was seen.

## Not done

No surface-specific or time-varying form beyond Elo; no adjustment for age, fatigue or the round; no
Challenger or ITF matches; no match-level (rather than player-level) model; no tiebreak benchmark; pool players who
meet each other appear in both players' criteria (a sensitivity analysis drops those matches).

## Amendments and disclosure recorded 2026-11-19 (before the full run)

A validation-only run (no clutch scores involved) printed: tour counts; the located share of charted matches (WTA 87.7%, ATP 88.3%
with the 21-day window); the calibration slopes (WTA best-of-3 decider 0.587, tiebreak 0.304); the criterion's spread (WTA: SD of
player excess 6.9 pp against 4.7 pp of binomial noise, i.e. about 5.0 pp of extra between-player spread); and simulated power (WTA, serve-like
predictor with chronological reliability 0.40: 3.0% rejection at theta = 0, power at 0.0125 of 4%, 13%, 34%, 77% at theta = 1, 2, 4, 8 pp per
true SD). Two changes were made before the full run, neither after seeing any relationship between a clutch score and a result:
1. V2 first required the charted last-point winner to equal the tour winner in at least 95% of located complete matches. It gave 95.7% (WTA)
and 94.9% (ATP); the disagreements were charts that stop mid-match (for example a last point at 0-0 in the fourth game), so the rule
tested chart completeness, not the mirror. V2 was replaced by the state-consistency rule above.
2. The power simulation first used binomial noise only; it now adds the criterion's extra between-player spread (estimated from the real excess,
without predictors) so that power is not overstated.
No predictor, criterion, rating setting, floor, threshold or decision rule was changed.

The ATP validation run also printed: calibration slopes (best-of-3 decider 0.623, best-of-5 decider 0.539, tiebreak 0.333); SD of player
excess 4.9 pp against 4.4 pp of binomial noise (2.1 pp of extra spread); and simulated power (serve-like predictor, reliability 0.44) of 11%,
48%, 93%, 100% at theta = 1, 2, 4, 8 pp per true SD (2.5% at theta = 0, rejection 6.0% at 0.05). The benchmark sensitivity is k = 6.56 percentage
points of set-win probability per percentage point of point-win probability. After the amended V2 both tours pass: the winner of the last charted
point is the tour winner in 99.75% (WTA, 3,216 chart-complete matches) and 99.86% (ATP, 5,832).
