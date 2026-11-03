# 7. Discussion (draft: limitations portion; applications portion written after Section 6 results)

## 7.x Limitations

**Who gets charted.** The MCP is a volunteer project, and charters choose well-known players and high-profile matches. Our pools are the 91 men and 55 women with the most charted matches, not a random sample of either tour. This matters less than it might seem for the reliability finding: if anything, these are the players with the most data, so reliability for less-charted players can only be lower. It matters more for the entropy result, which describes the relationship among elite, frequently televised players and may not extend further down the rankings.

**One fixed serve probability.** Leverage depends on the assumed probability that the server wins a point. We fix it for everyone to keep leverage independent of the player being measured. This treats a break point against a dominant server and against a weak one as equally important, which they are not. All conclusions hold across five values of this parameter, including each tour's own observed rate, but 13 of 91 ATP players on serve and 19 on return change the sign of their clutch score somewhere between p = 0.60 and 0.70. For a player near zero, whether they are labeled clutch at all depends on a modeling choice.

**What a null can and cannot say.** Our equivalence bounds rule out moderate or large correlations between conditional entropy and clutch performance among these players. They do not rule out small ones, and on WTA return, where the clutch score has almost no reliability, they rule out nothing. We also measure one kind of unpredictability, the reply to the previous shot. Other kinds, serve placement under pressure or tactical variation across a match, are not tested here.

**A known reconstruction gap.** A late addition to the pipeline (the tour-specific leverage variant) required rebuilding the ATP clutch features from raw data, and the rebuilt scores differ from the originals by up to 0.005 for some players. Every primary result uses the original, frozen file; the rebuilt version gives materially identical conclusions, and we report results that depend on it with that caveat.

**Career aggregates, not form.** Every measure here pools a player's whole charted career. A player's clutch performance could genuinely change over time; our interleaved split deliberately does not count such change as noise. Reliability of a single season, or a single match, would be lower still.
