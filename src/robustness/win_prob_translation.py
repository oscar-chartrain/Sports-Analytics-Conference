"""First-order translation of a clutch-score difference into match-win probability.

Leverage is, by construction, the change in match-win probability between
winning and losing a point. Raising a player's point-win probability by d on
the points in their top leverage quartile therefore changes the match-win
probability, to first order, by d times the summed leverage of those points.
A quartile clutch score is top minus bottom, so a difference of d can arise
anywhere between a pure top-quartile shift (largest effect) and a pure
bottom-quartile shift (smallest effect, because bottom-quartile points carry
little leverage). This script reports both ends of that range: the summed
leverage per charted match in each quartile (median over players, p = 0.65
leverage) and the implied effect of d = 1 and 2 points.

Descriptive projection from the point tables; not a hypothesis test. The
point table comes from applications_analyses.load_tour, which uses the cached
table if present and otherwise rebuilds it from the raw MCP files (see the
README), so this script also runs from a fresh clone once the raw data have
been fetched.

Writes results/applications/win_prob_translation.csv.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import numpy as np
import pandas as pd

import applications_analyses as aa

rows = []
for tour in ('atp', 'wta'):
    _, _, _, _, pts = aa.load_tour(tour)
    for role, col in (('serve', 'server'), ('return', 'returner')):
        top_mass, bottom_mass = [], []
        for _, d in pts.groupby(col):
            lev = d['leverage_p65'].dropna()
            n_matches = d.loc[lev.index, 'match_id'].nunique()
            top_mass.append(lev[lev >= lev.quantile(0.75)].sum() / n_matches)
            bottom_mass.append(lev[lev <= lev.quantile(0.25)].sum() / n_matches)
        top, bottom = float(np.median(top_mass)), float(np.median(bottom_mass))
        rows.append({'tour': tour, 'role': role,
                     'top_quartile_leverage_per_match_median': top,
                     'bottom_quartile_leverage_per_match_median': bottom,
                     'winprob_pp_per_1pp_if_top_shift': top,
                     'winprob_pp_per_1pp_if_bottom_shift': bottom,
                     'winprob_pp_per_2pp_if_top_shift': 2 * top,
                     'winprob_pp_per_2pp_if_bottom_shift': 2 * bottom})
out = pd.DataFrame(rows)
out.to_csv(os.path.join(aa.OUT_DIR, 'win_prob_translation.csv'), index=False)
print(out.round(2).to_string(index=False))
