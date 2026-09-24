# Entropy-Under-Pressure Escalation Delta: Pre-Registration and Results

## Pre-registration

Written before splitting a single transition by pressure situation or
computing a single escalation value.

### Why this variable

Every other style variable added as a Step 2 extension (serve zone,
net play, return depth) is measured as a normal-vs-high-pressure delta —
does a player's behavior change under pressure — not just a career-wide
level. `conditional_normalized_entropy`, the primary predictor, is the one
exception: it's a single number, never split by pressure situation. That's
an inconsistency with this project's own established pattern, not a
deliberate scope decision, and it means the primary hypothesis test has
never actually asked "does a player's shot-selection consistency change
under pressure, and does *that* change predict clutch performance,"
only "is a player's overall consistency level related to clutch
performance." Those are different, both plausible questions.

### Method

`step2_entropy_pipeline.get_player_shot_transitions()` gained an optional
`include_pressure=True` argument that classifies each transition's
underlying point via the same `parsing.get_pressure_flags()` /
`is_high_pressure()` logic already used for the serve-zone, net-play, and
return-depth escalation deltas, adding a `high_pressure` boolean column.
Default `False` preserves the function's original 4-column output
unchanged for every existing caller. No new parsing or hitter-attribution
logic is introduced; this reuses the exact same pressure classifier
already relied on elsewhere.

For each player, `conditional_normalized_entropy` is computed separately
on their normal-situation transitions and their high-pressure transitions
(same `compute_transition_entropy()` function, same MIN_OBS=30
per-context floor, applied independently to each subset). A player is
included only if *both* subsets clear that floor.

```
entropy_escalation_delta = conditional_normalized_entropy(high pressure)
                          - conditional_normalized_entropy(normal)
```

Positive = shot selection becomes *more* unpredictable under pressure;
negative = a player tightens up and becomes more predictable under
pressure.

### Commitment (fixed before running)

1. This is an exploratory/secondary predictor, per the same discipline
   `step3_variable_preregistration.md` already committed to for the other
   escalation-delta variables. It does not replace or compete with
   `conditional_normalized_entropy` as the primary predictor, regardless
   of what it finds.
2. Splitting transitions by pressure situation, on top of the existing
   per-context split, is expected to reduce the sufficient sample size
   meaningfully below the 91/55 primary pool, since high-pressure points
   are a minority of all points by construction. The actual sufficient n
   will be reported plainly, not treated as a problem to route around.
3. The correlation between `entropy_escalation_delta` and
   `{role}_clutch_p65` will be tested for both roles, both tours (4
   comparisons total), with a Bonferroni correction across those 4 applied
   and reported alongside the raw p-values, regardless of outcome.
4. The escalation delta itself, and its distribution across players
   (positive vs. negative, i.e. who loosens up vs. tightens up under
   pressure), will be reported as a standalone descriptive fact regardless
   of whether it correlates with anything.
5. This document will not be edited after seeing results.

## Results

Written after running `src/robustness/entropy_pressure_escalation.py`
exactly as specified above.

### Sample size: the pre-registered expectation was wrong, in the good direction

Commitment #2 above expected the additional pressure split to meaningfully
reduce the sufficient sample below the 91/55 primary pool. It didn't:
**91/91 ATP and 55/55 WTA players remain sufficient in both the normal and
high-pressure buckets**, at the same MIN_OBS=30 per-context floor used
everywhere else. This is consistent with the MIN_OBS sensitivity finding
in `power_and_robustness.md` (the floor was never binding even at 3x the
original threshold) — this pool's per-player data depth turns out to
comfortably support an even finer split than originally expected. Reported
here because the pre-registration committed to reporting the actual
number plainly, including when the original expectation was wrong.

### The escalation delta is small and roughly balanced

| Tour | Mean delta | Std | Median | Get less predictable under pressure | Get more predictable under pressure |
|---|---|---|---|---|---|
| ATP | +0.0003 | 0.0084 | -0.0002 | 45/91 | 46/91 |
| WTA | -0.0035 | 0.0080 | -0.0029 | 18/55 | 37/55 |

For reference, the primary predictor's *between-player* spread (the level,
not the change) is roughly 0.026 in standard deviation across the ATP
pool. The within-player pressure-driven change is smaller than that by a
factor of about 3, on both tours. In plain terms: most players' shot
selection consistency is fairly stable whether or not the moment is
high-pressure — for the typical player, entropy under pressure looks a
lot like entropy in general. ATP splits close to a coin flip on which
direction players move (45 vs. 46); WTA skews toward players tightening
up under pressure (37/55 vs. 18/55), a real, if modest, majority pattern
worth noting even though it doesn't end up correlating with clutch below.

### Correlation with clutch performance

| Tour | Role | n | r | p |
|---|---|---|---|---|
| ATP | Serve | 91 | +0.132 | 0.214 |
| ATP | Return | 91 | -0.121 | 0.252 |
| WTA | Serve | 55 | -0.195 | 0.154 |
| WTA | Return | 55 | -0.177 | 0.197 |

None of the four comparisons reach nominal significance, and none come
close to the Bonferroni-corrected threshold (alpha=0.0125 across these 4
comparisons; nothing survives). Sign is inconsistent across tour and role
(ATP serve and return point in opposite directions; WTA serve and return
both negative), which is itself evidence against reading anything into the
pattern rather than treating it as noise around zero.

### Honest verdict

Refining the hypothesis from "is a player's overall consistency level
related to clutch performance" to "does a player's consistency *change*
under pressure, and does that change relate to clutch performance" finds
the same answer: no. This adds a genuinely new angle rather than
re-testing the same one — it's a within-player, pressure-conditional
version of the primary predictor, not a restatement of it — and it comes
back null too, on a pool that (surprisingly, and reported as such) turned
out to be deep enough to support the additional split without losing a
single player. That strengthens the overall null's credibility by one more
independent angle, at no cost in statistical power, and closes the one
real inconsistency in this project's own methodology: every other Step 2
extension already had its escalation delta; the primary predictor is now
the last (not the only exception it used to be).

### How to reproduce
```
python3 src/robustness/entropy_pressure_escalation.py
```
Needs the raw MCP data already present locally in `results/{tour}/`. Per-
player output saved to `results/{tour}/entropy_pressure_escalation.csv`.
