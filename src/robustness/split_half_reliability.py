"""
split_half_reliability.py -- split-half reliability of the entropy
predictor and the clutch-score outcome
============================================================================
Implements the check pre-registered in
docs/atp/04_regression_results/split_half_reliability.md, run in that
order. Distinguishes "no true relationship" from "the measurements are
too noisy to see one," a question the power/MDES and MIN_OBS checks in
power_and_robustness.py don't answer.

Splits each tour's relevant matches into two halves by sorting match_ids
(date-prefixed, so this sort is chronological) and alternating even/odd
positions into half A / half B -- an interleaved split, not a
first-half-of-career vs. second-half split, so a real change in a
player's style over their career doesn't get mistaken for measurement
noise. Recomputes conditional_normalized_entropy and {role}_clutch_p65
independently on each half using the exact same methodology as the
primary pipeline (same MIN_OBS=30 floor per half, same leverage engine),
then correlates half A against half B across players sufficient in both.

Needs the raw MCP data already present locally in results/{tour}/ (this
repo never commits it; fetch per the root README's Reproduce section
first). This is the slow script in the project: two full extraction
passes (entropy transitions + clutch/leverage) per half, per tour.

spearman_brown() below now lives in core/formulas.py (it used to be
copy-pasted separately in this file, continuous_slope_reliability.py,
shrinkage_reliability.py, opponent_adjusted_return_clutch.py, and
make_reliability_figure.py).

Usage: python3 split_half_reliability.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import pandas as pd
import numpy as np
from scipy import stats

import data_io as dio
import features as feat
import formulas as f
import step2_entropy_pipeline as s2

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load_raw(tour):
    if tour == 'atp':
        gender = 'm'
    else:
        gender = 'w'
    results_dir = os.path.join(REPO_ROOT, 'results', tour)
    old_cwd = os.getcwd()
    os.chdir(results_dir)
    try:
        matches = dio.load_matches(f'charting-{gender}-matches.csv')
        points = dio.load_points_data(decades=('2020s', '2010s', 'to-2009'), gender=gender)
    finally:
        os.chdir(old_cwd)
    return matches, points


def load_pool(tour):
    results_dir = os.path.join(REPO_ROOT, 'results', tour)
    if tour == 'atp':
        features_filename = 'step2_full_pool_features.csv'
    else:
        features_filename = 'wta_full_pool_features.csv'
    features_path = os.path.join(results_dir, features_filename)
    return pd.read_csv(features_path)['player'].tolist()


def split_matches(matches_df, players):
    """One canonical A/B assignment for every relevant match, based on
    each match's position in the globally date-sorted list of matches
    involving any qualified player. A player's own matches are a
    subsequence of that sorted list, so they land in an interleaved
    early/late pattern across both halves, not a career-first-half vs.
    career-second-half split."""
    relevant_matches = matches_df[
        matches_df['Player 1'].isin(players) | matches_df['Player 2'].isin(players)
    ].copy()
    sorted_ids = sorted(relevant_matches['match_id'].tolist())
    half_map = {}
    for i, mid in enumerate(sorted_ids):
        if i % 2 == 0:
            half_map[mid] = 'A'
        else:
            half_map[mid] = 'B'
    return half_map, relevant_matches


def build_entropy_half(matches_df, points_df, players, half_map, half_label):
    ids = set()  # match_ids belonging to this half
    for mid, h in half_map.items():
        if h == half_label:
            ids.add(mid)
    sub_matches = matches_df[matches_df['match_id'].isin(ids)]
    sub_points = points_df[points_df['match_id'].isin(ids)]
    transitions = s2.get_player_shot_transitions(sub_matches, sub_points, players)

    values = {}
    for player in players:
        result = s2.compute_transition_entropy(transitions, player, min_obs_per_context=feat.MIN_OBS)
        if result is not None and len(result['low_contexts']) == 0:
            values[player] = result['conditional_normalized']
    return values


def build_clutch_half(matches_df, points_df, players, half_map, half_label):
    ids = set()  # match_ids belonging to this half
    for mid, h in half_map.items():
        if h == half_label:
            ids.add(mid)
    sub_matches = matches_df[matches_df['match_id'].isin(ids)]
    sub_points = points_df[points_df['match_id'].isin(ids)]
    clutch = feat.build_clutch_features(sub_matches, sub_points, players)
    return clutch.set_index('player')


def reliability_report(name, half_a_vals, half_b_vals):
    players = sorted(set(half_a_vals) & set(half_b_vals))
    n = len(players)
    if n < 4:
        print(f"{name}: n={n}, too small to compute reliability")
        return {'name': name, 'n': n, 'r_half': np.nan, 'p': np.nan, 'r_full': np.nan}
    a_list = []
    b_list = []
    for p in players:
        a_list.append(half_a_vals[p])
        b_list.append(half_b_vals[p])
    a = np.array(a_list)
    b = np.array(b_list)
    r, p = stats.pearsonr(a, b)
    r_full = f.spearman_brown(r)
    print(f"{name}: n={n} (players sufficient in both halves)")
    print(f"  split-half r={r:+.4f} (p={p:.4f}), Spearman-Brown corrected full-length reliability={r_full:.4f}")
    return {'name': name, 'n': n, 'r_half': r, 'p': p, 'r_full': r_full}


def run_tour(tour):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players = load_pool(tour)
    matches, points = load_raw(tour)
    half_map, relevant_matches = split_matches(matches, players)
    n_a = sum(1 for h in half_map.values() if h == 'A')
    n_b = sum(1 for h in half_map.values() if h == 'B')
    print(f"{len(players)} players, {len(half_map)} relevant matches split {n_a}/{n_b} A/B")

    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]

    print("\nComputing entropy on each half...")
    entropy_a = build_entropy_half(relevant_matches, relevant_points, players, half_map, 'A')
    entropy_b = build_entropy_half(relevant_matches, relevant_points, players, half_map, 'B')

    print("\nComputing clutch scores on each half...")
    clutch_a = build_clutch_half(relevant_matches, relevant_points, players, half_map, 'A')
    clutch_b = build_clutch_half(relevant_matches, relevant_points, players, half_map, 'B')

    results = [reliability_report(f'{tour.upper()} entropy', entropy_a, entropy_b)]

    for role in ['serve', 'return']:
        suff_col = f'{role}_clutch_p65_sufficient'
        a_vals = {}
        for p in clutch_a.index:
            if clutch_a.loc[p, suff_col]:
                a_vals[p] = clutch_a.loc[p, f'{role}_clutch_p65']
        b_vals = {}
        for p in clutch_b.index:
            if clutch_b.loc[p, suff_col]:
                b_vals[p] = clutch_b.loc[p, f'{role}_clutch_p65']
        results.append(reliability_report(f'{tour.upper()} {role} clutch', a_vals, b_vals))

    return results


if __name__ == '__main__':
    all_results = []
    for tour in ['atp', 'wta']:
        all_results.extend(run_tour(tour))

    print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}")
    for r in all_results:
        if r and not np.isnan(r['r_half']):
            print(f"{r['name']:20s} n={r['n']:3d}  r_half={r['r_half']:+.4f}  "
                  f"r_full (Spearman-Brown)={r['r_full']:.4f}")
        elif r:
            print(f"{r['name']:20s} n={r['n']:3d}  too small to compute")
