"""First-order translation of a clutch-score difference into match-win probability.

Leverage is, by construction, the change in match-win probability between
winning and losing a point. Raising a player's point-win probability by d on
the points in their top leverage quartile therefore changes the match-win
probability, to first order, by d times the summed leverage of those points.
This script reports that summed leverage per charted match (median over
players, p = 0.65 leverage) and the implied effect of d = 1 and 2 points.
Descriptive projection from committed point tables; not a hypothesis test.
It ignores the bottom quartile (so it is the effect of a pure top-quartile
shift) and is approximate. Writes results/applications/win_prob_translation.csv.
"""
import pickle
import numpy as np
import pandas as pd

rows = []
for tour in ('atp', 'wta'):
    _, pts = pickle.load(open(f'results/{tour}/cache_applications_{tour}.pkl', 'rb'))
    for role, col in (('serve', 'server'), ('return', 'returner')):
        mass = []
        for _, d in pts.groupby(col):
            top = d[d['leverage_p65'] >= d['leverage_p65'].quantile(0.75)]
            mass.append(top['leverage_p65'].sum() / d['match_id'].nunique())
        med = float(np.median(mass))
        rows.append({'tour': tour, 'role': role, 'top_quartile_leverage_per_match_median': med,
                     'winprob_pp_per_1pp_clutch': med, 'winprob_pp_per_2pp_clutch': 2 * med})
out = pd.DataFrame(rows)
out.to_csv('results/applications/win_prob_translation.csv', index=False)
print(out.round(2).to_string(index=False))
