# Pre-registration: a continuous clutch estimator and a chronological split

Written 2026-11-17, before `src/robustness/slope_chronological.py` was run. Self-registered, and
written after all earlier results were known (see `preregistration_timeline.md`). No result of
either analysis below had been seen when this was written; the code was only syntax-checked.

## Why

1. **Estimator.** The paper's clutch score compares the top and bottom leverage quartiles and
   discards the middle half of each player's points. A reviewer can fairly ask whether the
   unreliability is a property of clutch or of that wasteful estimator. A per-player slope of
   point-win on leverage uses every point.
2. **Stability over time.** The split-half tests interleave matches, so they test stability
   across matches from the same period. The practical question (does early clutch predict later
   clutch) is harder: a chronological split also absorbs real drift in skill, form and opposition.

## Analysis 1: continuous leverage-slope estimator

Outcomes (same points and players as the paper): S serve points, Rt return points, R1
rally-decided points. For each player and each half, the ordinary least squares slope of
point-win (0/1, player's view) on leverage (p = 0.65 leverage, as in the paper), multiplied by
the player's full-sample leverage standard deviation for that role (fixed across halves and
splits, so it uses no outcome information) so the score reads as "change in win probability for
a one-SD higher-leverage point". A half needs at least 120 points (the paper's 4 x 30) and
leverage that varies. Reported:

- original-split reliability (Spearman-Brown), and the median, 95% range and share at or above
  0.70 over 1,000 random balanced splits (seed 20261117), for the slope and, side by side, for
  the quartile score from the same code;
- Pearson correlation between the full-sample slope score and the full-sample quartile score;
- true spread and implied reliability by the match-clustered two-stage estimator (sandwich SE
  from per-match score contributions; tau-squared is the variance of scores minus the mean
  squared SE, floored at zero; 95% interval from 2,000 player bootstrap resamples);
- the raw slope (per unit leverage, no SD scaling) as a secondary check on the original split
  and the random splits.

Decision rule: the paper's own criterion. The slope is "reliably measured" only if the
random-split median is at least 0.70 and at least 95% of splits are. If it is, the paper must say
the conclusion depends on the estimator. Otherwise it reports that the finding is not specific to
the quartile scheme.

Validation (script aborts otherwise): the quartile original-split reliabilities of S, Rt and R1
from this script's code match `allshots_reliability.csv` to within 0.001.

## Analysis 2: chronological split

For each player, order the player's charted matches by date (ties by match id); the earlier half
of the matches (rounded up) is A and the later half B. Quartile thresholds are recomputed inside
each half, as in the interleaved split. Reported for the quartile score (S, Rt, R1, R2, R3) and
the slope score (S, Rt, R1):

- the early-late correlation r (the stability coefficient) and its Spearman-Brown step-up, with
  95% player-bootstrap intervals (2,000 resamples);
- beside the interleaved original-split reliability and random-split median for the same outcome.

No decision rule is added beyond the criterion above. The gap between interleaved and
chronological reliability is reported as a lower bound on drift plus a loss of the shared
period, not as an estimate of drift.

## Not done

No logistic per-player slope, no opponent or surface adjustment, no estimator beyond those above
is tested, and no threshold is changed after seeing results.
