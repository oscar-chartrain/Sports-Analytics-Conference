# Consistency Fixes: Pre-Registration

**Written 2026-11-11, before any script for these two checks existed.** These
are not new questions. They close two places where the paper's own tables used
a single-split reliability after the random-split extension
(`applications_extensions_preregistration.md`) showed that a single split can
sit far from the center (WTA return clutch: 0.055 on the original split, 0.27
at the random-split median). Decision rules are fixed now; anything changed
afterwards goes in the Deviations log with date and reason.

## Fix 1: Break-point reliability over random splits

### Why
Table 5 of the paper (break-point conversion and save reliability) reports the
original split only, while Table 1 reports both. Whether the break-point
conclusions hold across splits was not tested.

### Procedure
1. Same 1,000 random balanced splits as the extension: permute the globally
   date-sorted relevant match list, alternate positions into halves A and B.
   NumPy seed 20261111, same draw logic.
2. Per player, per half, per role: break-point rate, baseline rate and
   differential, with the break-point and baseline definitions fixed in
   `applications_extensions_preregistration.md`. A player enters a split's
   reliability only if they have at least 30 break points in that role in
   both halves (the number excluded is reported).
3. Reliability = Spearman-Brown corrected split-half correlation across
   players. Report, per tour, role and statistic (raw rate, differential):
   the original-split value, the median over random splits, the 2.5th and
   97.5th percentiles, and the share of splits with reliability below 0.70.

### Validation (must pass first)
Pushing the original alternating assignment through the new code must reproduce
the reported Table 5 original-split values within 0.001 (ATP save 0.7543 raw /
0.3998 differential; ATP conversion 0.6174 / 0.0535; WTA save 0.4391 / 0.1181;
WTA conversion 0.0634 / -0.2895). If it does not, stop and investigate.

### Decision rules, committed in advance
- The interpretation table in `applications_extensions_preregistration.md`
  (Analysis B) is applied to the **random-split median**. The original-split
  value is reported beside it.
- If the original split and the median land in different rows of that table,
  the paper says the classification is split-dependent and reports both.
- A statement "below 0.70" is called robust if at least 95% of random splits
  agree, the same rule as before.

## Fix 2: Reliability-corrected equivalence bounds at random-split reliabilities

### Why
The paper's corrected bounds (Table A2, Figure 2) use original-split
reliabilities. For WTA return the paper currently quotes a back-of-envelope
recalculation (about 0.82) at the random-split median, flagged as not formally
rerun. This replaces it with a real computation.

### Procedure
1. Observed-scale TOST bounds `B_obs` are recomputed with the unmodified
   `tightest_tost_bound()` from `disattenuated_equivalence_bounds.py` on the
   real per-player data, and must match the documented values (ATP 0.213 serve,
   0.189 return) within 0.001 before any new number is trusted.
2. True-score bound `B_true = B_obs / sqrt(rel_entropy * rel_clutch)`, with
   `rel_entropy` as documented (ATP 0.925, WTA 0.897; entropy is not re-split)
   and `rel_clutch` taken three ways: the original split (reproducing the
   existing table), the random-split median, and the 2.5th and 97.5th
   percentiles of the random-split reliability (giving a range). Medians and
   percentiles come from `results/applications/ext_a_random_splits.csv`.
3. If a reliability used is <= 0, or the resulting bound exceeds 1, the bound
   is reported as vacuous (not capped or clipped).

### Commitments
- All four tour-role combinations at all three reliability versions are
  reported, whatever they show.
- The sampling uncertainty of the reliabilities is reflected only through the
  2.5th and 97.5th percentile versions, not propagated formally; this is
  stated in the paper.
- The paper's WTA return sentence is replaced by the computed value, and the
  Limitations wording adjusted to match.

## What would change the paper

| Outcome | Change |
|---|---|
| Break-point classification differs between original split and median | Table 5 reports both; the text says split-dependent |
| WTA return corrected bound at the median is below 1 | Text states the computed value, replacing the back-of-envelope figure |
| Any corrected bound still exceeds 1 at the 2.5th percentile reliability | Reported as vacuous at that end of the range |

## Deviations log

Logged 2026-11-11, after the first run of `src/robustness/consistency_fixes.py`.
No decision rule was changed after seeing results.

1. **Validation passed.** The original assignment reproduced all eight Table 5
   values to four decimals, and the ATP observed bounds matched the documented
   0.213 and 0.189.
2. **Fix 1 outcomes.**
   - ATP BP conversion, raw rate: the original split (0.617) lies **outside**
     the random-split 95% range [0.631, 0.807]. Under the pre-registered rule
     the random-split median (0.729) becomes the headline; the original is
     disclosed as an unusual draw.
   - Applying the interpretation table to the medians: ATP serve (raw 0.715,
     differential 0.344) and ATP return (raw 0.729, differential 0.227) both
     fall in row 1 (reliable as skill, not as clutch). On the original split
     ATP return had been in row 3 (raw 0.617 below 0.70). The classification is
     therefore split-dependent for ATP return, as the rule requires saying.
   - ATP BP save raw: 38.8% of splits fall below 0.70 and ATP BP conversion
     raw 27.8%, so neither "below 0.70" nor "at or above 0.70" meets the 95%
     robustness rule; the paper reports them as borderline.
   - WTA: all four statistics are below 0.70 in 100% of splits (row 3).
3. **Fix 2 outcomes.** The back-of-envelope WTA return figure in the paper
   (about 0.82) is confirmed at 0.823. Bounds at the 2.5th-percentile
   reliability are vacuous for ATP return and WTA return (reliability at or
   below zero) and for WTA serve (1.475); reported as vacuous, not clipped.
4. **Original-split column of the corrected-bounds table.** This script uses
   the exact original-split reliabilities (e.g. 0.0547); the existing Table A2
   and Figure 2 use the documented rounded values (0.055), which changes bounds
   by at most 0.006 (WTA return 1.819 against the documented 1.813). The paper
   keeps the documented values in that column so that it matches Figure 2, and
   uses this script's values for the random-split columns.
