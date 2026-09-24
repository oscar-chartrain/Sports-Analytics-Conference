# WTA Replication — README

## Purpose
Independent replication of the pre-registered ATP analysis
(`conditional_normalized_entropy` predicting `serve_clutch_p65` /
`return_clutch_p65`) on the WTA, using the identical pipeline logic, to test
whether the ATP null generalizes to a second, independent population.
Pre-registered before touching any WTA data — see
`wta_replication_preregistration.md`.

## What is verified-identical vs. reconstructed
`src/core/parsing.py`, `step2_entropy_pipeline.py`, and the leverage
engine (`src/core/formulas.py`) are used completely unmodified — same
functions, only the input data changed. The clutch-score orchestration
function (`build_clutch_features()`, in `src/core/features.py`) was **not
recoverable** from the original ATP work; it has been reconstructed from
the original Step 3 design notes
(now folded into `step3_README.md`'s "Related work" and "Key decisions"
sections) with the actual `quartile_clutch()` function reused verbatim
from `step3_h2h_check.py` (real, validated code, not a reconstruction).
The one genuine provenance gap is the "tiered" pressure variant, whose
exact mechanism those design notes don't fully specify — see
`build_clutch_features()`'s docstring for the specific interpretation
used and why. The primary p=0.65 result and the p=0.60/0.70 fixed-constant
robustness checks carry full confidence; the tiered variant should be
cited as a secondary, reconstructed check.

## Data-volume-driven threshold decision (made before seeing any result)
WTA has 4,080 total charted matches vs. ATP's 7,567 (~54%). At the
identical ≥40-charted-match threshold, this yields 55 qualified players
vs. ATP's 91 — proportional to the underlying data volume, not a
methodological loosening. The boundary-eligibility player (Veronika
Kudermetova, exactly 40 matches) was sparsity-checked the same way Step 1
checked Nakashima for ATP: all 6 core entropy cells cleared 900+
observations, confirming the threshold is safe for WTA too.

## Data-quality checks (same standard as Step 1/2)
- **Hitter-parity regression guard**: 96.3% match rate against `PtWinner`
  ground truth (141,355 winner-marked points checked) — even higher than
  ATP's 90.3%, confirming the notation-parsing and hitter-attribution logic
  generalizes correctly to the WTA data, not just coincidentally to ATP's.
- **Sufficiency coverage**: 100% of the 55-player pool clears `MIN_OBS=30`
  on `pooled_entropy`, `transition_entropy` (the primary predictor),
  `dropshot_rate`, `serve_zone`, `net_play`, and `return_depth`.
  `dropshot_direction_entropy` clears for only 1/55 players (vs. ATP's
  9/91) — same rare-subgroup pattern, excluded from pool-wide use for the
  same pre-registered reason.
- **Merge integrity**: entropy-features and clutch-features tables merged
  cleanly on player name, 55/55, no mismatches.

## Bug found and fixed during this review (before anything was reported further)
Comparing the packaged `build_clutch_features()` deliverable against the
original inline computation surfaced a real, if narrow, precision bug: the
"tiered" variant computed `p_tiered = 0.65 - 0.0075` in one version and
`p_tiered = 0.6425` (the literal) in the other. These are equal in real-number
terms but differ by ~1e-16 in IEEE 754 floating point. Because leverage
values are heavily discretized (many points share the exact same discrete
score state, and therefore the exact same leverage value — e.g. 1,478 points
tied at a single value in a 50K-point sample), a quartile boundary can land
exactly on a tie cluster. A 1e-16 floating-point wobble was enough to flip
an entire tied cluster of points across that boundary, which is how a
bit-level rounding difference produced a visible ~0.007 shift in one
player's tiered clutch score. Fixed by using a single canonical literal
(0.6425) and, more importantly, by regenerating all output from one script
run rather than maintaining two parallel implementations that could
silently diverge. Verified self-consistent by re-running the canonical
script twice and confirming byte-identical output (max diff = 0.0).

Impact on conclusions: negligible. The corrected serve-side tiered
correlation moved from r=-0.2656 (p=0.0500) to r=-0.2635 (p=0.0519) — a
shift in the fourth decimal place of the correlation, not a change in any
substantive finding. This is recorded here rather than silently corrected,
consistent with this project's standing bug-disclosure practice. The p60,
p65, and p70 variants were never affected (they use clean literals with no
computed-vs-literal discrepancy), and neither was the primary hypothesis
test.

## Primary result

| Role | Pearson r (p65) | p |
|---|---|---|
| Serve | -0.259 | 0.056 |
| Return | +0.196 | 0.151 |

At face value this looks like it might contradict the ATP null (serve is
borderline, and one robustness variant, p70, crosses p<0.05 at 0.017). It
doesn't survive the same scrutiny the ATP null was put through:

| Check | Serve | Return |
|---|---|---|
| Spearman rank correlation | rho=-0.174, p=0.203 | rho=+0.131, p=0.341 |
| After removing 3 most influential players | r=-0.181, p=0.199 | r=+0.242, p=0.084 |
| Quadratic term added | linear term p jumps to 0.183 | — |
| Bonferroni-adjusted threshold (8 comparisons) | need p<0.0063 | need p<0.0063 |
| Heteroskedasticity (Breusch-Pagan) | none (p=0.176) | none (p=0.970) |

The Pearson correlation on serve is driven partly by a handful of specific
players (Linette, Radwanska, Kerber carry the highest Cook's distance) and
weakens substantially under a nonparametric rank test.

**Fifth variant added later: tour-specific empirical p.** WTA's own
observed server point-win rate is 0.5725 — meaningfully lower than any of
the fixed constants above (0.60/0.65/0.70), consistent with WTA's
real, documented lower service dominance relative to ATP. Using it:
serve r=-0.266 (p=0.050), return r=+0.260 (p=0.055). This is the smallest
nominal p-value in the now-10-comparison family (5 variants x 2 roles), but
it is **not** a new departure from the pattern above — it sits alongside
the existing p70/tiered/p65 borderline values, and the family-wise
Bonferroni-corrected threshold across all 10 comparisons is 0.0050, which
nothing clears. Full write-up (including the ATP side and a provenance
finding it surfaced):
`docs/atp/03_leverage_clutch/empirical_p_variant.md`.

No comparison across either role, at any of the now 5 leverage variants,
survives correction for the number of comparisons run.

## A reliability caveat that hits WTA return particularly hard
Split-half reliability testing (`docs/atp/04_regression_results/split_half_reliability.md`)
found `conditional_normalized_entropy` highly reliable on WTA (0.897,
Spearman-Brown corrected). WTA serve clutch is moderately reliable (0.578,
comparable to ATP's 0.572). WTA return clutch, however, comes in at 0.055
full-length reliability, essentially indistinguishable from measurement
noise. The WTA return-side null above should be read as inconclusive
rather than confirmatory: a predictor that's well-measured, paired with
an outcome that currently isn't, will produce a null result regardless of
whether a true relationship exists. The WTA serve-side null and the ATP
results carry more evidentiary weight than the WTA return-side result
specifically.

## Honest verdict
The WTA data is a second null, not a contradiction of the ATP result. It's
a noisier null than ATP's (smaller n, 55 vs. 91, means wider confidence
intervals and more point-estimate wobble), but there's no robust evidence
of a relationship between shot-selection entropy and clutch performance on
either tour, by either measure of robustness applied. That conclusion is
on solid footing for serve; for WTA return specifically, see the
reliability caveat above before citing it with the same confidence. This
is still the stronger paper outcome overall: independent replication
across two populations, identical pre-registered pipeline, same
substantive conclusion, now reported with an honest account of where the
measurement itself is the limiting factor.

## Convergent check
Entropy vs. `blr_combined` (field-standard Balanced Leverage Ratio):
r=+0.006, p=0.967 — null, consistent with the role-separated result once
you account for the fact that BLR pools serve and return together (any
opposite-signed, non-robust role effects would partially cancel in a
combined metric anyway).

## Outputs
(paths below are relative to the repo root, post-reorg)
- `results/wta/wta_full_pool_features.csv` — 55 players, entropy/style
  features (identical schema to `results/atp/step2_full_pool_features.csv`)
- `results/wta/wta_clutch_features.csv` — 55 players, clutch scores
  (identical schema to `results/atp/step3_clutch_features.csv`)
- `results/wta/wta_merged.csv` — merged, regression-ready
- `build_clutch_features()`, in `src/core/features.py` — reconstructed
  orchestration function, with provenance notes
- `results/figures/step5_atp_wta_comparison_scatter.png` — side-by-side
  scatter, both tours, both roles
