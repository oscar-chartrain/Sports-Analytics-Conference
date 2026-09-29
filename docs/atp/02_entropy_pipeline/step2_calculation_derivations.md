# Step 2: Calculation Derivations

Every value the Step 2 pipeline computes, derived from first principles, with
a worked numeric example using Sinner's actual data. Intended as the basis for
the paper's Methods section.

---

## 1. Pooled (marginal) Shannon entropy

**What it measures:** how unpredictable a player's shot is, ignoring any
situational context. Just "what's the overall distribution of
forehand/backhand × direction for this player's career."

**Setup.** Let `C = {(forehand,1), (forehand,2), (forehand,3), (backhand,1),
(backhand,2), (backhand,3)}` be the 6 cells. Lob, halfvolley, swinging
volley, trick, and unknown shots are genuinely excluded (`wing=None` in
`mcp_common.WING_MAP`, filtered out entirely per Step 1's sparsity finding).
**Dropshots are not excluded**: they're included but folded into their
wing's forehand/backhand cell for this core grid (`WING_MAP['u'] =
'forehand'`, `WING_MAP['y'] = 'backhand'`); they only get their own separate
cells in the Section 4 extended grid below. "Lob/other excluded" in
shorthand elsewhere in this project's docs means *these five* categories,
not dropshots: worth stating precisely here since this document is the
one meant to be copied into the paper's Methods section. For a given
player, let `n_c` be the number of charted shots landing in cell `c`, and
let

```
N = Σ_{c ∈ C} n_c
```

be the player's total usable shot count.

**Step 1: convert counts to probabilities.** For each cell:

```
p_c = n_c / N
```

This is just the empirical relative frequency: the maximum-likelihood
estimate of "if I picked one of this player's shots at random, what's the
chance it's cell `c`."

**Step 2: apply the Shannon entropy formula.**

```
H = − Σ_{c ∈ C} p_c · log2(p_c)
```

with the standard convention `0 · log2(0) := 0` (cells with zero
observations contribute nothing, rather than causing `log2(0) = −∞`).

**Why this formula and not something else:** Shannon entropy is the unique
function (up to a constant) satisfying three properties that make "spread of
a distribution" meaningful here: continuity in the `p_c`, maximized when all
outcomes are equally likely, and additivity across independent choices. In
information-theoretic terms, `H` is the average number of bits needed to
communicate which cell a shot fell into, given the observed distribution. A
player whose shots always land in the same cell needs 0 bits (`H=0`,
perfectly predictable); a player who spreads shots evenly across all 6 cells
needs `log2(6)` bits (maximum unpredictability).

**Step 3: normalize.** Raw `H` is in bits and its ceiling depends on how
many cells there are, which makes it hard to compare across players or
category schemes. Divide by the maximum possible entropy for this cell count
(achieved at a perfectly uniform distribution):

```
H_max = log2(|C|) = log2(6) ≈ 2.5850 bits
H_norm = H / H_max
```

`H_norm ∈ [0,1]`: 0 = always the same cell (fully predictable), 1 = perfectly
uniform across all 6 cells (maximally unpredictable).

**Worked example, Jannik Sinner, pooled career (2020s data, post hitter-attribution-fix):**

*Note: an earlier version of this document used pre-fix numbers (total
N=80,377, H_norm=0.9766). A hitter-attribution bug was found and fixed after
this document was first written (see `step2_README.md`'s bug-fix section);
every number below reflects the corrected pipeline.*

| Cell | n_c | p_c = n_c/N |
|---|---|---|
| forehand, 1 | 15,273 | 0.19010 |
| forehand, 2 | 13,935 | 0.17342 |
| forehand, 3 | 10,911 | 0.13580 |
| backhand, 1 | 5,853 | 0.07286 |
| backhand, 2 | 16,037 | 0.19961 |
| backhand, 3 | 18,334 | 0.22822 |
| **N** | **80,343** | **1.0000** |

```
H = −(0.19010·log2 0.19010 + 0.17342·log2 0.17342 + 0.13580·log2 0.13580
     + 0.07286·log2 0.07286 + 0.19961·log2 0.19961 + 0.22822·log2 0.22822)
  ≈ 2.5106 bits

H_max = log2(6) ≈ 2.5850 bits

H_norm = 2.5106 / 2.5850 ≈ 0.9712
```

This matches the pipeline's reported value (0.9712) exactly.

---

## 2. Conditional (transition) entropy: the refined consistency measure

**What it measures:** how predictable a player's shot is **given the shot
they're reacting to** (the immediately preceding shot in the rally); this is
the measure that actually separated Sinner and Alcaraz, unlike the pooled
version above.

**Setup.** In addition to the current-shot categories `C` from Section 1,
define a context variable with 7 possible values: the 6 `(wing, direction)`
cells (for when the preceding shot was a directional forehand/backhand) plus
one catch-all `other` bucket (serve, lob, halfvolley, or missing-direction
predecessor). Call this context space `Ctx`.

For every (context, current) pair observed, let `n(k, c)` be the count of
transitions where the context was `k ∈ Ctx` and the current shot landed in
cell `c ∈ C`. Let:

```
N_k = Σ_{c ∈ C} n(k, c)      (total transitions with context k)
N   = Σ_{k ∈ Ctx} N_k        (total transitions, all contexts)
```

**Step 1: the conditional distribution for a single context.** Fix a
context `k`. The distribution of the CURRENT shot, given we're in context
`k`, is:

```
P(c | k) = n(k, c) / N_k
```

**Step 2: entropy of that conditional distribution.** Apply the same
Shannon formula as Section 1, but restricted to transitions with context `k`:

```
H(X | K=k) = − Σ_{c ∈ C} P(c | k) · log2( P(c | k) )
```

This is "how unpredictable is the current shot, once we already know what
the preceding shot was."

**Step 3: average over all contexts, weighted by how often each occurs.**
The context itself has a distribution too:

```
P(k) = N_k / N
```

The **conditional entropy** is the expectation of `H(X | K=k)` over that
distribution:

```
H(X | K) = Σ_{k ∈ Ctx} P(k) · H(X | K=k)
```

This is a weighted average: contexts that occur more often (higher `P(k)`)
count for more in the final number, but every context's *own* internal
predictability is what's being averaged, not the raw pooled counts across
contexts. This is the key mathematical difference from Section 1's marginal
entropy: marginal entropy asks "what's the shape of the whole distribution,"
conditional entropy asks "how much does that shape narrow down once you
know the situation, and then average that narrowing across situations."

**Normalization** works the same way as Section 1 (divide by `log2(6)`,
since the current-shot space `C` still has 6 categories regardless of
context).

**Step 4: marginal entropy on the same transition dataset**, for a fair
comparison. This is Section 1's formula, but computed on `n(k,c)` summed
over `k` rather than the full career shot log, so the "before context" and
"after context" numbers are on an apples-to-apples subset:

```
n_c = Σ_{k ∈ Ctx} n(k, c)          (marginal count, ignoring context)
H(X) = − Σ_{c ∈ C} (n_c/N) · log2(n_c/N)
```

---

## 3. Information gain (mutual information)

**What it measures:** how much of a player's shot-selection uncertainty is
"explained away" by knowing the preceding shot, i.e., how context-dependent
their shot choice is.

**Derivation.** By definition:

```
Information gain = H(X) − H(X | K)
```

This quantity has a name in information theory: it is exactly the **mutual
information** `I(X; K)` between the current shot and the context, which can
equivalently be written as:

```
I(X; K) = Σ_{k,c} P(k,c) · log2( P(k,c) / (P(k)·P(c)) )
```

where `P(k,c) = n(k,c)/N`. The two formulas are mathematically identical:
`H(X) − H(X|K) = I(X;K)` is a standard identity (it follows directly from
expanding both sides using `H(X,K) = H(K) + H(X|K)` and `H(X,K) = H(X) +
H(K|X)`). The pipeline uses the entropy-difference form because it's more
directly interpretable here ("how much did conditioning reduce the
uncertainty"), but citing it as mutual information in the paper is accurate
and standard.

**Properties that justify using it:** `I(X;K) ≥ 0` always (conditioning
can never *increase* average uncertainty; this is a theorem, not an
assumption), and `I(X;K) = 0` exactly when the current shot is statistically
independent of the context (knowing the preceding shot tells you nothing
about the next one).

**Relative information gain**, used for the "% reduction from marginal"
figures reported:

```
Relative info gain = I(X;K) / H(X)
```

This rescales to a proportion (0 to 1) of the player's *total* marginal
uncertainty that gets explained by context, which is what allows comparing
"how context-dependent is Sinner" vs. "how context-dependent is Alcaraz" as
percentages rather than raw bits.

**Worked example, Sinner (post hitter-attribution-fix, from the pipeline run):**

```
H(X)     = 2.5081 bits   (marginal, on the transitions dataset)
H(X | K) = 2.0475 bits   (conditional)

I(X;K) = H(X) − H(X|K) = 2.5081 − 2.0475 = 0.4605 bits

Relative info gain = 0.4605 / 2.5081 ≈ 0.1836  →  18.4%
```

---

## 4. Extended (dropshot) entropy grid: same formula, different `C`

The dropshot-inclusive check uses the identical Section 1 formula, just with
`C` redefined as 9 cells: `{forehand, backhand, dropshot} × {1, 2, 3}`. No new
mathematics; only the category set changes, which also changes the ceiling:

```
H_max = log2(9) ≈ 3.1699 bits
```

(Not currently used as the primary entropy variable, pending the
per-player minimum-observation floor noted in the README, but the formula
is ready to go once that floor is set.)

---

## 5. Rates and proportions (serve zone, net-play, return depth)

These are **not entropy calculations**: they're simple conditional relative
frequencies, the same `p_c = n_c/N` step from Section 1's "Step 1," just
without the entropy formula applied on top. For completeness, since the
pipeline reports several of them:

**Serve-zone distribution at a given pressure level `s`:**

```
P(direction = d | situation = s) = (count of serves with direction d AND situation s)
                                    / (total serves with situation s)
```

reported separately for `d ∈ {4 (wide), 5 (body), 6 (T)}` at each pressure
level `s ∈ {normal, approaching_break_point, break_point, set_point,
match_point}`.

**Net-play / serve-and-volley rate**, for a given pressure bucket `b`
(`normal` or `high-pressure composite`):

```
Net-play rate  = (# points in bucket b where went_to_net = True) / (# points in bucket b)
Pure SnV rate  = (# points in bucket b where is_snv = True)      / (# points in bucket b)
```

Both are simple binomial proportions (a mean of an indicator variable), not
entropy.

**Return-depth distribution**, same structure as serve zone:

```
P(depth = d | situation = s) = (# returns with depth d AND situation s) / (# returns with situation s)
```

for `d ∈ {7 (shallow), 8 (mid), 9 (deep)}`.

**This distributional form is what the Sinner/Alcaraz sanity-check report
prints (the "26.0%→35.8% shallow" style percentages), but it is not what
feeds the regression-ready feature CSV.** `features.reduce_pressure_features()`
(in `src/core/features.py`) instead collapses the 3-way distribution to a single continuous number per
pressure bucket, via an ordinal encoding:

```
depth_scale(d) = 1 if d=7 (shallow), 2 if d=8 (mid), 3 if d=9 (deep)
mean_depth(situation = s) = mean over all returns in situation s of depth_scale(d)
return_depth_shift_delta = mean_depth(high-pressure) − mean_depth(normal)
```

This is `mean_return_depth_normal` / `mean_return_depth_high_pressure` /
`return_depth_shift_delta` in `step2_full_pool_features.csv`: the actual
columns available to Step 3/4's regression (`return_depth_shift_delta` is
listed as a secondary/exploratory predictor in
`step3_variable_preregistration.md`). It was missing from this document
entirely until this coherence review found the gap: only the descriptive
proportion form above had been written down, not the regression-ready
reduction actually used downstream. The ordinal encoding treats
shallow/mid/deep as equally spaced, which is a simplifying assumption (not
verified against, say, actual court-distance measurements) worth naming
explicitly if this variable is cited in the paper as more than an
exploratory control.

---

## 6. Pressure/situation classification: logical derivation, not a formula

The base situation, set point, and match point labels aren't statistical
calculations: they're a deterministic classification derived from the raw
score. Included here for completeness since they gate every rate/proportion
in Section 5.

**Score encoding:** `SCORE_MAP = {0→0, 15→1, 30→2, 40→3, AD→4}`, giving the
server's score `s` and returner's score `r` on this integer scale (from
`Pts` + `Svr`).

**Base situation** (mutually exclusive, checked in this order):
```
r = 4                          → break_point
s = 4                          → game_point_server
r = 3 and s < 3                → break_point
s = 3 and r < 3                → game_point_server
s = 3 and r = 3                → deuce
r + 1 = 3 and s < 3             → approaching_break_point   (would-be break point)
otherwise                      → normal
```

**Set point**, layered on top: let `g_server`, `g_returner` be current games
won in the set. Server has a set point if `situation = game_point_server` AND

```
(g_server + 1) ≥ 6   and   (g_server + 1) − g_returner ≥ 2
```

(the standard tennis set-win condition, 6+ games with a 2-game margin, with
no upper bound, so it also correctly covers advantage sets that run past
6-6). Returner's set point is the mirror condition under `break_point`.

**Match point**, layered on top of set point: let `sets_to_win = ⌈best_of /
2⌉` (2 for best-of-3, 3 for best-of-5, excluded/`None` if `Best of` is
unparseable in the source data). Server has match point if they have a set
point AND `(sets_won_by_server + 1) = sets_to_win`; mirror for returner.

**Tiebreak points** use the same set/match-point logic but on the raw
tiebreak point score (`parse_tiebreak_score`) against a target of 7 (standard)
or 10 (only for `Final TB?` codes `'A'`/`'S'`, the super-tiebreak formats),
again with a 2-point margin requirement.

**High-pressure composite:**
```
is_high_pressure = (situation ∈ {break_point, game_point_server, deuce,
                                   approaching_break_point})
                    OR set_point_server OR set_point_returner
                    OR match_point_server OR match_point_returner
```
a logical OR, not a weighted or probabilistic combination.
