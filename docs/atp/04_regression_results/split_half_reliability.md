# Split-Half Reliability of Entropy and Clutch Score: Pre-Registration and Results

## Pre-registration

Written before splitting any player's matches or computing a single
half-sample entropy or clutch value.

### Why this check

A null result has two very different explanations, and nothing run so
far distinguishes them: either shot-selection entropy genuinely doesn't
predict clutch performance (a true null), or one or both measurements are
too noisy, as measurements of the underlying trait, for any correlation
between them to show up even if a true relationship exists (an
unreliability problem, distinct from the sample-size/power questions
already addressed in `power_and_robustness.md`). Power and MIN_OBS
sensitivity ask "do we have enough players." This check asks a different
question: "if we measured the same player's entropy or clutch score
twice, independently, would we get a similar number both times." That's
ordinary split-half reliability, a standard psychometric check that
hasn't been applied to either measure in this project yet.

### Method

For each tour, every qualified player's charted matches are split into
two halves by sorting their match_ids (which are date-prefixed, so this
sort is chronological) and alternating: even positions in the sorted list
go to half A, odd positions go to half B. This is an interleaved split,
not a first-half-of-career vs. second-half-of-career split, specifically
so that a real change in a player's style or clutch performance over
their career doesn't get mistaken for measurement noise (an interleaved
split samples "early" and "late" matches into both halves roughly evenly).

Both `conditional_normalized_entropy` and `{role}_clutch_p65` (serve and
return) are recomputed independently on half A and half B, using the
exact same methodology as the primary pipeline (same category scheme,
same MIN_OBS=30 sufficiency floor applied per half, same leverage engine
at p=0.65) with the only difference being which half of a player's
matches feed the computation.

**Reliability metric**: the split-half correlation is the Pearson r
between each player's half-A and half-B value, across every player who
clears MIN_OBS=30 sufficiency in *both* halves independently. Because a
half-length measurement is inherently noisier than the full-length one
actually used in the primary analysis, the Spearman-Brown prophecy
formula (`r_full = 2*r_half / (1 + r_half)`) is applied to project what
the reliability of the full-career measurement would be.

### Commitment (fixed before running)

1. Results will be reported for both tours and all three measures
   (entropy, serve clutch, return clutch), regardless of outcome.
2. Splitting the data in half will push some players below the MIN_OBS=30
   floor in one or both halves who clear it on the full data. The number
   of players excluded this way will be reported explicitly, not routed
   around by loosening MIN_OBS specifically for this check — a high
   exclusion rate is itself informative about how much data a reliable
   per-player estimate actually needs.
3. Interpretation will use conventional psychometric benchmarks fixed
   before seeing results: reliability ≥0.70 is conventionally
   "acceptable," ≥0.80 "good," following common practice (e.g., Nunnally,
   1978). Below 0.70 will be reported as a genuine limitation on how much
   weight the primary null result can bear, not minimized after the fact.
4. This document will not be edited after seeing the computed values.

## Results

Written after running `src/robustness/split_half_reliability.py` exactly as
specified above. This is the most consequential check run in this
project since the original null result: it doesn't change the null, but
it changes which parts of it should be trusted.

### Reliability estimates

| Measure | Tour | n (both halves sufficient) | Split-half r | Spearman-Brown full-length r | Verdict (pre-registered benchmarks) |
|---|---|---|---|---|---|
| Entropy | ATP | 91 | 0.861 | **0.925** | Good |
| Entropy | WTA | 55 | 0.812 | **0.897** | Good |
| Serve clutch | ATP | 91 | 0.401 | **0.572** | Below acceptable |
| Serve clutch | WTA | 55 | 0.407 | **0.578** | Below acceptable |
| Return clutch | ATP | 91 | 0.131 | **0.231** | Poor |
| Return clutch | WTA | 55 | 0.028 | **0.055** | Effectively unreliable |

No players were excluded by the per-half MIN_OBS=30 floor for either
tour: all 91 ATP and all 55 WTA players remain sufficient in both halves,
for every measure. That's a clean result in its own right, and it means
none of the numbers above are inflated or suppressed by selective
attrition.

### The entropy predictor is not the weak link

`conditional_normalized_entropy` is a highly reliable measurement on both
tours (0.90-0.93 full-length reliability), comfortably above the
conventional "good" threshold. Whatever is limiting this study's ability
to detect a relationship, it isn't noise in the predictor. This is a
genuinely reassuring result for the paper: the "Robot vs. Magician" style
variable is a stable, well-measured trait of a player, not an artifact of
which matches happened to get charted.

### The clutch score is a different story, and the outcome side is where the real limitation lives

Serve clutch reliability (0.57-0.58 on both tours) sits below the
conventional 0.70 "acceptable" threshold pre-registered above. Return
clutch is worse: 0.23 for ATP (poor) and just 0.05 for WTA, which is
barely distinguishable from a coin flip's worth of measurement noise.
This means the null result should not be read as equally strong evidence
across serve and return. The serve-side null involves two moderately
reliable measures; the return-side null, especially for WTA, involves a
reliable predictor paired with an outcome measure that a null result
almost has to occur under, regardless of whether a true relationship
exists, simply because the outcome can't be measured precisely enough
with the current quartile-split construction and available data volume.

### Verification: is the WTA return figure (0.055) a bug?

Checked directly, since a number this low deserves scrutiny before being
trusted. Pulled every WTA player's actual half-A/half-B return clutch
values and their underlying bucket sizes:

- **Bucket sizes are large, not small.** Median ~550-600 points per
  high/low-leverage bucket, minimum 267, comfortably 10-50x the
  MIN_OBS=30 floor. This isn't a thin-sample artifact.
- **Spearman rho (0.023, p=0.865) matches Pearson r (0.028, p=0.839)
  almost exactly.** If a handful of outlier players were dragging down an
  otherwise-decent Pearson correlation, the rank-based Spearman version
  (robust to exactly that) would look meaningfully better. It doesn't, so
  this isn't a fragile correlation being wrecked by one or two bad data
  points.
- **The clutch scores themselves are tiny and the half-to-half swing is
  often as large as the entire between-player range.** The whole WTA
  return-clutch pool spans about -0.11 to +0.08. Individual players'
  half A vs. half B values often swing by nearly that much on their own
  (Radwanska: -0.106 → -0.002; Kim Clijsters: -0.013 → -0.081; Ana
  Ivanovic: +0.006 → +0.076).

That combination rules out a computational error and rules out "too few
points." What it points to instead: a win-rate-delta statistic on
point-level binary outcomes carries real sampling variance even at large
n when the true underlying effect is small, and whatever real
between-player differences exist in return clutch appear to be small
relative to that noise floor. One thing this check can't rule out and
hasn't tested: some of that noise could be a mix-of-opponents effect
rather than pure sampling noise, if a player's half-A and half-B
opponents differed somewhat in serve quality. That's exactly the
opponent-strength-adjustment question this project has explicitly
deferred since Step 1 (see `step3_README.md`'s known limitations), so it
isn't a new gap, but it means "unreliable measurement" is likely the
right diagnosis, not necessarily the complete one.

### Disattenuated correlation (with an important caveat)

Classical test theory gives a standard correction for measurement
unreliability: divide the observed correlation by the square root of the
product of both measures' reliabilities, estimating what the correlation
between the *true* underlying traits would be if both were measured
perfectly.

| Tour | Role | Observed r (p65) | Disattenuated r |
|---|---|---|---|
| ATP | Serve | -0.041 | -0.057 |
| ATP | Return | +0.016 | +0.035 |
| WTA | Serve | -0.259 | -0.360 |
| WTA | Return | +0.196 | **+0.886** |

The WTA return value is not a hidden strong relationship. It's the
textbook failure mode of disattenuation under near-zero reliability:
dividing by `sqrt(0.897 * 0.055) ≈ 0.221` amplifies a small, noisy
observed correlation by a factor of ~4.5, and the resulting number is
essentially uninterpretable rather than a real effect-size estimate. It's
reported here for completeness and as a direct illustration of *why* the
0.055 reliability figure above is a genuine problem, not just a mildly
disappointing number: below roughly 0.70-0.80 reliability, disattenuation
stops being a rescue and starts being noise amplification. The ATP and
WTA serve values (reliabilities 0.57-0.58) are more stable, though still
below the range where disattenuation is considered trustworthy, and both
remain small in magnitude either way.

### Honest verdict

This check doesn't reverse the null, but it changes how confidently
different parts of it can be cited. The predictor is solid. The outcome
variable is not uniformly solid, particularly on return, and particularly
for WTA. The paper should state plainly that the serve-side null carries
more evidentiary weight than the return-side null, and that the WTA
return-side result specifically should be treated as inconclusive due to
outcome-measurement unreliability rather than as confirmatory evidence of
"no relationship." This is a genuine, previously invisible limitation
that a reviewer would be right to ask about, and it's better to name it
here first.

The follow-up check below rules out one candidate fix (switching to a
continuous-slope construction) and, by ruling it out, makes the
"genuinely small effect, high per-point noise" explanation more likely
than "we built the outcome measure badly."

## Follow-up: does a continuous-slope construction improve outcome reliability?

### Pre-registration

Written before computing a single continuous-slope value. The clutch
score's low reliability (above) could come from the quartile-split
construction itself throwing away the middle 50% of a player's points, or
it could be a property of the data independent of construction choice
(small true effect, high per-point noise). This follow-up tests which.

**Method**: for each player and role, instead of a win-rate delta between
top and bottom leverage quartiles, fit `won ~ leverage_p65` (OLS, linear
probability model, consistent with the OLS used everywhere else in this
project rather than logistic regression) across *all* of that player's
points for that role, and take the slope. This uses 100% of a player's
points instead of the top/bottom 25%. Computed on the exact same
half-A/half-B split already built for the quartile check, and gated by
the identical `n >= MIN_OBS*4` total-point floor the quartile construction
uses (not a looser floor for the continuous version), specifically so any
reliability difference is attributable to the construction method, not to
comparing different player samples. `build_clutch_features()` gained an
optional `return_points=True` argument to expose the point-level leverage
table it already computes internally, rather than duplicating any of the
leverage/hitter-attribution logic in a second script.

**Commitment**: report split-half reliability for both constructions,
both tours, both roles, regardless of outcome. This check is scoped to
reliability only — it does not rerun the primary hypothesis test with a
continuous-slope outcome. If reliability improves meaningfully, that's a
candidate secondary measure for a future check, reported as such, not a
retroactive replacement of the pre-registered quartile-based primary
outcome. This section will not be edited after seeing results.

### Results

Written after running `src/robustness/continuous_slope_reliability.py` exactly as
specified above. Before trusting either construction's reliability
numbers, the quartile values recomputed by this script were cross-checked
against `build_clutch_features()`'s own output: 292 values compared
across both tours and both halves, max difference 0.00 (exact match).

| Tour | Role | Quartile r_full | Continuous-slope r_full | Delta |
|---|---|---|---|---|
| ATP | Serve | 0.572 | 0.465 | -0.107 |
| ATP | Return | 0.231 | 0.256 | +0.025 |
| WTA | Serve | 0.578 | 0.542 | -0.037 |
| WTA | Return | 0.055 | **-0.026** | -0.080 |

The continuous-slope construction does not improve reliability anywhere,
and makes it worse in three of four cases. WTA return goes slightly
negative, which is if anything a worse result than the quartile version's
0.055 (a negative split-half correlation means the two halves aren't just
noisy, they're actively uncorrelated).

This directly answers the question the follow-up was pre-registered to
test: **the quartile-split construction is not the cause of the clutch
score's reliability problem.** Using 100% of a player's points instead of
the top/bottom 25% doesn't help, and using all of them (including the
large mass of low-leverage, low-information points near the middle of the
distribution) appears to dilute the signal from the highest-contrast
points rather than average out noise, which is a plausible reason the
quartile version holds up at least as well. That rules out "we're just
discarding good data" as an explanation, and leaves the two explanations
already named in the verification section above: a genuinely small true
effect relative to per-point noise, and/or an uncontrolled opponent-mix
difference between halves. Both point away from a fixable construction
choice and toward either the data itself or a scope decision (opponent
adjustment) already disclosed as deferred. There's no reason, based on
this check, to prefer the continuous-slope construction over the
pre-registered quartile-split one for any future use.

### How to reproduce
```
python3 src/robustness/continuous_slope_reliability.py
```
Same cost profile as `split_half_reliability.py` (two full extraction
passes per half, per tour); reuses that script's data-loading and
match-splitting functions directly.

### How to reproduce the original split-half check
```
python3 src/robustness/split_half_reliability.py
```
The slowest script in the repo: two full extraction passes (entropy
transitions + clutch/leverage) per half, per tour, using the raw MCP data
already present locally in `results/{tour}/`.
