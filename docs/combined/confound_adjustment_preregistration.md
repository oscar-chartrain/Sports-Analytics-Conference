# Pre-registration: confounder adjustment of the clutch score (surface, opponent, time, format)

Written 2026-11-18, before `src/robustness/confound_adjusted_clutch.py` was run. Self-registered,
and written after all earlier results were known (see `preregistration_timeline.md`). No adjusted
result had been seen when this was written. Only the raw (unadjusted) full-sample scores were
computed, to check that the new code reproduces the committed clutch tables (it does, to 1e-16 on
the regenerated tables).

## Why

Section 7 lists surface, opponent and era as uncontrolled. They matter for the *reliability*
finding in two opposite ways. (a) They can add match-level noise to a player's clutch score
(surface and opponent mix change from match to match), which would make the score look less
reliable than the underlying construct. (b) They can add *stable* between-player signal (players
who play mostly on grass have a different leverage mix), which would make the score look more
reliable than it is. The earlier era/surface check (`confound_check_era_surface.py`) controlled
player-level mixes in the entropy-clutch regression only. The opponent adjustment covered return
points only. Neither tested reliability.

A concrete confound mechanism: leverage depends on the score state, and the score state depends on
the opponent and the surface (a weak opponent produces fewer tight scores; grass produces more
tiebreaks). A player's top-leverage points are therefore drawn disproportionately from tight
matches against strong opponents, and their bottom-leverage points from easy matches. The raw
top-minus-bottom difference then mixes clutch with opponent strength.

## Estimators (same points, players, leverage p = 0.65 and quartile rule as the paper)

Outcomes: S (serve-point win), Rt (return-point win), R1 (rally-decided point win). R2 and R3
are shot-level ratio outcomes and are not adjusted.

**A. Covariate adjustment (ANCOVA within player and leverage bucket).** For every point define a
pseudo-outcome z = won - x'b, where x holds the point's context and b is estimated by pooled
least squares of `won` on x after removing each player's cell means. Cells are
player x leverage bucket (top quartile, middle, bottom quartile), using the player's full-sample
thresholds for the role (for R1: thresholds from all of the player's points, rally points only).
Removing cell means makes b identified from within-player, within-bucket variation, so it cannot
absorb the leverage effect itself. The adjusted clutch score is the paper's quartile difference
computed on z in place of `won`. Covariates (core set):
- surface: Clay and Grass indicators (Hard and unrecognised values are the base);
- Best-of-5 indicator;
- match date in decades (centred), a linear time/era term inside a player's career;
- opponent strength: the opponent's win rate in the opposing role (the returner's return-win rate
  on the player's serve points; the server's serve-win rate on the player's return points),
  computed leave-pair-out (excluding every point from matches between the player and that
  opponent) and shrunk to the tour mean with weight K = 200 points,
  (wins + K x mean) / (n + K). K = 200 is the ratio of binomial noise variance to an assumed
  true-spread variance of about 3.5 pp, fixed now.
Coefficients are estimated separately for S, Rt and R1. For R1 the covariates are interacted with
the player's role on the point and a role indicator is added, so the role mix of top and bottom
leverage points is also adjusted. Columns with no variation (for example Best-of-5 in WTA) are
dropped. Coefficients are estimated once on the full sample and held fixed across halves and
splits (a nuisance parameter fit on hundreds of thousands of points). A check at the original
split re-estimates them inside each half.

Sensitivity versions of A: extended set (core + late round [QF, SF, F] + Grand Slam indicator);
opponent shrinkage K = 50 and K = 1000.

**B. Within-match estimator (match fixed effects).** For each player and each match with at least
3 points in both the top and bottom bucket, take that match's top-minus-bottom difference in the
raw outcome. The score is the weighted mean over matches with weights 1/(1/n_top + 1/n_bottom).
A half is scored only if the matches used hold at least 30 top and 30 bottom points (the paper's
floor). B removes every influence that is constant within a match (opponent, surface, round,
conditions, form on the day) with no model. It cannot remove confounds that vary within a match,
and it discards matches with too few points in one bucket.

## Reported

For A (core, and the sensitivity versions) and B, beside the raw score from the same code, for the
ATP and WTA and for S, Rt, R1:
1. Split-half reliability (Spearman-Brown): original split, and the median, 2.5th and 97.5th
   percentile and share of splits at or above 0.70 over 1,000 random balanced splits (seed
   20261119; the same splits for every estimator). Chronological split (earlier half of each
   player's matches against the later half) with player-bootstrap intervals (2,000).
2. Between-player spread: the standard deviation of full-sample scores, the match-clustered
   true spread and implied reliability (the paper's two-stage estimator, 95% intervals from 2,000
   player bootstraps), the correlation of the adjusted with the raw score, and the mean
   adjusted-minus-raw shift in percentage points.
3. The estimated covariate coefficients with match-clustered standard errors.
4. The paper's headline entropy-clutch correlation (conditional normalised entropy against serve
   and return clutch) recomputed with the adjusted full-sample scores of A (core) and B, beside the
   raw value.

## Decision rule, fixed in advance

An adjusted score is "reliably measured" only by the paper's criterion: random-split median at
least 0.70 and at least 95% of splits at or above 0.70. Interpretation:
- If no adjusted score in any tour and outcome meets the criterion, the paper reports that the
  unreliability is not explained by surface, opponent, time or format.
- If some do, the paper must say the conclusion depends on adjustment, name which, and revise the
  title-level claim.
- If an adjusted median is at least 0.10 above the raw median but still below the criterion, the
  paper reports the improvement as partial.
- If adjusted reliability is lower than raw, the paper reports that part of the raw stable spread
  was context, not clutch.
- For the entropy-clutch correlations, the test family is 4 (two tours, serve and return) per
  adjustment; a correlation counts as significant only below 0.05 / 4 = 0.0125. A change in
  conclusion is reported as such.
No estimator, covariate set or threshold is changed after seeing results. Specifications other
than the core A and B are sensitivity checks and cannot change the primary reading.

## Validation (script aborts if any fails)

V1. The raw scores from the new code reproduce the committed original-split reliabilities of S,
Rt and R1 (`allshots_reliability.csv`) within 0.001, and the full-sample serve and return clutch
of every player equal the regenerated clutch tables to within 1e-9.
V2. The new fast routine reproduces `rally_extension.sums` on random splits for random players,
for the raw outcome and for an adjusted one, to within 1e-9.
V3. The per-point context arrays align with the player arrays (same matches, same outcomes).
V4. Leave-pair-out opponent strength matches a brute-force recomputation on 200 random points.
V5. With all covariates set to zero the adjusted score equals the raw score exactly.
V6. Simulation with known truth, per tour, on the real design (leverage, context, matches),
outcomes redrawn as Bernoulli with each player's role rate plus the fitted covariate effects:
 (i) no clutch effect: the mean of A and of B across players must lie within 3 standard errors
 of zero, at the fitted covariate effects and at three times them (the latter forces the raw
 score to be visibly biased if the covariates are confounded with leverage);
 (ii) a planted per-player clutch effect (N(0, 4 pp) added to each player's top-quartile points):
 the mean regression slope of the score on the planted effect, over 5 replicates, must lie in
 [0.85, 1.15] for A and for B.
The raw score's bias in these simulations is reported, not tested.

## Not done

No two-way (server and returner) strength model, no opponent strength by surface, no indoor or
altitude covariate (not in the match file), no adjustment of R2 or R3, no adjustment for
within-match confounds beyond the leverage quartile (fatigue, score-dependent tactics), no
re-estimation of the multilevel or match-nested models with covariates.

## Changes to the validation design recorded 2026-11-18 (before the full run)

A smoke run on WTA with 5 random splits was made to debug the code. Its adjusted results were seen
(they differ little from the raw ones). The run exposed three weaknesses in the V6 simulation
design. No estimator, covariate, threshold, split, seed or decision rule was changed; only the
validation was.

1. V6(i) as written compared each estimator's mean with zero in units of its own sampling noise.
   Raw, A and B are computed from the same simulated outcomes and share their noise, so a 3-SE
   noise draw (a +0.9 pp mean for B in the WTA x3 case) made the unbiased estimators fail. The
   check is now paired: the same uniform draws generate outcomes with the covariate effects and
   without them (true clutch 0), each estimator is applied to both, and the per-player
   difference (the bias) must be within 3 SE of zero. This is a stricter test.
2. With the real covariates the raw score was hardly biased even at three times the effect, so
   V6(i) could not tell a working adjustment from a no-op. V6(iii) was added: leverage is
   redefined within each player as z(leverage) + 2 x z(match-level opponent strength), so
   top-leverage points come from strong opponents by construction, with covariate effects x3. The
   raw score must come out biased (more than 3 SE from its no-confound value) and A and B must
   not. The first version of this scenario made the induced confound vary within a match
   (through the role-specific opponent column of R1), which B cannot remove by design; it was
   redefined to be constant within a match.
3. R1 was added to V6 (it had only been covered by V2 and V5).
Also added, logged and not an abort rule: V7, the frozen-table entropy-clutch correlations
(ATP serve -0.0413, return +0.0164; WTA serve -0.259, return +0.196) are reproduced by the merge
code to 4 decimals.
