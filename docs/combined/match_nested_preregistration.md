# Pre-registration: a match-nested variance model of clutch

Written 2026-11-17, before `src/robustness/match_nested_variance.py` was run. Self-registered,
and written after all earlier results were known (see `preregistration_timeline.md`),
including the multilevel and clustered estimates (Table S6) that this plan extends. No result
of this analysis had been seen when this was written; the code was only syntax-checked.

## Why

The multilevel model of Section 6.1 gave each player a random intercept and slope but could not
add a random effect for match within player (it did not converge in reasonable time on the point
data), so its likelihood-ratio test ignored that points within a match are correlated. This
plan fits a three-level model on data aggregated to player-matches, which is fast and keeps the
match level explicit.

## Model

For player p and match i, the per-match clutch score (top-quartile rate minus bottom-quartile
rate, in percentage points; quartile thresholds are the player's full-sample values, as in the
paper) is

    d_pi = mu + u_p + w_pi + e_pi,   u_p ~ N(0, tau_p^2),  w_pi ~ N(0, tau_m^2),  e_pi ~ N(0, v_pi)

with tau_p^2 the stable between-player variance of true clutch, tau_m^2 the match-to-match
variance of a player's true clutch around their own level, and v_pi the known sampling variance
of the match score, v_pi = pt(1-pt)/n_t + pb(1-pb)/n_b with pt, pb the player's own pooled
top- and bottom-quartile rates (not the match's own, which are unstable at a few points) and
n_t, n_b the match's point counts in the two buckets. A match enters only if both buckets hold
at least 3 points (primary; sensitivity at 1 and 5, point estimates only). Outcomes: S serve
clutch, Rt return clutch, R1 rally-decided point clutch. R2 and R3 are ratio outcomes with no
simple per-match binomial variance and are not run.

Estimation: maximum likelihood on the marginal likelihood of each player's match vector
(covariance diag(tau_m^2 + v_pi) + tau_p^2 11'), with mu, tau_p^2 and tau_m^2 free; several
starting values, the best kept. Intervals: 1,000 player-bootstrap refits (95% percentile).

## Reported

- tau_p, tau_m and the mean sampling SD of one match score (pp), with 95% intervals.
- Reliability of a career-length score under the model: tau_p^2 / (tau_p^2 + mean over players
  of 1 / sum_i 1/(tau_m^2 + v_pi)), the error variance being that of the player's
  inverse-variance-weighted mean. Also at the median charted-match count of the tour for a
  common reference.
- Matches needed for reliability 0.70 under the model: (0.70/0.30) x (tau_m^2 + mean v) / tau_p^2.
- Likelihood-ratio tests with the 50:50 chi-square(0,1) mixture for tau_p^2 = 0 (stable
  differences, now with match-level variance in the model) and for tau_m^2 = 0 (real
  match-to-match variation in clutch).
- How many matches and players are kept at each minimum.

## Validation (script aborts if it fails)

Parametric simulation: data with the observed design (each player's number of matches and v_pi)
and known tau_p = 1.5 pp, tau_m = 3.0 pp, 200 replicates for each of ATP serve and WTA serve.
The mean estimated tau_p and tau_m must each fall within 15% of the truth. A second simulation
with tau_m = 0 must give a mean tau_m below 1.0 pp.

## Interpretation, fixed in advance

If the model's career-length reliability is below 0.70 and the matches needed exceed the
median charted-match count of the tour, the paper reports that the nested model confirms the
earlier estimates. If tau_m is large relative to tau_p, the paper reports that most
non-sampling variation is match-to-match, which is a further reason a short sample is
uninformative. No estimator or threshold is changed after seeing results. If the match scores'
normal approximation is poor at the 3-point minimum, the 5-point sensitivity is the check.

## Not done

No point-level nested model (the earlier one was infeasible), no covariates (surface, opponent,
era), no R2 or R3, and no correction for the correlation between a match's top and bottom
buckets beyond treating them as independent.

## Deviation recorded 2026-11-17 (after a first run)

The first run used maximum likelihood as written above. Its ATP results had been produced and
seen (for example ATP serve tau_p 1.96 pp, tau_m 3.58 pp; ATP return tau_p 0.47 pp) when the
validation simulation on the WTA design failed the pre-registered rule: mean estimated tau_m
at true tau_m = 0 was 1.05 pp (limit 1.0), and with true tau_p 1.5 and tau_m 3.0 the means were
1.32 and 2.64, about 12% low, the usual small-sample downward bias of maximum likelihood with
55 players. The script aborted before any WTA result was produced. Estimation was changed to
restricted maximum likelihood (REML), the standard remedy, with the validation rules unchanged,
and everything was rerun. The likelihood-ratio tests are REML tests of variance components with
the same fixed effect. The switch was prompted by the simulation, not by a WTA result, but the
ATP maximum-likelihood results were known when it was made.

## Second deviation recorded 2026-11-17 (WTA failed validation under REML as well)

Under REML the WTA simulation again failed the unchanged rule: with true tau_p = 1.5 and
tau_m = 3.0 the means were 1.38 and 2.64 (both within 15%), but at true tau_m = 0 the mean
estimate was 1.05 pp (limit 1.0), a positive value that arises because an estimated variance
cannot go below zero. The rule was not relaxed. Instead, the script now records a tour's
validation result (`results/applications/match_nested_validation.csv`) and reports no fits for
a tour that fails; the paper reports the nested model for ATP only and says WTA failed the
check. The ATP validation passed under both ML and REML.
