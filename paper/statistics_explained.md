# Reading the Numbers: A Plain-English Guide to This Project's Statistics

This document exists for one reason: the numbers in this project (entropy
scores, correlations, p-values, confidence intervals, reliability
coefficients) show up constantly in the docs and the abstract, and it's
easy to lose track of what each one is actually claiming. Nothing here is
new analysis. It's a plain-language companion to what's already reported
in `docs/` and `paper/abstract.md`, written so any of those numbers can be
looked up and re-understood without re-deriving it from scratch.

Each section explains: what the number means, what scale it's on, how to
read a "big" vs. "small" value, and a worked example using this project's
own real numbers.

---

## 1. Entropy: "how unpredictable is this player's shot choice"

**What it measures.** For a given situation (specifically: given the shot
a player is reacting to), how varied is their response? Do they usually
hit the same kind of shot, or does it change a lot?

**The scale.** 0 to 1, always, by construction.
- **0** means totally predictable: in a given situation, the player
  always makes the same choice.
- **1** means totally random: every option is equally likely, no pattern
  at all.
- This is a normalized number. Under the hood it starts as a raw
  "Shannon entropy" measured in bits (a concept from information theory:
  how many bits it would take to describe which shot a player picked),
  then gets divided by the maximum possible value for a 6-option grid
  (forehand/backhand x 3 directions), which forces it into a clean 0-to-1
  scale regardless of how many categories were involved.

**What real players actually look like.** Nobody is near either
extreme. The observed range is:
- ATP: 0.705 to 0.861 (91 players)
- WTA: 0.730 to 0.829 (55 players)

So every professional player is fairly unpredictable in an absolute
sense (they're all above 0.70 out of a possible 1.0), and the
*interesting* variation, the part this project's whole hypothesis rests
on, is happening within a fairly narrow band near the top of the scale.
This is itself a small, useful finding: the differences between a
"metronomic" player and a "flair" player are real but subtle in this
metric, not night-and-day.

---

## 2. Clutch score: "does this player do better or worse when it matters more"

**What it measures.** We compare how often a player wins a point in
high-pressure situations (like break points, set points) against how
often they win a point in low-pressure situations. The clutch score is
roughly the difference between those two rates.

**The scale.** Centered on 0, no fixed bounds, but in practice the
values in this project are small, generally somewhere between -0.10 and
+0.10.
- **Positive** = the player performs *better* under pressure than
  normal. Colloquially, "clutch."
- **Negative** = the player performs *worse* under pressure. Colloquially,
  "chokes."
- **Near zero** = pressure doesn't seem to change their performance much
  either way.

**Important caveat that matters a lot later in this document:** this
number, on its own, doesn't tell you whether it's a *real, stable trait*
of the player or just noise from a limited sample of high-pressure
points. That's what reliability (Section 6) is for.

---

## 3. Correlation (r): "do these two numbers move together, across players"

**What it measures.** This is the actual test at the heart of the paper.
Across all players in a pool (91 for ATP, 55 for WTA), do the players
with higher entropy also tend to have higher (or lower) clutch scores?

**The scale.** -1 to +1, always, for any correlation coefficient.
- **r = 0**: no relationship. Knowing a player's entropy tells you
  nothing about their clutch score.
- **r = +1**: a perfect positive relationship. Every player with more
  entropy has a higher clutch score, no exceptions.
- **r = -1**: a perfect negative relationship, the mirror image.
- **The sign** (+ or -) tells you the direction: does clutch performance
  go up or down as entropy goes up.
- **The size** (how far from 0) tells you the strength, regardless of
  sign. r = -0.5 and r = +0.5 are equally "strong," just pointing
  opposite directions.

**A conventional rule of thumb for interpreting size** (Cohen's
benchmarks, widely used but not a law of nature): around 0.1 is
considered "small," 0.3 "medium," 0.5 "large." This is a fixed
convention, independent of how many players are in the sample, it just
describes how big the *pattern* is, if it's real.

**Our actual numbers, and what they say:**

| Tour | Serve r | Return r |
|---|---|---|
| ATP | -0.041 | +0.016 |
| WTA | -0.259 | +0.196 |

All four of these are close to zero, especially the ATP pair. Even
WTA's largest value (-0.259) is still well under the "medium" convention
of 0.3, and, as later sections explain, doesn't survive further
scrutiny. The headline finding of the paper is exactly this: no matter
how you slice it, entropy and clutch performance don't move together in
any meaningful way.

**One more distinction worth knowing:** this project mostly uses
*Pearson* correlation (the standard kind, sensitive to the exact
numeric relationship) but also checks with *Spearman* correlation
(based on rankings, not exact values, so a few extreme outliers or a
non-straight-line relationship can't distort it as easily). When both
agree, as they do here, that's a stronger form of evidence than either
alone.

---

## 4. p-value: "how surprising would this result be if there's actually nothing going on"

This is the concept people misread most often, so it's worth being
precise.

**What it actually means.** Start by imagining, hypothetically, that the
true answer really is "no relationship at all" (r = 0 in the real
world). Because we only ever measure a limited sample of players, even
under that hypothetical, we won't get exactly 0, random variation alone
will push the number away from zero a bit. The p-value asks: *if that
hypothetical is true, how often would random noise alone produce a
result at least this far from zero?*

- **Small p** (say, 0.01): a result this extreme would be quite rare if
  nothing were really going on. That's evidence something real might be
  there.
- **Large p** (say, 0.70): a result this extreme is totally unremarkable
  even under "nothing's going on." Can't rule out coincidence.

**What it does NOT mean** (common misreadings to avoid):
- It is **not** "the probability that there's no real relationship."
- It is **not** "the probability the result is due to chance," stated
  as a fact about this specific result.
- It only ever describes how surprising the *data* would be, under a
  specific hypothetical about the world. It says nothing directly about
  which hypothetical is actually true.

**The conventional threshold** is p < 0.05 ("less than a 1-in-20 chance
of a coincidence this extreme"), but that threshold is a convention, not
a hard boundary between "real" and "fake."

**Our actual p-values:**

| Tour | Serve p | Return p |
|---|---|---|
| ATP | 0.70 | 0.88 |
| WTA | 0.056 | 0.151 |

These are mostly large, meaning: exactly what you'd expect to see if
there truly is no relationship. WTA serve (0.056) is the closest to the
conventional 0.05 line, close enough that it's worth a second look,
which is exactly what the project did (see Sections 4-5 and the
robustness checks in `docs/`), and it didn't hold up under closer
scrutiny.

---

## 5. Confidence intervals and multiple-comparison correction: being honest about uncertainty

**Confidence interval (CI).** Instead of reporting just one number for
r, a 95% CI reports a *range*: "our best single estimate is X, but given
the noise in this sample, the true value could plausibly be anywhere
from A to B." If that range includes 0, we cannot rule out "no
relationship" as the true answer, which is exactly the visual point of
the forest-plot figure in the abstract: every single interval, across
both tours and the pooled test, crosses the zero line.

A p-value and a CI are two views of the same underlying math: if a 95%
CI excludes 0, the corresponding p-value will be below 0.05, and vice
versa. The CI is often more informative because it shows a *range*, not
just a yes/no significance call, so it also communicates how wide (how
uncertain) that range is.

**Multiple-comparison correction (Bonferroni).** Every time you run more
than one statistical test, the odds that *at least one* of them looks
"significant" purely by chance go up, even if nothing real is happening
anywhere. This project runs several related tests (multiple leverage
variants, both tours, both roles), so a stricter significance threshold
is applied to compensate. A Bonferroni correction is the simplest,
most conservative version of this: divide the usual 0.05 threshold by
the number of comparisons being made. Across the 4-comparison family
used for one of this project's checks, the corrected threshold becomes
0.0125, meaning a result now needs to be considerably more extreme to
count as "significant" than it would need to be in isolation. This is
part of why WTA serve's p = 0.056, already not significant at the
ordinary 0.05 line, is even further from clearing the corrected bar.

**Equivalence testing (TOST), the stronger alternative used in this
project.** A plain "not significant" result only tells you what the data
*failed* to show. TOST (two one-sided tests) instead asks a more useful,
positive question: "given this data, how large could the true effect
possibly be, and can we rule out anything bigger than that?" The result
is a genuine upper bound (for example, "the true r is smaller than
0.21"), which is a stronger and more informative claim than "we didn't
find significance."

---

## 6. Reliability (split-half): a completely different question from correlation

This is the part of the project most likely to be confused with
correlation, because it also produces a number that looks like a
correlation, but it is answering an entirely different question.

**The question correlation answers:** do two *different* variables (like
entropy and clutch score) move together, across players?

**The question reliability answers:** if I measured the *same* variable,
for the *same* player, **twice**, using two independent halves of their
career, would I get roughly the same number both times?

**How it's actually done here.** Every qualified player's matches are
split into two halves (interleaved by date, not first-half-of-career
vs. second-half, specifically so a real change in a player's style over
time isn't mistaken for measurement noise). Entropy, and separately
clutch score, are recomputed completely independently on each half.
Then we correlate half A against half B, across players. That
correlation is the reliability figure.

**Why this matters so much.** A measurement can be *real* (not a
calculation bug) and still be *unreliable*, if it's mostly driven by
random sampling noise rather than a stable trait of the player. Low
reliability doesn't mean the number is wrong, it means it's noisy: two
honest, correct measurements of the same underlying thing can come out
looking very different just because of which specific points happened
to be charted in each half.

**Our actual reliability numbers** (Spearman-Brown corrected, which
adjusts a half-length measurement's reliability up to what the
full-length measurement's reliability would be expected to be):

| Measure | ATP | WTA |
|---|---|---|
| Entropy | 0.925 (good) | 0.897 (good) |
| Serve clutch | 0.572 (below "acceptable") | 0.578 (below "acceptable") |
| Return clutch | 0.231 (poor) | 0.055 (essentially unmeasurable) |

Conventional psychometric benchmarks (used throughout this project,
fixed before results were seen): 0.70+ is "acceptable," 0.80+ is
"good." Entropy clears "good" comfortably on both tours. Clutch scores,
especially return clutch, do not, WTA's 0.055 is barely distinguishable
from pure noise.

**Why this changes how the correlation numbers (Section 3) should be
read.** If you correlate a *reliable* variable (entropy) against an
*unreliable* one (return clutch, especially for WTA), you will tend to
find "no relationship" even if a real one exists, simply because one
side of the comparison is mostly measurement noise, not signal. This is
the single most important nuance in the whole project: the serve-side
null carries real evidentiary weight (both sides are decently
measured), but the return-side null, especially for WTA, should be read
as *inconclusive* rather than *confirmatory*. A well-measured predictor
paired with a barely-measurable outcome will produce a null result
regardless of whether a true relationship exists.

**A cautionary example: disattenuation.** There's a classical statistical
correction that tries to estimate "what would the correlation have been
if both variables were measured perfectly," by dividing the observed r
by the square root of the product of both variables' reliabilities.
Applying it here to WTA return produces r = +0.886, which looks like a
huge, exciting relationship. It is not. Dividing by a reliability as low
as 0.055 amplifies a small, noisy observed correlation (+0.196) by a
factor of about 4.5x, this is a textbook illustration of *why* very low
reliability is a genuine problem: below roughly 0.70-0.80 reliability,
this kind of correction stops rescuing the estimate and starts
manufacturing noise. It's included in the project's docs specifically
as a worked example of a trap to avoid, not as a real finding.

---

## Quick-reference glossary

| Term | Plain-English meaning | Scale | Our typical values |
|---|---|---|---|
| Entropy | How unpredictable a player's shot choice is | 0 (predictable) to 1 (random) | 0.70-0.86 |
| Clutch score | Performance shift under pressure vs. normal | Centered on 0, no fixed bound | roughly -0.10 to +0.10 |
| Correlation (r) | Do two variables move together, across players | -1 to +1 | -0.26 to +0.20 in this project |
| p-value | How surprising the data would be if there's truly no relationship | 0 to 1 | 0.06 to 0.88 in this project |
| Confidence interval | The plausible range for the true value, given the noise | Same units as the estimate | all cross zero here |
| Bonferroni correction | A stricter significance bar to account for running multiple tests | Shrinks the 0.05 threshold | as low as 0.005 in this project |
| TOST / equivalence bound | A positive bound on how large the true effect could be | Same units as r | e.g. \|r\| < 0.21 (ATP) |
| Split-half reliability | If measured twice independently, would you get the same number | 0 (pure noise) to 1 (perfectly consistent) | 0.055 to 0.925 in this project |
| Disattenuation | A correction estimating the "true" correlation if measurement were perfect | Same units as r, but unstable at low reliability | +0.886 (WTA return, a cautionary example, not a finding) |
