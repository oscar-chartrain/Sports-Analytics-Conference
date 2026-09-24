"""
run_pipeline.py -- single end-to-end driver, either tour
=============================================================
Replaces the manual "run these six scripts in this order, remember which
files feed which" sequence with one command:

    python3 run_pipeline.py --tour atp --min-matches 40
    python3 run_pipeline.py --tour wta --min-matches 40

This is orchestration only -- it calls the existing, already-validated
functions from core/data_io.py, core/features.py, core/formulas.py, and the
sibling step2_entropy_pipeline.py in the right order. It does not
reimplement or modify any of their logic, so it carries none of the risk a
refactor of the underlying functions would.

Produces, for the requested tour:
  {tour}_qualified_pool_min{N}.csv
  {tour}_full_pool_features.csv       (entropy/style, Step 2 equivalent)
  {tour}_clutch_features.csv          (leverage/clutch, Step 3 equivalent)
  {tour}_merged.csv                   (regression-ready, Step 4 equivalent)
  {tour}_merged.csv.snapshot.json     (data provenance)
  plus prints the primary regression result and robustness table.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm

import data_io as dio
import features as feat
import formulas as f
import step2_entropy_pipeline as s2


def fetch_and_load(tour, min_matches, decades=('2020s', '2010s', 'to-2009')):
    if tour == 'atp':
        gender = 'm'
    else:
        gender = 'w'
    matches = dio.load_matches(f'charting-{gender}-matches.csv')
    points = dio.load_points_data(decades=decades, gender=gender)
    pool = dio.get_qualified_player_pool(matches, min_matches=min_matches)
    pool.to_csv(f'{tour}_qualified_pool_min{min_matches}.csv', index=False)
    return matches, points, pool


def build_entropy_features(tour, matches, points, pool):
    players = pool['player'].tolist()
    relevant_matches = matches[matches['Player 1'].isin(players) | matches['Player 2'].isin(players)]
    target_ids = set(relevant_matches['match_id'])
    relevant_points = points[points['match_id'].isin(target_ids)]

    core_shots = s2.get_player_shots(relevant_matches, relevant_points, players)
    extended_shots = s2.get_player_shots_extended(relevant_matches, relevant_points, players)
    transitions = s2.get_player_shot_transitions(relevant_matches, relevant_points, players)
    pressure = s2.get_pressure_features(relevant_matches, relevant_points, players)

    rows = []
    for player in players:
        row = {'player': player}
        row['charted_matches'] = pool.loc[pool['player'] == player, 'charted_matches'].iloc[0]

        core_result = s2.compute_player_entropy(core_shots, player, min_obs_per_cell=feat.MIN_OBS)
        row['total_core_shots'] = core_result['total_shots']
        row['pooled_normalized_entropy'] = core_result['normalized_entropy']
        row['pooled_entropy_sufficient'] = core_result['data_sufficient']

        trans_result = s2.compute_transition_entropy(transitions, player, min_obs_per_context=feat.MIN_OBS)
        if trans_result is not None:
            row['total_transitions'] = trans_result['total_transitions']
            row['conditional_normalized_entropy'] = trans_result['conditional_normalized']
            row['marginal_normalized_entropy_transitions'] = trans_result['marginal_normalized']
            row['info_gain_relative'] = trans_result['info_gain_relative']
            row['transition_low_context_count'] = len(trans_result['low_contexts'])
            row['transition_entropy_sufficient'] = len(trans_result['low_contexts']) == 0
        else:
            row['total_transitions'] = 0
            row['conditional_normalized_entropy'] = np.nan
            row['marginal_normalized_entropy_transitions'] = np.nan
            row['info_gain_relative'] = np.nan
            row['transition_low_context_count'] = np.nan
            row['transition_entropy_sufficient'] = False

        row.update(feat.compute_dropshot_features(extended_shots, player, min_obs=feat.MIN_OBS))
        row.update(feat.reduce_pressure_features(pressure, player, min_obs=feat.MIN_OBS))
        rows.append(row)

    feature_df = pd.DataFrame(rows)
    feature_df.to_csv(f'{tour}_full_pool_features.csv', index=False)
    return feature_df, relevant_matches, relevant_points


def run_regression(tour, merged):
    print(f"\n{'='*70}\nPRIMARY REGRESSION ({tour.upper()})\n{'='*70}")
    for role in ['serve', 'return']:
        suff_col = f'{role}_clutch_p65_sufficient'
        clean = merged[merged['transition_entropy_sufficient'] & merged[suff_col]]
        n_dropped = len(merged) - len(clean)
        if n_dropped:
            print(f"NOTE: {n_dropped} player(s) dropped for insufficient data on {role} "
                  f"(gated explicitly on '{suff_col}', not inferred from NaN) -- see below.")
        y = clean[f'{role}_clutch_p65']
        X = sm.add_constant(clean['conditional_normalized_entropy'])
        m = sm.OLS(y, X).fit()
        r, p = stats.pearsonr(clean['conditional_normalized_entropy'], y)
        print(f"{role}: n={len(clean)} (of {len(merged)} pool), r={r:+.4f}, p={p:.4f}, "
              f"beta={m.params['conditional_normalized_entropy']:+.4f}, R2={m.rsquared:.4f}")

    if 'p_empirical' in merged.columns:
        print(f"\nTour-specific empirical p used above: {merged['p_empirical'].iloc[0]:.4f}")
    print(f"\nRobustness across p-variants:")
    for v in ['p60', 'p65', 'p70', 'tiered', 'empirical']:
        for role in ['serve', 'return']:
            col = f'{role}_clutch_{v}'
            suff_col = f'{role}_clutch_{v}_sufficient'
            clean = merged[merged['transition_entropy_sufficient'] & merged[suff_col]]
            r, p = stats.pearsonr(clean['conditional_normalized_entropy'], clean[col])
            print(f"  {col:28s}  r={r:+.4f}  p={p:.4f}  (n={len(clean)})")

    pvals = []
    for v in ['p60', 'p65', 'p70', 'tiered', 'empirical']:
        for role in ['serve', 'return']:
            col = f'{role}_clutch_{v}'
            suff_col = f'{role}_clutch_{v}_sufficient'
            clean = merged[merged['transition_entropy_sufficient'] & merged[suff_col]]
            pvals.append(stats.pearsonr(clean['conditional_normalized_entropy'], clean[col])[1])
    bonf = f.bonferroni_correction(pvals)
    print(f"\nBonferroni-corrected alpha for these {bonf['n_comparisons']} comparisons: "
          f"{bonf['corrected_alpha']:.4f}. Any significant: {any(bonf['significant'])}")


def main():
    parser = argparse.ArgumentParser(description='Run the full entropy/clutch pipeline for one tour.')
    parser.add_argument('--tour', choices=['atp', 'wta'], required=True)
    parser.add_argument('--min-matches', type=int, default=40)
    parser.add_argument('--decades', nargs='+', default=['2020s', '2010s', 'to-2009'],
                         help='Which decade files to load, e.g. --decades 2020s for a quick smoke test')
    args = parser.parse_args()

    t0 = time.time()
    print(f"[1/4] Fetching and loading {args.tour.upper()} data...")
    matches, points, pool = fetch_and_load(args.tour, args.min_matches, decades=tuple(args.decades))
    print(f"  {len(pool)} qualified players, {time.time()-t0:.0f}s")

    print(f"[2/4] Building entropy/style features...")
    t0 = time.time()
    features, rel_matches, rel_points = build_entropy_features(args.tour, matches, points, pool)
    print(f"  done, {time.time()-t0:.0f}s")

    print(f"[3/4] Building leverage/clutch features...")
    t0 = time.time()
    clutch = feat.build_clutch_features(rel_matches, rel_points, pool['player'].tolist())
    clutch.to_csv(f'{args.tour}_clutch_features.csv', index=False)
    print(f"  done, {time.time()-t0:.0f}s")

    print(f"[4/4] Merging and running primary regression...")
    merged = features.merge(clutch, on='player', how='inner', validate='one_to_one')
    merged.to_csv(f'{args.tour}_merged.csv', index=False)
    dio.snapshot_data_sources(f'{args.tour}_merged.csv',
                              sources={f'{args.tour}_merged.csv': merged},
                              extra={'tour': args.tour, 'min_matches': args.min_matches,
                                     'min_obs': feat.MIN_OBS, 'pool_size': len(pool)})
    run_regression(args.tour, merged)


if __name__ == '__main__':
    main()
