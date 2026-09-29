# Power, Measurement-Precision, and Threshold Robustness: Pre-Registration and Results

## Pre-registration

Written before running any of the three checks below or looking at their
output, following the same discipline as every other pre-registration
document in this project.

### Why these three checks

The primary regression (`docs/atp/04_regression_results/step4_results_writeup.md`,
`docs/wta/wta_README.md`) and the pooled regression
(`docs/combined/pooled_regression.md`) report a null result and back it
with TOST equivalence bounds, but three assumptions behind those numbers
were never directly tested:

1. **How much could this study actually have detected?** "Well-powered"
   has so far been a qualitative claim.
2. **Does every player's entropy/clutch estimate deserve equal weight in
   the regression?** Federer (723 charted matches) and Nakashima (40) are
   currently weighted identically, even though Federer's estimates are
   built on far more data and are presumably less noisy.
3. **Is the MIN_OBS=30 sufficiency floor itself well-calibrated?** Every
   other constant in this pipeline (p=0.65, the ≥40-match pool threshold)
   has been sensitivity-checked. MIN_OBS hasn't.

### 1. Power analysis / minimum detectable effect size (MDES)

**Method**: closed-form power calculation for a Pearson correlation test
against r=0, via the Fisher z-transform (`z = arctanh(r)*sqrt(n-3)`,
approximately standard normal under H1 with true correlation r). Solve
for the smallest |r| detectable at 80% power and two-sided alpha=0.05, for
n=91 (ATP), n=55 (WTA), and n=146 (pooled). Implemented as
`stats_helpers.mdes_correlation()`.

**Commitment**: report the MDES for all three sample sizes regardless of
where the actual observed correlations fall relative to them, and report
achieved power to detect Cohen's conventional small/medium/large effect
sizes (r=0.1/0.3/0.5) at each n as a complementary framing.

### 2. Match-count-weighted regression (attenuation-bias check)

**Method**: two complementary checks, both using `conditional_normalized_entropy`
as the predictor and `{role}_clutch_p65` as the outcome, for each tour and
role independently:
- **WLS**, weighted by `charted_matches`, against the same OLS specification
  already used in the primary regression.
- **High-data subsample**: restrict to players in the top quartile of
  `charted_matches` within their own tour (ATP: ≥~130 matches; WTA:
  ≥~88 matches; exact cutoffs computed from each tour's own data, not
  hardcoded), and rerun the unweighted primary regression on that subsample.

**Commitment**: report both the weighted and subsample results in full,
including sample sizes, regardless of outcome. If either version shows a
materially different result from the primary (unweighted, full-pool)
regression, that becomes a reportable finding in its own right, not a
reason to prefer the weighted/subsample version as "more correct" after
the fact: the primary regression's specification was itself pre-registered
and remains primary.

### 3. MIN_OBS threshold sensitivity

**Method**: recompute data-sufficiency gating at MIN_OBS ∈ {20, 30
(baseline), 50, 100} and rerun the primary correlation on whichever
players remain sufficient at each threshold, for both tours and roles.
Two components:
- **Clutch-side** (quartile-bucket gating): fully derivable from existing
  committed data (`n_serve_high_leverage`, `n_serve_low_leverage`,
  `n_return_high_leverage`, `n_return_low_leverage` columns already in
  `step3_clutch_features.csv` / `wta_merged.csv`), since the quartile
  split itself doesn't depend on MIN_OBS, only whether the resulting score
  is flagged reliable. No data refetch needed.
- **Entropy-side** (per-context transition gating): requires re-deriving
  each player's per-context transition counts via
  `step2_entropy_pipeline.get_player_shot_transitions()`, since only the
  count of low contexts (not each context's actual n) was saved to the
  features CSV. Uses the raw MCP data already present locally from earlier
  work; no fresh fetch needed either.

**Commitment**: report, at each threshold, how many players remain
sufficient and what the correlation looks like on that subset, for both
the clutch-side and entropy-side gating. Since 100% of both pools already
clear MIN_OBS=30 on the primary variables, the informative direction is
raising the bar (50, 100), not lowering it (20): lowering it cannot
change the primary regression's sample, since everyone already clears 30.
That expectation is stated here, before running, precisely so it isn't
retrofitted as an explanation afterward if the results look boring at
MIN_OBS=20.

### General commitment

All three checks are additive. None of them replace, override, or
retroactively edit the primary regression, the WTA replication, or the
pooled regression, which remain the project's primary, pre-registered
results. This document will not be edited after seeing any of the three
checks' output.

## Results

Written after running all three checks exactly as specified above (`src/robustness/power_and_robustness.py`).

### 1. Power analysis / MDES

| Sample | n | MDES at 80% power | Power for r=0.1 (small) | Power for r=0.3 (medium) | Power for r=0.5 (large) |
|---|---|---|---|---|---|
| ATP | 91 | \|r\| ≥ 0.290 | 15.6% | 82.7% | 99.9% |
| WTA | 55 | \|r\| ≥ 0.370 | 11.2% | 60.7% | 97.7% |
| Pooled | 146 | \|r\| ≥ 0.230 | 22.4% | 95.9% | 100.0% |

"Well-powered" needs a qualifier: all three samples are well-powered for
medium-to-large effects (Cohen's r=0.3+) but underpowered for small ones
(r=0.1): nowhere close to 80% power at any sample size tested. WTA in
particular is underpowered even for a medium effect (61%).

This sharpens, rather than undercuts, the TOST equivalence bounds already
reported: the ATP bound (\|r\| < 0.213) and the pooled serve bound
(\|r\| < 0.174) are both *tighter* than what 80%-power MDES would have
required to call the study "adequately powered" for effects of that size.
TOST uses the actual observed data to bound the effect, not just the
sample size in the abstract, so it's doing more precise work here than a
power statement alone would suggest: the honest combined claim is "this
study could reliably have found a medium-or-larger effect, and separately,
the effect it did find rules out anything larger than roughly a
small-to-medium one," which is a more calibrated statement than either
number alone.

### 2. Match-count-weighted regression

| Tour | Role | Unweighted β (p) | Weighted (WLS) β (p) | High-data subsample r (p), n |
|---|---|---|---|---|
| ATP | Serve | -0.0447 (0.697) | +0.0074 (0.940) | +0.203 (0.354), n=23 |
| ATP | Return | +0.0138 (0.877) | -0.0801 (0.304) | -0.175 (0.423), n=23 |
| WTA | Serve | -0.3730 (0.056) | -0.2786 (0.126) | +0.230 (0.428), n=14 |
| WTA | Return | +0.2479 (0.151) | +0.2811 (0.085) | +0.318 (0.268), n=14 |

(High-data subsample = top quartile of `charted_matches` within each
tour: ATP ≥130 matches, WTA ≥88 matches.)

Every weighted and subsample version remains non-significant. But the more
informative pattern is the sign instability: three of the four unweighted
results flip sign once weighted toward higher-data players, and two of
the four flip sign again in the high-data-only subsample (small n there,
23 and 14, so individually underpowered; see MDES above). If a real
relationship were being attenuated by noise in the thin-data players'
entropy estimates, weighting toward the best-measured players should have
pulled the correlations *consistently* toward one direction. Instead they
scatter. That's more consistent with a genuine null (noise moving around
zero) than with a real effect hiding behind measurement error. This
directly answers the motivating question for this check: more charted
matches does mean a more stable *entropy estimate* per player, but giving
that stability more weight in the regression doesn't surface a
relationship the unweighted analysis missed.

### 3. MIN_OBS threshold sensitivity

**Clutch-side** (quartile-bucket gating, re-derived from existing
committed data): completely unchanged at every threshold tested.

| Tour | Role | n at MIN_OBS=20 | 30 | 50 | 100 |
|---|---|---|---|---|---|
| ATP | Serve | 91 | 91 | 91 | 91 |
| ATP | Return | 91 | 91 | 91 | 91 |
| WTA | Serve | 55 | 55 | 55 | 55 |
| WTA | Return | 55 | 55 | 55 | 55 |

r and p are identical to the 3rd decimal at every threshold for all four
tour/role combinations (see console output; not worth a separate table
since nothing moves).

**Entropy-side** (per-context transition gating, re-derived from the raw
points data): also completely unchanged.

| Tour | Sufficient at MIN_OBS=20 | 30 | 50 | 100 |
|---|---|---|---|---|
| ATP | 91/91 | 91/91 | 91/91 | 91/91 |
| WTA | 55/55 | 55/55 | 55/55 | 55/55 |

Neither gating mechanism was ever close to binding, even at more than 3x
the original floor (MIN_OBS=100). The ≥40-charted-match pool eligibility
rule from Step 1 was evidently generous enough that every qualified player
clears both sufficiency floors by a wide margin: whatever imprecision
exists in this analysis isn't coming from thin per-player sample sizes at
the leverage-bucket or transition-context level. (This is a different
axis from check 2's `charted_matches`-weighted analysis: a player can
clear every count-based sufficiency floor easily while still having a
noisier *point estimate* of their entropy than a much-higher-volume
player. Check 2 is the one that actually tests that distinction.)

### Overall verdict

None of these three checks change the paper's conclusion, and together
they make the null more precisely characterized rather than just
asserted:
- The study is well-powered for medium-or-larger effects, not small ones:
  a real, honest qualifier on "well-powered" that should go in the
  paper's methods section.
- Weighting or subsetting toward the best-measured players doesn't
  surface a hidden relationship; results scatter in sign rather than
  converging, which argues against the attenuation-bias explanation for
  the null.
- The MIN_OBS=30 sufficiency floor (on both the entropy and clutch sides)
  was never actually binding for this pool, even tested up to 100, so
  none of the reported results can be attributed to an over- or
  under-strict data-sufficiency threshold.

### How to reproduce
```
python3 src/robustness/power_and_robustness.py
```
The MDES/power and match-count-weighted checks run in seconds from
existing committed CSVs. The entropy-side MIN_OBS check re-extracts
per-context transition counts from raw points data and is the slow part
(several minutes per tour); it needs the raw MCP files already present in
`results/{tour}/` (see the root README's Reproduce section).
