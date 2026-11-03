# Applications Analyses: Results

Results of the three analyses pre-registered in
`docs/combined/applications_preregistration.md` (committed 2026-11-03 before
any script existed). Produced by one run of
`src/robustness/applications_analyses.py` on the same local MCP pulls behind
every other documented result. Machine-readable outputs:
`results/applications/`.

## Sanity checks

| Check | ATP | WTA |
|---|---|---|
| Points processed (vs documented) | 1,132,053 (= documented) | 426,269 |
| Serve clutch reliability reproduces doc (±0.005) | 0.5720 vs 0.572, PASS | 0.5784 vs 0.578, PASS |
| Return clutch reliability reproduces doc | 0.2313 vs 0.231, PASS | 0.0547 vs 0.055, PASS |
| Entropy reliability reproduces doc | 0.9253 vs 0.925, PASS | 0.8965 vs 0.897 (`wta_README.md`), PASS |
| Pooled LR = pipeline `blr_combined` | max diff 0, PASS | max diff 7e-16, PASS |
| Bootstrap identity replicate = point estimates | max diff 4e-16, PASS | max diff 2e-16, PASS |
| Bootstrap mean within ±0.002 of estimate | **flag, see below** | **flag, see below** |

(The pre-registration listed no single WTA entropy figure to check against;
the 0.897 in `wta_README.md` was found afterwards and matches.)

---

## Analysis 1: BLR reliability

Spearman-Brown full-length reliability, 95% CI from Fisher z on the
split-half r. n = 91 ATP, 55 WTA (no player excluded by the floor).

| Measure | ATP | WTA |
|---|---|---|
| Serve clutch (quartile) | 0.572 [0.350, 0.718] | 0.578 [0.274, 0.755] |
| Return clutch (quartile) | 0.231 [−0.167, 0.494] | 0.055 [−0.628, 0.451] |
| **BLR, faithful (mean of serve-LR and return-LR)** | **0.460 [0.180, 0.645]** | **0.206 [−0.368, 0.539]** |
| Pooled LR (this repo's `blr_combined`) | 0.683 [0.519, 0.791] | 0.443 [0.040, 0.676] |
| LR serve | 0.500 | 0.557 |
| LR return | 0.320 | −0.092 |

**Pre-registered verdict: ATP BLR = 0.460 falls in the "< 0.50" band, so the
claim is strengthened**: Tennis Abstract's published metric, aggregated over
a whole charted career, is poorly reliable. WTA BLR (0.206) is worse.

Two further observations:

- **Pooling serve and return inflates apparent reliability** (ATP 0.683 vs
  0.460). The pooled ratio mixes in how a player's points split between
  serve and return, which is stable from half to half but is not clutch.
  The published, "balanced" definition removes that, and what is left is
  much less stable.
- **Convergent validity, corrected.** The r = 0.793 previously reported as
  "correlation with BLR" is with the pooled LR. Against the faithful BLR, our
  combined quartile clutch score correlates **0.902 (ATP)** and **0.866
  (WTA)**: our construction tracks the published metric more closely than
  previously stated. Faithful BLR vs pooled LR: 0.716 ATP, 0.923 WTA.

Tennis Abstract reports BLR per match; this analysis covers career
aggregates only. A single match has far fewer points, so per-match BLR can
only be less reliable. No per-match figure was computed.

---

## Analysis 2: How much data a reliable clutch score needs

Projection, not a test. Median charted matches per qualified player: ATP 74,
WTA 64.

**Primary (Spearman-Brown prophecy).** Data multiple k, and matches ≈ k × median.

| Measure | ATP rel. | to 0.70 | to 0.80 | WTA rel. | to 0.70 | to 0.80 |
|---|---|---|---|---|---|---|
| Serve clutch (quartile) | 0.572 | ×1.7, ~129 | ×3.0, ~221 | 0.578 | ×1.7, ~109 | ×2.9, ~187 |
| Return clutch (quartile) | 0.231 | ×7.8, ~575 | ×13.3, ~985 | 0.055 | ×40, ~2,566 | ×69, ~4,399 |
| Serve clutch (shrinkage) | 0.594 | ×1.6, ~118 | ×2.7, ~202 | 0.624 | ×1.4, ~90 | ×2.4, ~154 |
| Return clutch (shrinkage) | 0.371 | ×4.0, ~293 | ×6.8, ~502 | 0.132 | ×15, ~982 | ×26, ~1,683 |
| BLR (faithful) | 0.460 | ×2.7, ~203 | ×4.7, ~347 | 0.206 | ×9.0, ~577 | ×15.5, ~989 |

For scale: the most-charted ATP player (Federer) has 723 matches; the
median qualified player has 74. Only one player in either pool has enough
charted matches for a return clutch score to reach 0.70 by the primary
projection.

**Secondary (per-player reliability under the shrinkage model).**

| | ATP serve | ATP return | WTA serve | WTA return |
|---|---|---|---|---|
| Median player reliability | 0.59 | 0.32 | 0.45 | 0.28 |
| Share of players ≥ 0.70 | 31% | 3% | 4% | 0% |
| Matches needed for 0.70 | ~120 | ~374 | ~184 | ~377 |

**Pre-registered consistency check (agree within 3×):** ATP serve 1.07,
ATP return 1.54, WTA serve 1.69, pass. **WTA return 6.8, fail.** As
committed, both figures are reported, with the reason:

- First hypothesis tested and **rejected**: that points within a match are
  correlated (shared opponent, conditions), so the shrinkage model's
  coin-flip variance underestimates real noise. The match-level bootstrap
  shows real sampling variance is only ~6–9% above the coin-flip value
  (median design effect 1.06–1.09 across all four tour/role cells), far too
  little to explain a 7× gap. Using the bootstrap variance instead gives
  model-based reliability 0.57 / 0.25 (ATP serve/return) and 0.43 / 0.27
  (WTA), essentially unchanged.
- Explanation: **the WTA return split-half estimate is itself very
  imprecise.** With 55 players its 95% CI runs from −0.63 to 0.45; the
  model-based value (~0.27) lies well inside it. The prophecy formula is
  extremely sensitive near zero (0.055 → ×40; 0.27 → ×6), so a small,
  imprecise reliability produces a huge, unstable projection.
- What the paper says: WTA return clutch needs somewhere between ~380 and
  ~2,600 charted matches to reach 0.70. Either end is several times more
  than any WTA player has.

---

## Analysis 3: Uncertainty on players' scores and ranks

Player-cluster bootstrap, B = 2,000, seed 20261103.

| | ATP serve | ATP return | ATP BLR | WTA serve | WTA return | WTA BLR |
|---|---|---|---|---|---|---|
| Players | 91 | 91 | 91 | 55 | 55 | 55 |
| Median width of 95% rank interval | 50 | 62 | 56 | 36 | 39 | 40 |
| Players whose interval excludes pool mean | 22 | 10 | 19 | 7 | 6 | 8 |
| Top-10 (by estimate) whose interval stays in top 20 | 1 | 0 | 1 | 2 | 1 | 0 |

A typical player's 95% interval covers more than half the ranking. Of the
players a leaderboard would put in the top 10, almost none can be placed in
the top 20 with confidence.

**Named players (ATP).** Rank 1 = most clutch, of 91.

| Player | Serve clutch rank [95%] | Return clutch rank [95%] | BLR rank [95%] |
|---|---|---|---|
| Carlos Alcaraz | 50 [27–74] | 32 [15–66] | 48 [25–76] |
| Jannik Sinner | 56 [36–77] | 57 [31–80] | 68 [40–82] |
| Novak Djokovic | 72 [53–80] | 78 [52–84] | 83 [63–86] |
| Roger Federer | 64 [47–74] | 86 [63–86] | 81 [62–86] |

Alcaraz ranks above Sinner on every measure, as the "flair" story
predicts, but every pair of intervals overlaps heavily; the data cannot
separate them.

**Observation, not tested (flag for Discussion).** The most dominant
players (Djokovic, Federer; Swiatek on WTA: return rank 51 [35–54] and BLR
52 [41–54] of 55) sit near the *bottom* of the clutch rankings, with
intervals that exclude the pool mean. One possible reason: high-leverage
points occur mostly in close matches, which for a dominant player are
disproportionately against strong opponents, while their low-leverage
points come in routine wins. If so, the clutch score partly measures
opponent mix, not pressure performance. This was not pre-registered and is
not tested here; it is reported as a possible validity problem.

**Bootstrap bias flag (pre-registered threshold ±0.002).** Breached by a
minority of players on the quartile clutch scores (ATP: 36 serve, 34 return
of 91; max 0.009), not by BLR (max 0.002). Across players the bias averages
out (median +0.0003 / −0.0004 ATP) and its typical size (median |bias|
0.0014) is ~4% of a typical interval half-width (~0.035). Likely cause:
leverage is heavily tied at identical score states, so resampling moves
tied clusters across the quartile boundary. Intervals are reported as
computed, uncorrected.

## Deviations log

None from the pre-registered procedures. One post-hoc diagnostic was added
to explain the failed WTA-return consistency check (bootstrap-based design
effect, above), and one untested observation is recorded (dominant players
ranking low); both are labelled as such.
