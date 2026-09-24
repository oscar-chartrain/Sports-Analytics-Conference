"""
step3_h2h_check.py -- head-to-head-specific validation (Djokovic vs Federer)
================================================================================
This is a supplementary validation diagnostic, not part of the main
pipeline and not a change to the primary (opponent-independent) clutch
score used in Step 4. The main clutch score in step3_clutch_features.csv
stays pooled across each player's full career against all opponents,
exactly as pre-registered; opponent-strength adjustment stays explicitly
deferred.

This check exists because a specific, published claim about Federer's
break-point struggles (Sackmann/Tennis Abstract) is scoped to his
head-to-head matches against Djokovic specifically, not a general
across-the-board reputation. Testing that claim properly requires a
head-to-head-specific score, computed the same way (within-player quartile
split, MIN_OBS gating) but restricted to matches between these two players.

quartile_clutch() below is the original, validated implementation -- it's
also used (as a verbatim copy) by core/features.py's build_clutch_features(),
but this file is where it was first written and checked against the real
Djokovic/Federer numbers, so it's imported here rather than duplicated.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd

import data_io as dio
import features as feat

MIN_OBS = feat.MIN_OBS
quartile_clutch = feat.quartile_clutch

matches_df = dio.load_matches('charting-m-matches.csv')
match_players = matches_df.set_index('match_id')[['Player 1', 'Player 2']]

h2h_match_ids = match_players[
    ((match_players['Player 1'] == 'Novak Djokovic') & (match_players['Player 2'] == 'Roger Federer')) |
    ((match_players['Player 1'] == 'Roger Federer') & (match_players['Player 2'] == 'Novak Djokovic'))
].index

points = pd.read_csv('step3_points_with_leverage.csv', low_memory=False)
h2h_points = points[points['match_id'].isin(h2h_match_ids)].copy()
h2h_points = h2h_points.join(match_players, on='match_id')
h2h_points['server'] = h2h_points['Player 1'].where(h2h_points['Svr'] == 1, h2h_points['Player 2'])
h2h_points['returner'] = h2h_points['Player 2'].where(h2h_points['Svr'] == 1, h2h_points['Player 1'])
h2h_points['server_won_point'] = (h2h_points['PtWinner'] == h2h_points['Svr']).astype(float)

print(f'Charted Djokovic-Federer matches: {len(h2h_match_ids)}, points: {len(h2h_points)}\n')

results = []
for player in ['Novak Djokovic', 'Roger Federer']:
    serve_pts = h2h_points[h2h_points['server'] == player].copy()
    serve_pts['won'] = serve_pts['server_won_point']
    return_pts = h2h_points[h2h_points['returner'] == player].copy()
    return_pts['won'] = 1 - return_pts['server_won_point']

    s_score, s_nh, s_nl, s_suf = quartile_clutch(serve_pts, 'leverage_p65', min_obs=MIN_OBS)
    r_score, r_nh, r_nl, r_suf = quartile_clutch(return_pts, 'leverage_p65', min_obs=MIN_OBS)

    results.append({
        'player': player,
        'h2h_serve_clutch': s_score, 'h2h_serve_sufficient': s_suf,
        'n_serve_high': s_nh, 'n_serve_low': s_nl,
        'h2h_return_clutch': r_score, 'h2h_return_sufficient': r_suf,
        'n_return_high': r_nh, 'n_return_low': r_nl,
    })

out = pd.DataFrame(results)
pd.set_option('display.width', 200)
print(out.to_string(index=False))
out.to_csv('step3_h2h_djokovic_federer_check.csv', index=False)
