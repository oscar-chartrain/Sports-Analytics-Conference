# Step 2 → Step 3 Variable Pre-Registration

Written before Step 3 (leverage-weighted clutch score) or any regression is
built, so the choice of predictors isn't retroactively justified by seeing
which ones correlate with the outcome. This is a decision document, not a
code artifact. Its only job is to commit, in writing, to which of Step 2's
variables are the paper's primary hypothesis test vs. secondary/exploratory,
before that choice could be influenced by Step 3/4 results.

## Primary predictor (the paper's central hypothesis test)

`conditional_normalized_entropy` (from `step2_full_pool_features.csv`) is
the Shannon entropy of a player's shot choice conditioned on the preceding
shot in the rally, normalized to [0,1]. This is the "Robot vs Magician"
variable: lower means more predictable/consistent shot selection given the
situation, higher means more improvisational. Sufficient for 100% of the
91-player pool.

Justification for primary status: it's the only style variable that has
real spread across the pool (0.705-0.861, not bunched at a ceiling), passed
a face-validity check against independent knowledge of player styles
(grinders low, unorthodox hitters high), and is exactly what the paper's
title and research question describe. The other variables below are real
findings, but they're about serve tactics, net tactics, and return tactics
under pressure, not general shot-selection consistency.

`info_gain_relative` is a companion to the above: how much of a player's
shot-selection uncertainty is explained by the preceding shot, i.e. how
situation-dependent their game is at all. Kept as a secondary primary
variable alongside conditional entropy, since it captures a conceptually
different question ("how predictable" vs. "how context-driven") that the
paper may want to report together.

## Explicitly not primary (established as unusable, keep for the paper's methods narrative)

`pooled_normalized_entropy` (marginal, unconditional entropy): the sanity
check showed this sits in a narrow band near the ceiling for both Sinner
and Alcaraz (and, at full-pool scale, likely for most players, though this
hasn't been separately confirmed pool-wide) and mostly reflects court
geometry rather than style. Worth reporting in the paper as a "what we
tried first and why it didn't work" methodological narrative, since it's a
legitimate part of the story, not a result to hide, but it must not be
substituted for conditional entropy in the regression.

## Secondary / exploratory predictors (control variables or follow-on findings, not the headline test)

These extensions were built because the sanity check on Sinner/Alcaraz
suggested real signal, which is itself a reason for caution: deciding their
role now, rather than after running them against the full pool's clutch
scores, is the actual point of this document.

- `net_play_escalation_delta`: normal-vs-high-pressure change in net-play
  rate. Strong, consistent signal in the sanity check (Alcaraz roughly 2x
  Sinner's net rate at every pressure level). Proposed role: a control
  variable (net-aggression style may independently predict clutch outcomes
  for reasons unrelated to shot-selection consistency) rather than a
  second primary predictor, to keep the paper's central claim about
  entropy clean.
- `wide_serve_escalation_delta`: didn't differentiate Sinner/Alcaraz in
  direction (both escalate toward the wide serve under pressure). Proposed
  role: exploratory only, or a robustness check, not a predictor the
  regression is built around.
- `return_depth_shift_delta`: real for Alcaraz in the sanity check but
  thin sample size at the top of the pressure ladder. Proposed role:
  exploratory; flag any full-pool result built on this as tentative given
  the known sample-size caveat.
- `dropshot_rate`: usable pool-wide (100% sufficient) but not yet
  validated against known player styles the way conditional entropy was.
  Proposed role: exploratory / secondary control.
- `dropshot_direction_entropy`: sufficient for only 9/91 players. Excluded
  from any pool-wide regression; may be reported as a single-subgroup
  finding (the 9 highest-volume players) if relevant, but never imputed or
  extrapolated to the rest of the pool.
- `entropy_escalation_delta` (added later, own pre-registration in
  `docs/atp/02_entropy_pipeline/entropy_pressure_escalation.md`): whether
  a player's conditional entropy itself shifts under pressure, closing an
  inconsistency where every other Step 2 extension had an escalation
  delta and entropy didn't. Tested as its own exploratory predictor
  against clutch, not a replacement for the primary (level) predictor;
  found null on both tours, both roles, surviving neither nominal
  significance nor the Bonferroni-corrected threshold across its own
  4-comparison family.

## What this document commits to

1. Step 3/4 will report `conditional_normalized_entropy` (and
   `info_gain_relative`) as the primary predictor(s) of the clutch score,
   decided before seeing that regression's results.
2. `pooled_normalized_entropy` will not be substituted in if the primary
   variable underperforms; its non-result is part of the methods
   narrative, not a discarded attempt.
3. Any of the secondary/exploratory variables that do show a strong
   full-pool relationship to clutch performance will be reported as
   secondary/exploratory findings, not reframed as having been the main
   hypothesis all along.
4. `dropshot_direction_entropy` will not be used in the main pool-wide
   regression under any circumstances, given its 9/91 coverage.

This document should be treated as a commitment device: if Step 3/4
results create pressure to reclassify a variable's role, that pressure is
exactly what pre-registration is meant to resist. The right move is to
note the tension in the paper's limitations section, not edit this file.
