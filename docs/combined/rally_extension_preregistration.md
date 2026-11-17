# Pre-registration: carrying the practice-side analyses to rally points

Written 2026-11-16, before `src/robustness/rally_extension.py` was run. Self-registered, and
written after all earlier results were known (see `preregistration_timeline.md`), including
the all-shot reliability results (`allshots_reliability.csv`), which this plan reads.

## Why

The all-shot analyses (Section 4.4, Table 2) extended the reliability test and the entropy
test to rally points and shot-level outcomes. The analyses in Section 6 and the robustness
checks in Section 4.3 and the Discussion were still serve and return only. A reader can fairly
ask whether the practice-side conclusions (data needed, true spread, rank uncertainty,
shrinkage, leverage-variant sensitivity) also hold for the rally outcomes. This plan repeats
each of them for the three rally outcomes where the quantity is defined.

## Outcomes

R1 rally-phase point clutch (point-win rate difference, top minus bottom leverage quartile,
on rally-decided points), R2 unforced-error clutch over all shots, R3 winner clutch over all
shots; definitions and minimum counts exactly as in `all_shots_analyses.py`. S and Rt (the
paper's serve and return clutch) are carried through the same code as calibration.
Units: percentage points of point-win rate (R1, S, Rt) or of rate per shot (R2, R3).

## Analyses

1. **Data needed.** Spearman-Brown prophecy of the matches needed for reliability 0.70, from
   the random-split median and 95% range already in `allshots_reliability.csv`.
2. **True spread.** Per player top-minus-bottom difference with a match-clustered (sandwich)
   standard error; tau-squared = variance of the differences minus the mean squared standard
   error, floored at zero; 95% interval from 2,000 player-bootstrap resamples; implied
   reliability tau-squared / (tau-squared + mean squared SE).
3. **Match-win translation (R1 only).** One true SD times the summed leverage per match of
   rally-decided top-quartile points (high end) and bottom-quartile points (low end). R2 and
   R3 are per-shot rates, so no first-order translation to point or match probability is
   attempted.
4. **Rank uncertainty.** Match-level cluster bootstrap (B = 2,000), as in
   `cluster_bootstrap_ranks.py`, but with each player's quartile thresholds held at their
   full-sample values instead of re-estimated in each replicate. S and Rt are run through the
   same fixed-threshold code and compared with the re-estimated-threshold widths already
   reported; if they differ by more than 15% the paper says so.
5. **Shrinkage.** Empirical-Bayes shrinkage within each half independently (as in
   `shrinkage_reliability.py`, with the clustered SE as the noise term), original split.
   If any shrunk reliability reaches 0.70 it must be reported. *Added before the full run,
   after a 3-split test run (a test of the code, whose output was seen) showed two
   original-split shrunk values above 0.70 (ATP winner clutch, WTA error clutch):* the same
   shrinkage is also run over 1,000 random balanced splits, and a cell counts as rescued by
   shrinkage only if the random-split median is at least 0.70 and at least 95% of splits are,
   the paper's own criterion. (A first full run returned undefined shrunk reliabilities in
   splits where a half's estimated true variance was zero, which collapses the shrunk scores
   to a constant; the code was changed to score those splits as reliability 0 and the run
   repeated. No other change was made.)
6. **Leverage variants.** Original-split reliability and the median over 200 random balanced
   splits for p = 0.60, p = 0.70, tiered and empirical leverage. If any rally outcome
   reaches a median of 0.70 with at least 95% of splits at or above it under any variant,
   the paper must say the conclusion depends on the leverage variant.

## Validation (script aborts otherwise)

The original-split reliabilities of R1, R2, R3, S and Rt from this script's code must match
`allshots_reliability.csv` and the paper to within 0.001.

## Not done

Break-point conversion and save rates are defined by a score state, not by how a point ends,
and splitting them by phase leaves too few points per player; no rally version is attempted.
The pooled leverage ratio already uses every point, rally points included. A multilevel model
for R2 and R3 was not attempted (ratio outcomes); the clustered two-stage estimator in 2
plays that role. Nothing else is tested, and no estimator or threshold is added after seeing
results.
