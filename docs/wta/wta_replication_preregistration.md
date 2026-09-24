# WTA Replication: Pre-Registration

Written before fetching or looking at any `charting-w-` (WTA) data, following
the same discipline as `step3_variable_preregistration.md`.

## What this is
An independent replication of the exact pre-registered ATP analysis
(`conditional_normalized_entropy` predicting `serve_clutch_p65` /
`return_clutch_p65`), run on the WTA using the identical pipeline
(`src/core/parsing.py`, the entropy pipeline, the leverage engine in
`src/core/formulas.py`), with the identical
player-eligibility threshold (≥40 charted matches), the identical
`MIN_OBS=30` sufficiency floor, and the identical primary predictor/outcome
pairing. No new variables, no new methodology. The only thing that changes
is the population.

## Hypothesis going in
We don't have a strong prior that this should replicate or fail to
replicate. The ATP null was well-powered and robust, which is some
evidence of a genuine absence of relationship rather than
population-specific noise, but tennis analytics literature has documented
real ATP/WTA differences in other contexts (e.g. rally length, serve
dominance, physicality of play), so a real population difference is a live
possibility, not something to dismiss going in. We commit to reporting
whichever outcome occurs (null replicates, null doesn't replicate, or same
direction but different significance) without reframing the paper's
central claim after the fact.

## What counts as a genuine test vs. what would be a violation
- Legitimate: running the identical pipeline on WTA data and reporting
  whatever comes out, including if the WTA eligibility threshold needs
  documented adjustment for data-volume reasons (paralleling Step 1's own
  sparsity checks, not weakening the bar to force a result).
- Not legitimate: adjusting MIN_OBS, the entropy category scheme, the
  leverage p-value, or the clutch-score construction specifically because
  the WTA result doesn't match the ATP result. Any adjustment made must be
  justified independently of the outcome (e.g. WTA has fewer charted
  matches per player on average, which may require revisiting the ≥40-match
  threshold on data-volume grounds alone) and documented before rerunning.

## Reporting commitment
Both outcomes (replication or non-replication) will be reported in the
paper as a real finding, not selectively included. If the WTA result
differs from the ATP result, that difference itself becomes something the
paper discusses (a genuine tour-level distinction), not something to
suppress in favor of the cleaner ATP-only story.
