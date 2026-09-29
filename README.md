# Shot-Selection Consistency and Clutch Performance in Tennis: A Reliability Warning for Clutch Metrics

Submission materials for the MIT Sloan Sports Analytics Conference (SSAC).

## The question

Does a player's **shot-selection consistency**, how predictable their choice
of shot is given the situation and measured as conditional Shannon entropy,
predict how well they perform under pressure ("clutch"), measured with a
leverage-weighted score in the style of Morris (1977)? Separately: can the
leverage-weighted clutch metrics already used by scouts and broadcasters, the
same family as Tennis Abstract's Balanced Leverage Ratio and the metric Stats
Perform presented at MIT Sloan SSAC 2022, actually be measured reliably
enough to support the claims made about them?

## The findings

**1. Leverage-weighted clutch metrics have reliability too low to trust,
particularly on return points, and no published clutch metric in tennis
appears to report its own reliability.** Split-half reliability testing
(splitting each player's matches into independent halves and checking how
well a repeated measurement agrees with itself) found
`conditional_normalized_entropy` highly reliable on both tours (0.90-0.93,
Spearman-Brown corrected). Leverage-weighted clutch scores are not: serve
clutch is moderate (0.57-0.58, below the conventional 0.70 "acceptable"
threshold) and return clutch is poor to effectively unmeasurable (ATP 0.23,
WTA 0.055), despite bucket sizes in the hundreds to thousands of points per
player, which rules out a thin-data explanation. Empirical-Bayes shrinkage
helps (ATP return 0.23 to 0.37, WTA return 0.055 to 0.13) but doesn't close
the gap, and correcting the project's own equivalence bound for both
variables' measurement error leaves ATP's null claim intact but pushes WTA
return's bound past 1, vacuous, no longer informative about the true
relationship at all. Any published or broadcast "clutch rating," especially
on return, should be treated as a noisy estimate until its own split-half
reliability is reported, the same standard expected of a psychometric
instrument. Details: follow-up check 4 below, and
[`paper/application_and_impact.md`](paper/application_and_impact.md).

**2. Separately, shot-selection consistency itself shows no relationship
with clutch performance, a well-powered null replicated independently on
two tours.** Across the qualified ATP pool (91 players, ≥40 charted matches
each) and a separately pre-registered WTA replication (55 players),
shot-selection entropy (`conditional_normalized_entropy`) shows no robust
relationship with leverage-weighted clutch performance, on serve or return,
across four leverage-weighting variants (p=0.60/0.65/0.70/tiered).

| Tour | Serve r (p) | Return r (p) | n |
|---|---|---|---|
| ATP | -0.041 (0.697) | +0.016 (0.877) | 91 |
| WTA | -0.259 (0.056) | +0.196 (0.151) | 55 |

WTA's serve correlation looks borderline before correction, but it doesn't
survive Bonferroni correction, Spearman rank re-testing, or influence-point
removal (full robustness battery in
[`docs/wta/wta_README.md`](docs/wta/wta_README.md)). ATP also has a TOST
equivalence bound, a stronger claim than "failed to reject the null": the
true effect can be bounded to |r| < 0.213 on serve and |r| < 0.189 on return
at 95% confidence. Full ATP write-up:
[`docs/atp/04_regression_results/step4_results_writeup.md`](docs/atp/04_regression_results/step4_results_writeup.md).
The leverage engine's own validation, including a head-to-head sanity check
on Djokovic and Federer's documented break-point reputation, is in
[`docs/atp/03_leverage_clutch/step3_README.md`](docs/atp/03_leverage_clutch/step3_README.md).

Nine follow-up checks were run after the main analysis, all pre-registered
before looking at results.

### 1. Pooling both tours

Combining ATP and WTA into one test (n=146): the point estimates look
different by eye, but a formal entropy×tour interaction term finds no
evidence the relationship actually differs by tour (serve p=0.146, return
p=0.207, and Cochran's Q agrees). The pooled test is still null, and an
independent Fisher z meta-analysis of the two tours' r values agrees.
Write-up: [`docs/combined/pooled_regression.md`](docs/combined/pooled_regression.md).

### 2. A fifth leverage variant

p60/p65/p70/tiered are all constants calibrated on ATP and reused unchanged
for WTA, even though the two tours differ in service dominance. Using each
tour's own observed server point-win rate instead (ATP 0.644, close to the
existing 0.65 constant; WTA 0.573, meaningfully lower than any existing
constant) still finds nothing that survives correction on either tour.
Building this also turned up something unplanned: rebuilding WTA's clutch
features from scratch reproduces the committed file exactly, but rebuilding
ATP's doesn't (differences up to ~0.005 in clutch scores), because the
original ATP script is gone and the current one is a reconstruction that
had only been checked against a handful of spot numbers, never a full-table
diff. Write-up, including that finding:
[`docs/atp/03_leverage_clutch/empirical_p_variant.md`](docs/atp/03_leverage_clutch/empirical_p_variant.md).

### 3. Ruling out measurement noise and floor artifacts

A check on whether the null could be an artifact of measurement noise or an
under/over-strict sufficiency floor rather than an absence of effect.
Weighting the regression by each player's charted-match count (a proxy for
how precisely their entropy is measured) doesn't surface a hidden
relationship: results scatter in sign rather than converging toward one
direction, which argues against noise masking a real effect. Separately,
the MIN_OBS=30 data-sufficiency floor turns out to have never actually been
binding for this pool, even tested up to 3x higher. A formal power analysis
also puts a number on "well-powered": both tours are well-powered for
medium-or-larger effects but not for small ones. Write-up:
[`docs/atp/04_regression_results/power_and_robustness.md`](docs/atp/04_regression_results/power_and_robustness.md).

### 4. Split-half reliability

This check changes which part of the null to trust. Splitting each player's
matches in two (interleaved by date, not first-half-of-career vs. second, to
avoid confusing career drift with measurement noise) and recomputing both
measures independently on each half shows `conditional_normalized_entropy`
is a highly reliable measurement on both tours (0.90-0.93, Spearman-Brown
corrected). The clutch score is not: serve clutch reliability is moderate
(0.57-0.58, below the conventional "acceptable" threshold), and return
clutch is poor to essentially unmeasurable (ATP 0.23, WTA 0.055). The
predictor was never the weak link: the outcome variable is, especially on
return, especially for WTA. That means the serve-side null carries real
evidentiary weight, while the return-side null, and the WTA return result
in particular, should be read as inconclusive rather than confirmatory: a
well-measured predictor paired with a barely-reliable outcome produces a
null result regardless of whether a true relationship exists. This is a
previously invisible limitation, reported here rather than smoothed over.

A follow-up check tested whether a continuous-slope outcome construction
(using 100% of a player's points instead of the top/bottom leverage
quartile) would fix this: it doesn't; reliability is equal or worse in
three of four cases, which rules out "the quartile split is the problem"
and points instead toward a genuinely small, noisy underlying effect.
Write-up: [`docs/atp/04_regression_results/split_half_reliability.md`](docs/atp/04_regression_results/split_half_reliability.md).

A second follow-up tried a different candidate fix: empirical-Bayes
shrinkage of each player's clutch score toward the pool mean, weighted by
their own data volume. This one helps, improving reliability in all four
tour/role combinations (e.g. ATP return 0.231 → 0.371, WTA return 0.055 →
0.132). It's a partial fix: none of the four clear the 0.70 "acceptable"
threshold even after shrinkage, so the underlying conclusion holds, but
it's the first correction that moves the needle at all. Write-up:
[`docs/atp/04_regression_results/shrinkage_reliability.md`](docs/atp/04_regression_results/shrinkage_reliability.md).

### 5. A third candidate fix, deferred since Step 1

Whether a mix-of-opponents effect (a player's high- and low-leverage return
points happening to fall against differently-strong servers) explains part
of return clutch's unreliability had been an open, named question since the
original leverage-clutch design decision. Adjusting each return point for
the serving opponent's own leave-one-out serve strength doesn't help: it
actively hurts: reliability falls on both tours (ATP 0.231 → 0.182, WTA
0.055 → -0.106). Of three fixes tried (continuous-slope, opponent
adjustment, shrinkage), only shrinkage helps, and even it doesn't fully
solve the problem: converging evidence that the reliability gap is a
property of the data, not a fixable construction choice. Write-up:
[`docs/atp/04_regression_results/opponent_adjusted_return_clutch.md`](docs/atp/04_regression_results/opponent_adjusted_return_clutch.md).

### 6. Era and surface confounds

The primary null was also checked against the two most obvious confounds a
reviewer could raise: player era and surface. (Ranking was considered too
but doesn't exist anywhere in the Match Charting Project's match metadata,
so it's disclosed as out of scope rather than proxied.) Adding career era
and surface mix as covariates to the entropy-clutch regression leaves
entropy non-significant on both tours, both roles, none surviving the
pre-registered Bonferroni threshold, and for WTA serve the coefficient
moves further from significance once these are included, not closer: the
opposite of what a masked confound would predict. This check is cheap to
run: unlike every other follow-up, it needs no raw MCP points data at all,
only each tour's small match-metadata file. Write-up:
[`docs/atp/04_regression_results/confound_check_era_surface.md`](docs/atp/04_regression_results/confound_check_era_surface.md).

### 7. Four secondary style predictors

Net-play escalation, wide-serve escalation, return-depth shift, and
dropshot rate were computed since Step 2, pre-registered as exploratory
variables, and never tested against clutch performance until now. Testing
all four against both clutch roles on both tours (16 comparisons,
Bonferroni-corrected) finds nothing that survives correction (another
null, not a second finding), but the check itself needed zero new data
extraction, only a merge of already-committed files: evidence the project's
infrastructure generalizes to new predictors rather than an untested claim
that it should. Write-up:
[`docs/atp/04_regression_results/secondary_predictors_regression.md`](docs/atp/04_regression_results/secondary_predictors_regression.md).

### 8. Disattenuated equivalence bounds

The equivalence bounds themselves were then corrected for measurement
unreliability on both sides, not just the point estimate. The project's
TOST bounds (|r| < 0.21 for ATP) are stated on the observed scale; dividing
by the attenuation factor implied by each variable's own split-half
reliability projects the equivalent bound onto the true (perfectly
measured) scale. ATP's equivalence claim survives, loosened but intact
(serve 0.21 → 0.29, return 0.19 → 0.32-0.41). WTA's does not, on return:
the disattenuated bound exceeds 1, even after the shrinkage fix, meaning
this project's data cannot rule out any true-score relationship at all for
WTA return once both variables' imperfect measurement is honestly
accounted for. That's a materially weaker claim than "no relationship,"
and the sharpest concrete illustration this project has of why a clutch
metric's own reliability has to be reported before its correlations mean
anything. Write-up:
[`docs/atp/04_regression_results/disattenuated_equivalence_bounds.md`](docs/atp/04_regression_results/disattenuated_equivalence_bounds.md).

### 9. Entropy under pressure

One more angle on the primary predictor itself: every other Step 2
extension (serve zone, net play, return depth) measures a
normal-vs-high-pressure escalation delta; entropy never did. Testing
whether a player's shot-selection consistency *changes* under pressure,
rather than just what its overall level is, closes that inconsistency and
finds the same answer as everything else: null, on both tours, both roles,
Bonferroni-corrected across the 4-comparison family. One honest surprise
along the way: splitting the data this much further was expected to shrink
the usable sample well below 91/55, and didn't: both full pools remained
sufficient. Write-up:
[`docs/atp/02_entropy_pipeline/entropy_pressure_escalation.md`](docs/atp/02_entropy_pipeline/entropy_pressure_escalation.md).

The null itself is the interesting result here: a carefully constructed,
pre-registered predictor that should plausibly matter for "clutch"
reputation doesn't detect one, and that holds across two tours, a combined
properly-powered test, and multiple robustness checks, not just one
convenient specification.

## Application and impact

Two things this project has a claim on: a broader, independent caution, and
a corrective for scouting/commentary narratives that treat stylistic
unpredictability as a pressure-performance asset. Split-half reliability
testing found that leverage-weighted clutch scores generally (the same
family of metric already published as Tennis Abstract's BLR and presented
at MIT Sloan SSAC 2022) can have poor measurement reliability, particularly
on return points, regardless of what predictor is being tested against
them, independent of this project's own null result. Full case, including a
reusable-infrastructure argument:
[`paper/application_and_impact.md`](paper/application_and_impact.md).
SSAC submission abstract draft: [`paper/abstract.md`](paper/abstract.md).

## Reproduce it

```bash
pip install -r requirements.txt
```

The pipeline fetches MCP data fresh from `raw.githubusercontent.com` rather
than shipping it (see [`DATA.md`](DATA.md) for why). Because every script
reads/writes plain relative filenames, run it from inside the tour's
`results/` folder so inputs and outputs land in the right place and nothing
touches the repo root:

```bash
# ATP
mkdir -p results/atp && cd results/atp
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-matches.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-2020s.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-2010s.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-to-2009.csv
python ../../src/pipeline/run_pipeline.py --tour atp --min-matches 40
cd ../..

# WTA
mkdir -p results/wta && cd results/wta
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-w-matches.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-w-points-2020s.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-w-points-2010s.csv
curl -O https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-w-points-to-2009.csv
python ../../src/pipeline/run_pipeline.py --tour wta --min-matches 40
cd ../..
```

`run_pipeline.py` prints the primary regression and the full p60/p65/p70/tiered/empirical
robustness table for whichever tour you ran, and writes `{tour}_qualified_pool_min40.csv`,
`{tour}_full_pool_features.csv`, `{tour}_clutch_features.csv`, and
`{tour}_merged.csv` alongside it. For a quick smoke test instead of the full
multi-decade pull, add `--decades 2020s` (sufficient for players whose careers
are entirely in the 2020s; not sufficient for the full qualified pool).

One caveat for ATP specifically: a fresh run computes clutch features from
scratch and lands very close to, but not bit-for-bit identical to, the
numbers quoted in `step4_results_writeup.md`. Those came from a frozen
`results/atp/step3_clutch_features.csv` whose original generating script no
longer exists (see `docs/atp/03_leverage_clutch/empirical_p_variant.md` for
the size of the gap; it doesn't change any conclusion). WTA reruns
reproduce the committed file exactly.

Both `src/pipeline/step1_validation.py` and `src/pipeline/step2_entropy_pipeline.py`
run a standing regression guard (`parsing.verify_hitter_parity()`) at the top
of their `__main__` block and fail loudly if hitter attribution doesn't match
ground truth at ≥85%: treat any run that doesn't print a parity rate near
90%+ as untrustworthy before looking at anything else.

## Repo layout

```
src/
  core/        shared modules: notation parsing, entropy/leverage math, data loading, feature construction
  pipeline/    step1_validation, step2_entropy_pipeline, run_pipeline, and the rest of the main pipeline
  robustness/  the 10 pre-registered follow-up checks
  figures/     the 7 export/plotting scripts
docs/
  atp/
    01_data_validation/   player-pool eligibility
    02_entropy_pipeline/  entropy pipeline methods + calculation derivations
    03_leverage_clutch/   leverage/clutch engine, related work, pre-registration
    04_regression_results/  the primary regression write-up
  wta/                 WTA replication: pre-registration + results, in one place
  combined/            cross-tour pooled regression: pre-registration + results
results/
  atp/       final ATP per-player CSVs (small; no raw or point-level data)
  wta/       final WTA per-player CSVs
  figures/   cross-tour comparison figure(s)
paper/       SSAC abstract and other paper-facing material
```

Docs are organized by tour first, build order second: `docs/atp/01...04`
keeps the order the ATP methodology was actually built and validated in,
while `docs/wta/` sits alongside it on its own, since the WTA replication
reused the validated ATP pipeline wholesale instead of going through its
own numbered stages.

`src/core/` holds everything the rest of the pipeline imports: `parsing.py`
(notation, hitter-attribution, score/pressure parsing), `formulas.py`
(entropy math, the leverage/win-probability engine, and general
statistical utilities like Bonferroni and TOST), `data_io.py` (loading
MCP files, provenance snapshots), and `features.py` (clutch/dropshot/
pressure feature construction). See `src/README.md` for exactly which
older single-purpose files these replaced and how each was verified.

`src/pipeline/run_pipeline.py` is the single entry point for a full tour
run. The rest of `src/pipeline/` is either an earlier per-stage script it
supersedes/wraps, or a variant reproduction path. `entropy_extraction_stage1.py`
+ `stage2_assemble_features.py` offer a disk-cached two-phase alternative
for the full-pool entropy extraction that may still be useful for iterating
without re-running the expensive extraction pass each time; both are kept
because the docs in `docs/` reference them directly, and both carry a note
pointing to `run_pipeline.py` as the canonical reproduction path.
`rerun_primary_regression.py` is a minimal, no-fetch way to reproduce just
the Step 4 regression numbers from an existing `{tour}_merged.csv`.
`rebuild_clutch_features.py` regenerates clutch features (e.g. for a new
leverage variant) without re-running entropy extraction; it never
overwrites a tour's primary CSV, always writing to a `_reconstructed`
suffixed file instead, printing a diff against the primary so any
provenance gap (see above) is visible on every run.

`src/robustness/` holds the pre-registered follow-up checks, each paired
with a write-up in `docs/atp/04_regression_results/` or `docs/combined/`.
`pooled_regression.py` runs the cross-tour analysis in `docs/combined/`
(needs both tours' `results/` outputs to already exist).
`power_and_robustness.py` runs the power/MDES, match-count-weighted
regression, and MIN_OBS threshold checks. `split_half_reliability.py` runs
the split-half reliability check (the slowest script in the repo: two full
extraction passes per half, per tour). `continuous_slope_reliability.py`
runs that check's follow-up (same cost profile; also cross-checks its own
quartile recomputation against `build_clutch_features()`'s output before
trusting either construction's reliability numbers).
`entropy_pressure_escalation.py` runs the entropy-under-pressure
escalation check, writing per-player output to
`results/{tour}/entropy_pressure_escalation.csv`. `shrinkage_reliability.py`
runs the empirical-Bayes shrinkage check, testing whether shrinking each
player's clutch score toward the pool mean (weighted by their own data
volume) improves split-half reliability; it does, in all four tour/role
combinations, unlike the continuous-slope construction, but none clear the
0.70 "acceptable" threshold. `opponent_adjusted_return_clutch.py` tests the
mix-of-opponents hypothesis deferred since Step 1 by adjusting return
clutch for each server's own leave-one-out serve strength; it doesn't
help, reliability falls on both tours. Reuses
`build_clutch_features(..., return_points=True)` unmodified for the
point-level table, no new parsing logic; same slow cost profile as the
other split-half checks. `confound_check_era_surface.py` adds career era
(median charted-match year) and surface mix (%clay, %grass) as covariates
to the primary entropy-clutch regression; the null holds on both tours
and roles. Needs no raw MCP points data, only each tour's small
match-metadata file already fetched for every other step; runs in
seconds. `secondary_predictors_regression.py` correlates the four
secondary Step 2 predictors (net-play escalation, wide-serve escalation,
return-depth shift, dropshot rate) against clutch score for the first
time; needs no raw MCP data, only the already-committed primary feature
and clutch files for both tours. `disattenuated_equivalence_bounds.py`
finds each tour/role's tightest TOST equivalence bound by binary search
on the real per-player data (cross-checked against the documented ATP
figures before trusting the new WTA numbers it produces), then divides by
each pairing's reliability-implied attenuation factor to get the
true-score bound; needs no raw MCP data either.

`src/figures/` builds the two figures in `paper/abstract.md`.
`export_split_half_data.py` reuses `split_half_reliability.py`'s functions
unchanged to export the per-player half-A/half-B values that script
computes but never saves, writing `results/figures/split_half_raw_{atp,wta}.csv`;
same slow cost profile as the robustness scripts above.
`export_split_half_clutch_counts.py` adds the per-half leverage-bucket
point counts to those same CSVs (clutch extraction only, skips the
entropy pass, so faster). `make_reliability_figure.py` plots those CSVs
into `results/figures/split_half_reliability_figure.png`.
`make_null_forest_figure.py` plots the primary entropy-clutch correlation
(r, 95% CI) across ATP, WTA, and pooled, into
`results/figures/null_forest_figure.png`. No longer one of the abstract's
two figures (superseded by the disattenuation figure below, which covers
the more novel result and all five leverage variants rather than one),
but still valid and kept for reference. `make_disattenuation_figure.py`
plots the disattenuated TOST equivalence bounds (observed-scale vs.
reliability-corrected, per tour/role) into
`results/figures/disattenuation_figure.png`; it imports
`robustness/disattenuated_equivalence_bounds.py` directly and reuses its
bound search and reliability tables unchanged, asserting its recomputed
ATP bounds match that script's documented values before saving.
`make_entropy_transition_illustration.py` is a supplementary,
docs-only figure (not one of the abstract's two): for Sinner and
Alcaraz, it plots the actual 6x6 shot-transition probability matrix
each player's conditional entropy number is computed from, into
`results/figures/entropy_transition_illustration.png`, referenced from
`docs/atp/02_entropy_pipeline/step2_README.md`. Reuses
`step2_entropy_pipeline.get_player_shot_transitions()` and
`compute_transition_entropy()` unchanged and asserts its recomputed
entropy for both players against the documented 0.7921/0.8000 before
saving. Needs the raw MCP 2020s points file locally; run from inside
`results/atp/`. `make_wta_entropy_transition_illustration.py` is the
WTA counterpart, for `docs/wta/wta_README.md`: Iga Swiatek vs. Bianca
Andreescu (chosen for charted-match coverage and entropy contrast, not
narrative; no WTA pair is named in this project's docs the way
Sinner/Alcaraz are for ATP), into
`results/figures/wta_entropy_transition_illustration.png`. No
prose-documented per-player value exists on the WTA side to check
against, so it instead asserts its recomputed entropy for both players
against the already-committed `results/wta/wta_full_pool_features.csv`.
Needs the raw MCP WTA points files locally; run from inside
`results/wta/`.

## Pre-registration and bug disclosures

Every hypothesis here was pre-registered before the relevant analysis was
run, and every bug found along the way is written up in place rather than
quietly fixed:

- [`docs/atp/03_leverage_clutch/step3_variable_preregistration.md`](docs/atp/03_leverage_clutch/step3_variable_preregistration.md)
  locks in primary vs. exploratory predictors before the regression exists.
  The WTA replication has its own pre-registration written before touching
  any WTA data:
  [`docs/wta/wta_replication_preregistration.md`](docs/wta/wta_replication_preregistration.md).
- A shot-parsing bug in Step 1/2 inverted every hitter label in every point.
  Caught by checking against ground truth, fixed by consolidating the
  parsing logic into one shared module (`src/core/parsing.py`). Full
  writeup, including before/after numbers:
  [`docs/atp/02_entropy_pipeline/step2_README.md`](docs/atp/02_entropy_pipeline/step2_README.md).
- Step 3's leverage engine (`src/core/formulas.py`) had a hardcoded
  server-alternation flag in the tiebreak branch, caught during a final
  review before sign-off. Writeup:
  [`docs/atp/03_leverage_clutch/step3_README.md`](docs/atp/03_leverage_clutch/step3_README.md).
- During the WTA replication, two numerically-equal but bit-different ways
  of writing the same probability flipped a cluster of tied leverage values
  across a quartile boundary. Writeup:
  [`docs/wta/wta_README.md`](docs/wta/wta_README.md).
- The Djokovic/Federer head-to-head check looked like a validation failure
  at first; it turned out to be a scoping error, not a bug. See
  [`docs/atp/03_leverage_clutch/step3_README.md`](docs/atp/03_leverage_clutch/step3_README.md).
- Rebuilding ATP's clutch features from scratch to add a new leverage
  variant showed, via a full-table diff, that the reconstruction doesn't
  exactly reproduce the frozen original file (WTA's rebuild does, exactly).
  Writeup: [`docs/atp/03_leverage_clutch/empirical_p_variant.md`](docs/atp/03_leverage_clutch/empirical_p_variant.md).

## Data and licensing

MCP data is fetched at run time, never committed, and licensed CC BY-NC-SA
4.0 by its original authors; see [`DATA.md`](DATA.md) for full attribution
and license details. The code in this repository is MIT-licensed (see
[`LICENSE`](LICENSE)); that license does not extend to MCP data.

## Tests

There's no dedicated automated test suite. The closest things to one are
`parsing.verify_hitter_parity()` (a runtime regression guard against the
Step 1/2 bug recurring) and `src/pipeline/step3_h2h_check.py` (an
independent validation diagnostic for the leverage engine). Worth adding a
real `tests/` directory if this pipeline gets extended further.
