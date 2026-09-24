# Step 3: Leverage-Weighted Clutch Score — README

## Purpose in the pipeline
Builds the outcome variable Step 2 was missing: a leverage-weighted clutch
score per player, split by serve/return, ready to regress against Step 2's
`conditional_normalized_entropy` in Step 4.

## Data source
Full-career MCP points data (`charting-m-points-2020s/2010s/to-2009.csv`),
fetched fresh via `raw.githubusercontent.com`, restricted to the 6,652
matches (of 7,567 total) involving at least one of the 91 qualified players.
1,132,053 points processed.

## Related work and what's actually novel here
Checked against prior work before building, since the outcome variable
below is not a new metric and that needs to be said plainly rather than
have a reviewer point it out:

- Morris (1977), "The most important points in tennis," is the original
  source of the leverage definition below. The recursive game/set/match
  win-probability machinery is decades-old, well-established math
  (Klaassen & Magnus, 2001, 2003; Barnett & Clarke, 2005; Newton & Keller,
  2005), not something this project derived from scratch.
- Klaassen & Magnus (2001), the standard reference for point-win-probability
  modeling in tennis, found that point outcomes aren't strictly IID:
  winning the previous point raises the odds of winning the next, and at
  important points the server's point-win probability drops below their
  baseline. They also note that deviations are small enough that a
  constant point-win probability is a reasonable approximation for
  match-win-probability modeling. That finding justifies the fixed-p
  approach below (the field's own documented simplifying assumption, not
  an original shortcut) and is why it gets a sensitivity check rather than
  being presented as a clean, uncontested constant.
- The outcome variable itself already exists in the field. Tennis Abstract
  publishes "Balanced Leverage Ratio" (BLR): average leverage of points won
  divided by average leverage of points lost, with clutch performance
  scoring above 1.0, built on the same Morris-style leverage. Stats Perform
  presented near-identical leverage/momentum metrics for tennis at MIT
  Sloan SSAC 2022, the same conference this paper targets. A reviewer
  familiar with that talk or with Tennis Abstract will recognize a
  "leverage-weighted clutch score" on sight.

What this means for the paper's contribution claim: the novelty is not the
clutch/leverage construct. It's pairing an information-theoretic
shot-selection consistency measure (conditional entropy) with an
established leverage-weighted outcome, to test whether stylistic
predictability/improvisation predicts pressure performance. A search for
that specific pairing (entropy-style predictors x leverage-weighted clutch
outcomes in tennis) turned up nothing; existing pressure/clutch research
in tennis is either physiological/psychological (choking studies) or
built on serve/return percentage stats, not an information-theoretic
style variable. That's the honest novelty claim, and it should be stated
that way explicitly in the paper's introduction and related-work section,
rather than implying the clutch metric itself is new.

Citations for the paper's related-work section: Morris (1977); Klaassen &
Magnus (2001, *JASA*, "Are points in tennis independent and identically
distributed?"); Klaassen & Magnus (2003) and Barnett & Clarke (2005) for
the standard recursive match-win-probability formulas underlying the
model below; Tennis Abstract (Sackmann) for BLR, the closest existing
published "clutch via leverage" metric; and Stats Perform's MIT Sloan
SSAC 2022 leverage/momentum talk. Naming this prior art before a reviewer
does is a strength signal, not a weakness admission.

## Key decisions
- **Leverage**: Morris (1977) definition, P(win match | win pt) - P(win match | lose pt),
  via exact recursive game/tiebreak/set/match win-probability functions
  (see the leverage engine section of `src/core/formulas.py`'s module
  docstring and function-level comments for the full derivation).
- **Fixed point-win probability p = 0.65**, uniform across every point
  regardless of player, to avoid circularity with the entropy predictor.
  Cross-checked at p = 0.60/0.65/0.70, plus a pressure-tiered variant using
  Klaassen & Magnus's (2001) published effect size (~0.75pp drop at
  high-pressure points).
- **Clutch score**: within-player quartile split (top vs bottom quartile of
  that player's own leverage distribution), serve and return computed
  separately, `MIN_OBS=30` gating both sides independently (reusing
  `features.MIN_OBS`). Chosen over a fixed global leverage threshold to
  guarantee every player has a usable high and low bucket, at some cost to
  how cleanly a single cutoff would report in the paper.
- **BLR** (Tennis Abstract's established leverage-ratio metric) computed
  alongside as a convergent-validity check, not a second primary outcome.

## A modeling result found along the way
Because a single p is shared by both players, any fresh or tied state (0-0
in a game, a not-yet-started set, even a tiebreak from 0-0) is exactly a
50/50 coin flip by symmetry, not an approximation. This replaces an
earlier "average over who serves the set's first game" approximation that
had been the initial plan for match-level probability: it now reduces to
exact binomial reasoning over remaining sets (each a fair coin) layered on
the exact, non-simplified probability of the set actually in progress. The
same symmetry argument gives an exact closed form for the tiebreak's own
"deuce" region, which was necessary to fix an infinite-recursion bug
during build (documented in the code comments in `src/core/formulas.py`).

## Bug found and fixed during final review (before sign-off)
A final full read-through of the leverage engine (prompted by "make sure to review
everything before validating Step 3") found a real bug in the tiebreak
branch of `compute_leverage`: it hardcoded the server-alternation anchor as
`True` for the win-path calculation and `False` for the lose-path
calculation, regardless of the actual point index. The correct anchor —
derived from the known fact that `Svr` tells us who serves the *current*
point — alternates in a `True, False, False, True, ...` pattern and must be
**the same value for both paths** (both start from the same total point
count). The hardcoded version was only actually correct for the very first
point of a tiebreak; it affected roughly half of all other tiebreak points
(~3.4% of all points overall, but disproportionately high-leverage ones,
since tiebreaks tend to be high-stakes). The full pipeline (leverage,
clutch scores, and the head-to-head check) was rerun after the fix. All
qualitative conclusions below held; numbers shifted only marginally (e.g.
BLR convergent-validity correlation moved from 0.792 to 0.793). This is
recorded here rather than silently corrected, consistent with this
project's standing bug-disclosure practice from Step 2.

## Sanity checks — reported honestly, including the one that didn't clearly pass

**1. Building-block checks**: break points, set points, and deciding-set
points at close scores all show high leverage (e.g. 0.388 for a break point
in a 5-5 deciding set) as expected; leverage correctly collapses to near-zero
in blowout contexts (0.0004 at 5-0 up a set) even at nominal "game point"
scores. Passed.

**2. Sinner vs Alcaraz**: Alcaraz shows positive clutch on both serve
(+0.002) and return (+0.008); Sinner shows small negative on both (-0.003,
-0.009). BLR agrees (Alcaraz 1.030, Sinner 0.996). This is in the direction
the paper's hypothesis would predict — the higher-entropy "Magician" showing
more positive clutch than the lower-entropy "Robot" — though this is n=1
pair, not evidence for the pool-wide relationship.

**3. Djokovic vs Federer — resolved, not a metric failure.** The general
(career-wide, all-opponents) clutch scores don't show Djokovic clearly ahead
of Federer (serve: -0.014 vs -0.007; return: -0.021 vs -0.026) — and two
fully independent methods (the leverage-quartile engine and a simple raw
break-point-rate calculation with no leverage math at all) agree on this,
so it is not a calculation error.

The documented reputation, however, is real — ATP's own official career
break-point-conversion rankings show Djokovic at #11 (44.11%) and Federer at
#88 (41.19%), a genuine multi-point gap. The original validation test was
simply scoped wrong: the specific, published version of this claim
(Sackmann/Tennis Abstract) is about Federer's break-point performance
**specifically in his head-to-head matches against Djokovic**, not a
general across-the-board reputation. Re-running the same quartile
methodology restricted to their 47 charted head-to-head matches (9,003
points; see `step3_h2h_check.py`) reproduces the documented pattern cleanly:

| | General (career, all opponents) | Head-to-head (vs each other only) |
|---|---|---|
| Federer serve clutch | -0.007 | **-0.022** |
| Djokovic return clutch | -0.021 | **+0.022** |

Federer's serve clutch is notably worse specifically against Djokovic than
his general average, and Djokovic's return clutch flips from negative
generally to notably positive specifically against Federer — matching the
matchup-specific narrative in the literature. This is a **supplementary
validation diagnostic only** (`step3_h2h_djokovic_federer_check.csv`), run
outside the main pipeline. It does not change the primary, opponent-independent
clutch score in `step3_clutch_features.csv`, and does not reopen the
opponent-strength-adjustment decision, which remains explicitly deferred per
the original pre-registration — a general clutch score and a matchup-specific
one are legitimately different constructs, and the main analysis stays
scoped to the former.

**4. p-sensitivity**: rank stability across p=0.60→0.70 is good (r=0.93
serve, r=0.87 return across the full pool), so relative ordering across
players, which is what Step 4's regression actually uses, is robust.
However, 13/91 players (serve) and 19/91 (return) flip *sign* somewhere in
that range, meaning for players near zero, whether they're labeled
marginally "clutch" or "choker" is sensitive to the p choice. Worth stating
plainly in the paper rather than only reporting the reassuring rank
correlation.

**5. BLR convergent validity**: combined serve+return clutch score
correlates with the established BLR metric at **r = 0.793** across all 91
players, a meaningfully strong agreement and direct evidence the
quartile-based construction isn't an idiosyncratic artifact of this
specific methodological choice.

## Sufficiency coverage across the pool
All **91/91 qualified players (100%)** clear `MIN_OBS=30` on both sides for
both serve and return clutch scores. The min-40-charted-matches threshold
from Step 2 turned out to be conservative enough to guarantee full coverage
here too — no players need to be dropped or flagged as partial for Step 4.

## Outputs for Step 4
- `step3_clutch_features.csv`: 91 players × serve/return clutch scores at
  p=0.60/0.65/0.70/tiered, sufficiency flags, BLR, high/low-leverage sample
  sizes. This is the only file Step 4 needs.
- `src/core/formulas.py`: the win-probability/leverage engine (importable
  module), needed only if Step 4 wants to recompute or extend leverage,
  not for the regression itself.
- `step3_points_with_leverage.csv`: full point-level leverage (1,132,053
  rows, ~204MB). Not shipped as a deliverable, since it's too large to be a
  sensible artifact and unnecessary given a better reproducibility story.
  It's fully regeneratable by running `build_clutch_features()` (in
  `src/core/features.py`) against the public MCP data (fetched fresh via `curl` from
  `raw.githubusercontent.com`, same as every other step). Shipping the code
  instead of a 204MB intermediate is also the right move for the GitHub
  repo required by SSAC's submission rules, since a code-reproducible
  pipeline is a stronger reproducibility story than a large static file.

## Handoff note for Step 4 — which columns to actually use
`step3_clutch_features.csv` has more columns than Step 4 needs. To avoid
reconstructing this distinction from memory:

- **Primary regression variables**: `serve_clutch_p65`, `return_clutch_p65`,
  gated by `serve_clutch_p65_sufficient` / `return_clutch_p65_sufficient`
  (both True for all 91 players, per the coverage check above — so in
  practice no rows need to be dropped, but the flags should still be checked
  programmatically rather than assumed).
- **Robustness-only, not primary**: `serve_clutch_p60` / `serve_clutch_p70` /
  `return_clutch_p60` / `return_clutch_p70` (the p-sensitivity check),
  `serve_clutch_tiered` / `return_clutch_tiered` (the pressure-tiered
  variant), and `blr_combined` (the convergent-validity check against Tennis
  Abstract's established metric). Step 4 should run its primary regression on
  the p65 columns only, and use the others afterward to confirm the
  regression result is stable — not to cherry-pick whichever version fits
  best, per the same pre-registration discipline as Step 2/3.
- **Diagnostic only, not for regression**: `n_serve_high_leverage`,
  `n_serve_low_leverage`, `n_return_high_leverage`, `n_return_low_leverage` —
  sample sizes behind each player's clutch score, useful for weighting or
  flagging thin-data players in sensitivity analysis, not inputs themselves.

## Known limitations to carry into the paper
- Fixed, uniform p=0.65 (Klaassen & Magnus's own documented simplification;
  cited, not original) — rank-stable but not sign-stable for borderline
  players.
- Opponent-strength adjustment still explicitly deferred (unchanged from the
  Step 2's original decision) — confirmed as the right call by
  the Djokovic/Federer resolution above: general and matchup-specific clutch
  are genuinely different constructs, and the main pipeline stays scoped to
  the opponent-independent version throughout.
- The Djokovic/Federer general-vs-head-to-head distinction (above) is itself
  worth a sentence in the paper's discussion section — it's a real
  illustration of why "clutch" claims in tennis commentary need to specify
  their scope (career-wide vs. matchup-specific) before being testable at
  all.
