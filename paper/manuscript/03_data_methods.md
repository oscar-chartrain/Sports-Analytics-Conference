# 3. Data

## 3.1 Source

All shot- and point-level data come from the Match Charting Project (MCP) [ref: Sackmann, MCP], a volunteer effort in which charters record every point of a professional match shot by shot: the type of each shot (forehand, backhand, slice, volley and so on), its direction in one of three court zones, the serve location, and how the point ended. No other public dataset records professional tennis at this level of detail; tracking data (ball speed, player position) is held privately by the tours and their data partners. The MCP is licensed CC BY-NC-SA 4.0; we redistribute only derived, player-level outputs.

## 3.2 Player pools

We include every player with at least 40 charted matches. Forty matches is the smallest count at which every forehand/backhand × direction cell holds more than 1,000 observations for the least-charted qualifying player, and every player in both pools clears the 30-observation floor we apply to each feature (below). The threshold was fixed before any outcome was computed.

| | ATP | WTA |
|---|---|---|
| Charted matches in MCP | 7,567 | 4,080 |
| Qualified players (≥40 matches) | 91 | 55 |
| Median charted matches per player | 74 | [WTA_MED] |
| Points analyzed | 1,132,053 | [WTA_N_POINTS] |

*Table 1. Player pools. A match counts toward a player's total whether they appear as Player 1 or Player 2.*

The MCP over-represents well-known players and high-profile matches, because charters choose what to chart. Our pools are therefore the most-charted players, not a random sample of the tour; Section 7 discusses what this does and does not affect.

## 3.3 Notation parsing and validation

Each point is stored as a string of shot codes. Every shot is attributed to its hitter by alternation from the serve. Because the serve is coded as a digit rather than a letter, an early version of our parser started the alternation one shot late and inverted every hitter label; we found this by checking parsed point winners against the MCP's own recorded winner (`PtWinner`), which rose from 9.7% to 90.3% agreement after the fix, and the parser now runs that check as a standing regression guard. All results in this paper use the corrected parser.

# 4. Methods

Every hypothesis, variable definition and decision rule below was written down before the corresponding data were analyzed. The WTA replication was pre-registered before any WTA data were loaded. The analyses in Section 6 were pre-registered separately, after the primary results were known; we mark them as such.

## 4.1 Shot-selection consistency: conditional entropy

We describe each groundstroke by its wing and direction: forehand or backhand, hit to one of three zones, giving six categories C. Rarer shots (lobs, half-volleys, overheads) are too sparse to support per-player estimates and are excluded from C; drop shots are folded into their wing.

A player's overall mix of shots says more about court geometry than about style: everyone hits more cross-court than down the line. What distinguishes a predictable player from an unpredictable one is how much their choice depends on what they have just received. We therefore condition on the incoming shot. For every shot the player hits, the context k is the wing and direction of the opponent's preceding shot (six values), plus one catch-all context for serves, lobs and shots with no recorded direction.

Let n(k, c) be the number of times the player hit category c in context k, N_k = Σ_c n(k, c), and N = Σ_k N_k. The player's conditional entropy is the average, over contexts, of how unpredictable their shot is within each context:

  H(X | K) = − Σ_k (N_k / N) Σ_c P(c | k) log₂ P(c | k),  with P(c | k) = n(k, c) / N_k    (1)

We divide by the maximum possible value, log₂ 6, so that the measure runs from 0 (the player always hits the same shot back to the same ball) to 1 (every reply is equally likely whatever they receive):

  H̃ = H(X | K) / log₂ 6    (2)

We call H̃ *conditional entropy* throughout. Each context must hold at least 30 shots for a player's value to be computed; all 91 ATP and 55 WTA players meet this floor. Figure 1 illustrates the measure for two players.

[FIGURE 1: entropy_transition_illustration.png. Caption: Conditional shot distributions for two players with low and high conditional entropy. Each row is an incoming shot; each cell, the share of replies to that shot.]

## 4.2 Clutch performance: leverage-weighted point outcomes

**Leverage.** Following Morris [ref: Morris 1977], the importance of a point is how much winning it, rather than losing it, changes the probability of winning the match:

  L = P(win match | win point) − P(win match | lose point)    (3)

We compute L exactly for every point with the standard recursive game, tiebreak, set and match win-probability formulas [refs: Klaassen & Magnus 2003; Barnett & Clarke 2005], given the score, who is serving, and the match format. The recursion needs one input, the probability p that the server wins a point. We fix p = 0.65 for every point and every player. Using each player's own serve strength would make leverage depend on the player being evaluated, which could create a spurious link between style and clutch; a single tour-wide constant avoids that. We repeat every result at p = 0.60 and p = 0.70, at a tiered value lowering p on pressure points by the effect Klaassen and Magnus estimated [ref: K&M 2001], and at each tour's observed serve-point win rate (0.644 ATP).

Leverage behaves as expected: a break point at 5–5 in a deciding set has L = 0.39, while a nominal game point at 5–0 up in the first set has L = 0.0004.

**Clutch score.** For each player and each role (serving and returning), we split that player's own points into quartiles of leverage, and define clutch as the difference in points won between their most and least important points:

  Clutch = (share of points won in the top leverage quartile) − (share won in the bottom quartile)    (4)

A positive score means the player wins a larger share of important points than unimportant ones. Using each player's own quartiles guarantees that every player has a well-populated high- and low-leverage group; each must contain at least 30 points (every player in both pools has more than 700). Serve and return are kept separate because they draw on different skills and, as Section 5 shows, behave very differently.

This construction belongs to the same family as the leverage-based clutch metrics already in use: Tennis Abstract's Balanced Leverage Ratio (BLR) [ref: Sackmann] and the leverage metrics Stats Perform presented at SSAC 2022 [ref]. BLR is the average leverage of points won divided by that of points lost, computed separately on serve and return and then averaged. We compute BLR for every player alongside our clutch score.

## 4.3 Measuring reliability

A clutch score is only useful if it describes the player and not the particular matches that happened to be charted. We test this with split-half reliability, the standard check for any measurement instrument. Each tour's matches are sorted by date and assigned alternately to half A and half B, so both halves cover each player's whole career and a genuine change in style over time is not mistaken for noise. Every measure is recomputed from scratch on each half, with the same floors, and the two halves are correlated across players. The correlation r_half describes a measure built from half the data; the Spearman–Brown formula gives the reliability ρ of the full-length measure:

  ρ = 2 r_half / (1 + r_half)    (5)

We read ρ ≥ 0.70 as acceptable, the conventional threshold. Because clutch scores rest on fewer points than entropy, we also test whether a better construction could rescue them: a continuous version that regresses point outcomes on leverage instead of comparing quartiles; an opponent-adjusted version that measures each return point against that server's own average; and an empirical-Bayes version that shrinks each player's score toward the pool mean in proportion to how noisy it is [ref: Efron & Morris].

## 4.4 Inference

**Primary test.** For each tour and role, we regress clutch score on conditional entropy across players (ordinary least squares; we report Pearson r, its p-value, the slope and its 95% interval). Five leverage variants × two roles give ten tests per tour; we Bonferroni-correct across all ten (α = 0.005).

**Equivalence.** A non-significant correlation does not show that the effect is small. We use two one-sided tests (TOST) [ref: Lakens] to find the smallest bound Δ such that |r| < Δ can be asserted at the 95% level.

**Disattenuation.** Measurement error pulls observed correlations toward zero. If the predictor has reliability ρ_X and the outcome ρ_Y, the correlation between the underlying traits is at most the observed one divided by √(ρ_X ρ_Y) [ref: Spearman 1904]. Applying this to the equivalence bound gives the largest true-score correlation our data can rule out:

  Δ_true = Δ / √(ρ_X ρ_Y)    (6)

When Δ_true exceeds 1, the data cannot rule out any correlation at all.

**Power.** With 91 ATP players, the primary test has 80% power to detect |r| ≥ 0.29 at α = 0.05.

**Pooled test.** Finally, we pool both tours (146 players) and add a tour × entropy interaction, to test whether the relationship differs between men and women.
