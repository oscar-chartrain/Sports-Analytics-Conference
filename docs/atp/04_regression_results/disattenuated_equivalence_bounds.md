# Disattenuated Equivalence Bounds: Method and Results

## Method and reporting commitment

Written before computing a single disattenuated bound. This document
differs in kind from the other pre-registration docs in this project:
it is not a new empirical hypothesis test on previously-unexamined data,
it is a deterministic recalculation applied to numbers already
established and already reported elsewhere (the TOST equivalence bounds
in `step4_results_writeup.md` and `pooled_regression.md`, and the
split-half and shrinkage reliability figures in
`split_half_reliability.md` and `shrinkage_reliability.md`). There is no
cherry-picking risk in the usual sense, the inputs are fixed and the
transformation is arithmetic, but the same discipline applies: what
gets reported is committed to before running, including any
uncomfortable result.

### Why this check

A cold-read review of `paper/abstract.md` raised a specific, valid
objection: once serve clutch reliability (0.57-0.58) is honestly labeled
sub-threshold alongside return clutch, there is no longer a
reliability-clean side of the null result left to lean on, and the
abstract's TOST bound ("|r| < 0.21") is stated on the *observed-score*
scale, not corrected for the fact that neither the predictor nor the
outcome is measured with perfect reliability. Classical test theory's
attenuation correction (already used descriptively in
`split_half_reliability.md`, and always with a strong caveat about
noise amplification at low reliability) can be applied to a *bound*, not
just a point estimate, in a way that is more defensible than correcting
a single noisy sample correlation: dividing an already-established
equivalence bound by the attenuation factor gives the equivalent bound
on the *true-score* scale, i.e. "how large could the real relationship
be, if both variables were measured perfectly."

### The calculation

For a given tour and role, let `B_obs` be the tightest symmetric bound
`(-B, B)` for which TOST equivalence holds at alpha = 0.05 on the
observed data (found by binary search using
`stats_helpers.tost_equivalence()`, unmodified, called repeatedly rather
than hand-deriving a new formula). The disattenuated (true-score) bound
is:

```
B_true = B_obs / sqrt(reliability_predictor * reliability_outcome)
```

using the already-documented Spearman-Brown-corrected reliabilities.
This is computed twice per tour/role: once using the original quartile
clutch score's reliability, once using the shrinkage-corrected
reliability from `shrinkage_reliability.md`, to show whether the partial
reliability fix changes the disattenuated picture.

### Scope decision, fixed before running

This check is scoped to ATP-only and WTA-only bounds. It does **not**
compute a disattenuated bound for the pooled (n=146) test, because
reliability was estimated separately per tour, not for the pooled
sample, and there is no principled, already-validated way in this
project to combine two tours' reliability estimates into one pooled
reliability figure without inventing a new, undisclosed method. Rather
than construct one ad hoc for this check, pooled disattenuation is left
out of scope.

### Commitment (fixed before running)

1. ATP's two recomputed observed-score bounds will be checked against
   the already-documented figures (serve < 0.213, return < 0.189) before
   any new number is trusted. If they do not match closely, that is
   reported as a discrepancy to resolve, not silently reconciled.
2. WTA's observed-score bounds have never been computed before in this
   project (only ATP-only and pooled bounds exist in `docs/`); the
   values found here will be reported as new, not retrofitted to match
   any prior expectation.
3. All 4 tour/role combinations, at both reliability versions (8
   disattenuated bounds total), will be reported in one table,
   regardless of outcome, including any bound that exceeds 1 (which
   would mean the disattenuated equivalence claim is vacuous, providing
   no real information about the true-score relationship, since a
   correlation cannot exceed 1 in magnitude).
4. This calculation treats the reliability point estimates as fixed and
   known. It does not propagate the reliability estimates' own sampling
   uncertainty (they too come from a finite pool of 91/55 players) into
   the disattenuated bound. This is a real limitation, named here before
   seeing results, not after.
5. This document will not be edited after seeing the computed values.

## Results

Written after running `src/robustness/disattenuated_equivalence_bounds.py` exactly
as specified above.

### Cross-check (commitment #1)

The recomputed ATP bounds, found by binary search on the real per-player
data rather than transcribed by hand, match the documented figures
exactly: serve 0.2134 vs. documented 0.213 (diff 0.0004), return 0.1894
vs. documented 0.189 (diff 0.0004). The method is trusted on this basis.

### WTA observed-score bounds (new; commitment #2)

Never computed before in this project. WTA serve: |r| < 0.457. WTA
return: |r| < 0.403. Both are far looser than ATP's bounds, reflecting
WTA's smaller pool (55 vs. 91) and, for serve, its closer-to-conventional-
significance point estimate (r = -0.259, p = 0.056). This was true before
any disattenuation was applied, and is worth stating plainly on its own:
the WTA-only equivalence claims were always weaker than ATP's, even on
the observed-score scale.

### Disattenuated (true-score) bounds, all 8, per commitment #3

| Tour | Role | Reliability version | Attenuation factor | B_obs | B_true |
|---|---|---|---|---|---|
| ATP | Serve | quartile | 0.727 | 0.213 | 0.293 |
| ATP | Serve | shrinkage | 0.741 | 0.213 | 0.288 |
| ATP | Return | quartile | 0.462 | 0.189 | 0.410 |
| ATP | Return | shrinkage | 0.586 | 0.189 | 0.323 |
| WTA | Serve | quartile | 0.720 | 0.457 | 0.635 |
| WTA | Serve | shrinkage | 0.748 | 0.457 | 0.611 |
| WTA | Return | quartile | 0.222 | 0.403 | **1.813 (vacuous)** |
| WTA | Return | shrinkage | 0.344 | 0.403 | **1.170 (vacuous)** |

### Honest verdict

**ATP's equivalence claims survive disattenuation, but the bound loosens
substantially.** Serve widens from ruling out |r| > 0.21 to ruling out
|r| > 0.29-0.29 (quartile/shrinkage), still tighter than a conventional
"medium" effect (Cohen's 0.3), a real, if less impressive, claim. Return
widens more, from 0.19 to 0.32-0.41: the shrinkage-corrected version
still rules out a "large" effect (0.5) with room to spare, but the
quartile version barely clears "medium." Disattenuation costs real
precision here, but the underlying claim, that a true relationship, if
one exists, is not large, remains intact for ATP on both roles.

**WTA serve survives, but only just, and was already the weakest
observed-score claim in the project.** The true-score bound (0.61-0.63)
only clearly rules out effects near the "large" end of conventional
benchmarks. It is a real bound, not vacuous, but it is not a strong one,
and this should be stated with that qualification rather than cited
alongside ATP's tighter numbers without distinction.

**WTA return's equivalence claim does not survive disattenuation at
all, at either reliability version.** A bound exceeding 1 is not
"weak evidence," it is no evidence: since a correlation cannot exceed 1
in magnitude by definition, a disattenuated bound above 1 means the
combination of (a) WTA return's already-loose observed-score bound and
(b) return clutch's very low reliability (0.055 quartile, 0.132 even
after shrinkage) leaves this project's data unable to rule out *any*
true-score relationship, including a very large one. This directly
answers the cold-read objection that motivated this check: for WTA
return specifically, the "no relationship" finding is not merely
inconclusive due to reliability, as `split_half_reliability.md` already
said, it is, once measurement error on both sides is properly accounted
for, uninformative about the true-score relationship in the strict
equivalence-testing sense. Shrinkage narrows the gap (1.81 -> 1.17) but
does not close it, consistent with `shrinkage_reliability.md`'s own
finding that shrinkage helps without fully solving the reliability
problem.

**This does not change the paper's primary conclusion, and sharpens
it.** The observed-score null result (entropy does not predict clutch
performance, across the leverage-weighting robustness battery) stands
exactly as reported. What this check adds is a more honest account of
*how much weight each piece of that null can bear*: ATP's null, on both
roles, remains a real, if less precisely bounded, corrective. WTA
serve's null is real but weaker than it may have appeared next to
ATP's tighter numbers. WTA return's null should not be cited as
evidence of "no relationship" in the true-score sense at all, only as
"this project's current data and methods cannot distinguish a true
relationship from noise on this specific role and tour," a materially
different and more limited claim.

### Limitation, per commitment #4

This calculation treats each reliability figure as fixed and known.
None of the reliability estimates' own sampling uncertainty (they are
themselves computed from a finite pool of 91 or 55 players) is
propagated into the disattenuated bounds above. A fully rigorous version
would carry that uncertainty through as well, likely widening every
bound in this table further, meaning the numbers above should be read
as optimistic (tightest-case) true-score bounds, not as the loosest
honest statement possible.

### How to reproduce
```
python3 src/robustness/disattenuated_equivalence_bounds.py
```
Needs only the already-committed primary feature and clutch files for
both tours; no raw MCP data or re-extraction required.
