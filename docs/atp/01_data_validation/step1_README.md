# Step 1: Data Validation

## Update: hitter-attribution bug found and fixed (see step2_README.md / src/core/parsing.py)

The original `step1_validation.py` had a hitter-attribution bug: it
assumed the first parsed shot in a rally was the serve (hit by the
server). It's actually the return of serve (hit by the returner); the
serve itself is coded as a digit, not a letter, so the parser never saw it
as a token at all. This inverted every per-player shot attribution in the
sparsity check below.

This did not affect this step's actual deliverable
(`qualified_player_pool_min40.csv`), which is built from match counts, not
shot-level attribution, confirmed byte-for-byte identical before and after
the fix. It did affect the per-player sparsity numbers in this README,
which have been corrected below.

`step1_validation.py` has been rebuilt to import shared, tested logic from
`src/core/parsing.py` (including the fix and a standing regression guard,
`verify_hitter_parity()`) rather than duplicating notation-parsing logic
inline. Full writeup of the bug and how it was found: `step2_README.md`.

## Purpose in the pipeline
Confirms the Match Charting Project (MCP) data is usable as the foundation for the
shot-selection entropy calculation, and defines *which players* are eligible to enter
that calculation. This step exists to catch data-quality problems (missing notation,
sparse cells) before building the entropy pipeline itself, and to lock in a defensible
player-inclusion rule before the analysis scales to 30-50 players.

## Files in this step
`step1_validation.py` is the validation script. It pulls MCP match and
point data, checks shot-notation completeness, parses shot-type/direction
tokens, and runs a per-player sparsity check on the shot-type ×
court-direction grid. It also defines `get_qualified_player_pool()`, a
reusable function for filtering players by charted-match count, and now
imports shared parsing/scoring logic from `src/core/parsing.py`.

`qualified_player_pool_min40.csv` is the output of
`get_qualified_player_pool()`: 91 players with ≥40 charted matches, sorted
by coverage (Federer 723 → Nakashima 40). This is the definitive player
pool for the entire project; every later step (entropy calc, clutch score,
regression) should draw its players from this file, not from the raw MCP
data directly. Unaffected by the bug fix above.

## Data sources
Repository: https://github.com/JeffSackmann/tennis_MatchChartingProject

Raw files pulled directly via `raw.githubusercontent.com`, no manual
download needed, re-fetched fresh at the start of each run:
- Match metadata: https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-matches.csv
- Points (2020s): https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-2020s.csv
- Points (2010s): https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-2010s.csv
- Points (pre-2010): https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-points-to-2009.csv

Notes:
- Women's matches use the same file pattern with `charting-w-` instead of
  `charting-m-`, if scope ever expands.
- Points data is split by decade; a full career pull (not just 2020s)
  requires concatenating all three points files. Step 2's full-pool driver
  now does this (all three decades loaded, 1,284,276 total points rows
  processed for the 91-player pool).
- The repo is updated periodically (~every 100 new charted matches);
  re-pulling at the start of each step picks up the latest coverage, so
  match counts may tick up slightly step to step.
- License: CC BY-NC-SA 4.0. Cite the Match Charting Project properly in
  the SSAC paper.

## Key decisions made in this step
1. **Player eligibility threshold: ≥40 charted matches.** Chosen because it's the point
   at which forehand/backhand × direction cells stay reliably populated (>1,000 obs each),
   even for the weakest-qualifying player (Nakashima, tested as the boundary case).
   **Confirmed at full-pool scale in Step 2:** running the actual entropy/pressure
   pipeline against all 91 players showed 100% of the pool clears the MIN_OBS=30 floor
   for pooled entropy, transition entropy, dropshot rate, serve zone, net-play, and
   return depth: this threshold was well-calibrated.
2. **Entropy calc uses forehand/backhand × 3 court-directions only (6 cells).** Lob and
   "other" (halfvolley/overhead) categories are excluded, tested at both a thin-coverage
   player (Draper, 29 matches, below threshold) and the boundary case (Nakashima, 40
   matches) and stayed sparse (single digits to low 20s) regardless of match count. This
   confirms it's genuine shot rarity, not a coverage artifact, so more data wouldn't fix it.
3. **No supplementary data sources.** MCP is confirmed as the only public shot-by-shot
   tennis dataset; other "datasets" found online are derived from MCP itself. Selection
   bias (charted matches skew toward popular/high-leverage matches) is a real, documented
   limitation of the source and should be named explicitly in the paper's limitations
   section: not something to work around.

## Sanity checks run (CORRECTED post-bug-fix numbers)

**Sinner: 81,338 usable shot tokens.** All 6 core cells robust (10,911-18,334
obs each).
```
direction    1      2      3
backhand   5853  16037  18334
forehand  15273  13935  10911
lob         130    314    187
other       198     70     96
```

**Alcaraz: 61,029 usable shot tokens.** All 6 core cells robust (4,645-14,892
obs each).
```
direction    1     2      3
backhand   4645  9403  14892
forehand  12523  8954   9152
lob         160   424    380
other       188   101    207
```

**Draper (29 matches, below threshold): 7,953 usable shot tokens.** Core
fh/bh cells fine; lob/other sparse as expected (this is the stress test for
"is exclusion of lob/other justified", confirmed yes):
```
[warning] Cells below 30 obs: lob-dir1 (15), lob-dir3 (19), other-dir1 (12),
          other-dir2 (8), other-dir3 (5)
[warning] Cells below 10 obs (high sparsity risk): other-dir2 (8), other-dir3 (5)
```

**Nakashima (40 matches, exactly at threshold): 11,704 usable shot tokens.**
Core fh/bh cells robust (796-2,464 obs each), confirming the 40-match cutoff
is safe for the full pool. Lob/other still sparse at exactly the threshold:
```
[warning] Cells below 30 obs: lob-dir1 (27), other-dir1 (28), other-dir2 (12)
```

The qualitative conclusions from the original (pre-fix) sanity check
(core forehand/backhand cells are robust for all four players, lob/other is
genuinely sparse regardless of match count) held up under the fix. Only the
exact per-cell counts changed.

## Feeds into Step 2
Step 2 (entropy pipeline build) should:
- Load players from `qualified_player_pool_min40.csv`, not from `charting-m-matches.csv` directly.
- Reuse the coarse shot-type mapping (forehand/backhand only, 3 directions) established here.
- Re-run the Sinner/Alcaraz sanity check as the first pipeline validation.
- **(Now done)** Import all shared parsing/scoring logic from `src/core/parsing.py`
  rather than re-deriving it, see that module's own docstring
  and `step2_README.md`'s bug-fix section for why.
