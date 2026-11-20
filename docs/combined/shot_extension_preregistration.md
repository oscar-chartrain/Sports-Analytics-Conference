# Shot-level extension and label accuracy: plan

Written 2026-11-20, before `src/robustness/shot_extension.py` or `src/robustness/label_accuracy.py` existed or was run. Self-registered, like the earlier plans (see `preregistration_timeline.md`). Descriptive: nothing here is a hypothesis test, and the 0.70 criterion and the 95%-of-splits rule of the paper are unchanged.

## Why

The paper measures errors by shot type but winners only over all shots, and it treats rally points as one block. This plan (a) adds winners by shot type and rally points by rally length, and (b) translates every reliability in the paper into how often a clutch label is right (the "label accuracy" of Section 6).

## A. New outcomes (five, all defined here)

Same data, pools, leverage (p = 0.65 quartiles), hitter attribution, 1,000 random balanced splits and Spearman-Brown routine as `all_shots_analyses.py`. Signed so that higher means better under pressure. Thresholds come from all the player's points, as for R1 to R9.

| Id | Outcome | Definition | Floor per bucket |
|---|---|---|---|
| R10 | Winner clutch, forehand | winners whose last shot is a forehand, per forehand shot hit: rate in top minus bottom quartile | 100 forehand shots |
| R11 | Winner clutch, backhand | same, backhand | 100 backhand shots |
| R12 | Winner clutch, slice | same, slice (codes r, s) | 100 slice shots |
| R13 | Point clutch, short rallies | point-win rate, top minus bottom, on rally-decided points of 2 to 4 shots in total (return included) | 30 points |
| R14 | Point clutch, long rallies | same, rally-decided points of 5 or more shots | 30 points |

Not included, by decision: the net-game family is not split (volleys, overheads, drop shots stay as in R7). The short/long cut (4 versus 5 shots) was fixed here from convention, not from outcome values; no outcome value of R10 to R14 has been computed or looked at.

Reported per outcome and tour: original-split reliability, random-split median with 2.5th to 97.5th percentile, share of splits at or above 0.70, and the median number of events per player in the two buckets (as in Table S19). All five outcomes are reported whatever they show. Five new outcomes are five more comparisons, so a single high value is a lead, not a finding, and the verdict "reliably measured" still needs median at least 0.70 and at least 95% of splits.

## Validation (the script aborts if any fails, before writing anything)

1. Hitter parity floor 0.85 (as before).
2. Original-split reliabilities of serve and return clutch equal the paper's documented values within 0.001.
3. The committed forehand-error outcome (R4) is reproduced from the new arrays: original-split reliability within 0.001 of `allshots_reliability.csv`.
4. Within every player, winners attributed to forehand, backhand and slice shots never exceed all winners (sanity of the family attribution).

## B. Label accuracy

Model: a player's observed score X is a true score T plus independent noise, both standardized, with corr(X, T) = sqrt(rho) and corr between two equally long records = rho, where rho is the full-length (Spearman-Brown) reliability. T is taken as normal. For the "top-quartile label" (X above its 75th percentile), exact bivariate-normal probabilities:

- precision: P(T above its 75th percentile | X above its 75th percentile);
- gross error: P(T below its median | X above its 75th percentile);
- repeat: P(X' above its 75th percentile | X above its 75th percentile), X' from an independent record of the same length.

Chance levels: 25%, 50% and 25%. Computed at each outcome's random-split median rho and at its 2.5th and 97.5th percentile (negative rho set to 0, rho capped at 0.99). Outcomes: every outcome of Tables S1 and S7 plus R10 to R14, both tours. The result is a derived projection resting on the normal and independent-noise assumptions and on estimated reliabilities; it is not a test and carries the interval from the reliability estimate only.

Seen before writing this plan: illustrative label-accuracy figures for rho of 0.24, 0.41, 0.53, 0.60, 0.70 and 0.90 from a scratch simulation (the model above), disclosed here; they do not depend on any new outcome.

## Outputs

`results/applications/shot_extension_reliability.csv`, `results/applications/label_accuracy.csv`, scrubbed run logs, a supplementary table for each, and at most one sentence and one column in the main text.
