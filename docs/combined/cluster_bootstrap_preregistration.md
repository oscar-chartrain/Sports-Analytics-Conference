# Pre-registration: match-level cluster bootstrap for the rank intervals

Written 2026-11-16, before the script `src/robustness/cluster_bootstrap_ranks.py`
existed or was run. Self-registered, and written after the Applications
bootstrap (2026-11-03) whose result it re-examines.

## Why

In the ATP pool about 70% of matches are between two pool players, so the same
points enter two players' scores (one as server, one as returner). The
Applications bootstrap resamples each player's matches independently, which
treats the players as unrelated. A cluster bootstrap that resamples the global
list of matches, and gives every player the draw count of each of their own
matches, keeps that dependence.

## Procedure

For each tour, draw B = 2,000 multinomial resamples of the full list of
relevant matches (seed 20261116). For every replicate, each player's matches
carry the replicate's draw counts, and serve clutch, return clutch and BLR are
recomputed with the same weighted-quartile code as the Applications bootstrap
(`applications_analyses.RolePoints`). Players are ranked within each replicate.
Sanity check before anything is written: unit weights reproduce every
player's pipeline serve and return clutch score.

## Decision rule

The cluster intervals replace the player-level intervals in the paper (the
player-level intervals stay in the repository). If the median 95% rank-interval
width differs from the player-level one by more than 10% in either direction on
any measure, the paper states the change. No other threshold is used.
