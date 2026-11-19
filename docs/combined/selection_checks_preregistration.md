# Pre-registration: selection checks (player-volume cutoff, tournament level)

Written 2026-11-18, before `src/robustness/selection_checks.py` was run. Self-registered, and
written after all earlier results were known (see `preregistration_timeline.md`). No result of
these checks had been seen when this was written; the code is first run in a validation-only mode.

## Why

The paper's sample is selected twice. (1) Players enter if they have at least 40 charted matches,
a cutoff chosen for the entropy analysis, not for reliability. A cutoff changes the number of
matches per player (more matches raise reliability) and the spread of players (range restriction
lowers it). (2) The Match Charting Project is volunteer-charted and over-represents Grand Slams
and Masters events, so a player's charted matches are not a random draw from their career, and
matches from one tournament share conditions. The 50:50 random match split in the paper puts
matches from the same tournament into both halves. Section 7 mentions selection but no check
tested whether the reliability conclusion depends on it.

## Checks (ATP and WTA; outcomes S serve clutch, Rt return clutch, R1 rally-point clutch;
the paper's definitions, leverage p = 0.65, quartile rule, 30-point floor)

**C1. Player-volume cutoff.** Pools of players with at least 20, 30, 40 (the paper's), 60 and 80
charted matches (appearances in the match file, as in the paper's pool). For each pool, the
universe is every match involving a pool player, split at random into balanced halves (1,000
splits, seed 20261120), Spearman-Brown reliability per split. Reported per pool: players, median
charted matches, median, 2.5th and 97.5th percentile and share at or above 0.70 of the split
reliabilities, and the between-player standard deviation of the full-sample score. The pools below
40 need leverage for matches outside the paper's table; it is computed with the paper's own
function (p = 0.65, same match-format lookup).

**C2. Tournament-blocked splits.** Paper pool. A block is a tournament edition (tournament name
and year). Whole blocks are assigned to halves, shuffled and allocated greedily to the half with
fewer matches (1,000 splits). Same reliability summary, beside the matched-split result from C1.

**C3. Grand Slam against other matches.** Paper pool. (a) Reliability within Grand Slam matches
only and within all other matches only (1,000 random splits inside the stratum; quartile
thresholds from the player's points in the half). (b) For each player with a defined full-sample
score in both strata (thresholds from the stratum's points), the mean Slam minus non-Slam score
with a player-level standard error, the correlation of the two scores across players, and that
correlation divided by sqrt(rel_Slam x rel_other), the strata's median split-half reliabilities
(a disattenuated value, shown only when both reliabilities are positive; descriptive).

**C4. Charting volume and Slam share against the score.** Paper pool. Spearman correlation of
each player's number of charted matches, and share of charted matches that are Grand Slams, with
the full-sample S, Rt and R1 scores. Family of 12 tests (2 tours x 2 predictors x 3 outcomes);
a correlation is called evidence of selection on the score only below 0.05 / 12 = 0.0042.

## Decision rules, fixed in advance

- "Reliably measured" is the paper's criterion: median at least 0.70 and at least 95% of splits at
  or above 0.70.
- C1: if any pool meets the criterion for any outcome, the paper must say the conclusion depends
  on the pool and name it. If reliability rises with the cutoff but never meets it, the paper
  reports the trend. If a pool's median differs from the paper pool's by 0.10 or more in either
  direction, the paper says so.
- C2: if the blocked median is 0.10 or more below the matched-split median, shared tournament
  conditions inflated the headline reliability (the paper says so; this direction supports its
  conclusion more strongly). If it is within 0.10, the paper reports that tournament clustering
  does not matter.
- C3: descriptive; no stratum counts as reliable unless it meets the criterion. A mean Slam
  difference is reported in points; a disattenuated cross-stratum correlation near 1 would be
  reported as consistent with one stable trait buried in noise, one well below 1 as evidence the
  score is context-dependent.
- C4: any correlation below 0.0042 is reported as selection on the score, with the sign.
No estimator, threshold, pool or seed is changed after seeing results.

## Validation (the script aborts if any fails)

V1. The 40-match pool equals the paper's player list, and the extended point table reproduces the
paper table's per-player arrays (leverage, outcome, rally flag), matched by match id, exactly.
V2. Leverage recomputed with the new code path on 300 random rows of the paper table equals the
cached leverage to 1e-12.
V3. At cutoff 40 the new random-split medians are within 0.02 of the committed medians in
`allshots_reliability.csv` (different splits; Monte Carlo error only).
V4. Blocked splits keep every block on one side and are balanced to within the largest block.
V5. The Grand Slam flag matches the confounder script's definition, and every match is in exactly
one stratum.

## Not done

No adjustment for who charted a match (the file records the charter but it is mostly one
volunteer); no re-estimation of the entropy relationships on the larger pools; no tournament-level
fixed-effect model; no weighting by inverse selection probability (the selection mechanism is
unobserved). The check can show whether the conclusion moves under the selections I can observe,
not whether charting selection on unobserved features matters.

## Disclosure recorded 2026-11-18 (before the full run)

A validation-only run on WTA (100 splits at cutoff 40, 20 blocked splits) printed its cutoff-40
and blocked results as well as the validation lines; they were seen (cutoff-40 medians 0.42 serve,
0.27 return, 0.26 rally-point; blocked splits within 0.02 of them). All five validation checks
passed. No pool, estimator, threshold, seed or decision rule was changed after seeing them.
