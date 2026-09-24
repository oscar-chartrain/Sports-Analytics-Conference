"""
entropy_pressure_escalation.py -- does shot-selection consistency change
under pressure, and does that change predict clutch performance?
============================================================================
Implements the check pre-registered in
docs/atp/02_entropy_pipeline/entropy_pressure_escalation.md, in that
order. Every other Step 2 style extension (serve zone, net play, return
depth) is measured as a normal-vs-high-pressure delta; entropy itself
never was until this script.

Uses step2_entropy_pipeline.get_player_shot_transitions(include_pressure=True)
(no new parsing logic -- reuses the same pressure classifier already used
elsewhere) to split each player's transitions into normal and
high-pressure subsets, computes conditional_normalized_entropy separately
on each (same MIN_OBS=30 per-context floor as everywhere else, applied
independently to both subsets), and correlates the resulting escalation
delta against the primary clutch outcome.

Needs the raw MCP data already present locally in results/{tour}/ (this
repo never commits it; fetch per the root README's Reproduce section
first).

Usage: python3 entropy_pressure_escalation.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import pandas as pd
import numpy as np
from scipy import stats

import features as feat
import formulas as f
import step2_entropy_pipeline as s2
import split_half_reliability as sr

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def compute_escalation(matches_df, points_df, players):
    transitions = s2.get_player_shot_transitions(matches_df, points_df, players, include_pressure=True)
    normal_df = transitions[~transitions['high_pressure']]
    hp_df = transitions[transitions['high_pressure']]

    rows = []
    for player in players:
        normal_result = s2.compute_transition_entropy(normal_df, player, min_obs_per_context=feat.MIN_OBS)
        hp_result = s2.compute_transition_entropy(hp_df, player, min_obs_per_context=feat.MIN_OBS)

        normal_sufficient = normal_result is not None and len(normal_result['low_contexts']) == 0
        hp_sufficient = hp_result is not None and len(hp_result['low_contexts']) == 0

        if normal_result:
            entropy_normal = normal_result['conditional_normalized']
            n_transitions_normal = normal_result['total_transitions']
        else:
            entropy_normal = np.nan
            n_transitions_normal = 0
        if hp_result:
            entropy_high_pressure = hp_result['conditional_normalized']
            n_transitions_high_pressure = hp_result['total_transitions']
        else:
            entropy_high_pressure = np.nan
            n_transitions_high_pressure = 0

        row = {
            'player': player,
            'entropy_normal': entropy_normal,
            'entropy_high_pressure': entropy_high_pressure,
            'n_transitions_normal': n_transitions_normal,
            'n_transitions_high_pressure': n_transitions_high_pressure,
            'sufficient': normal_sufficient and hp_sufficient,
        }
        if row['sufficient']:
            row['entropy_escalation_delta'] = row['entropy_high_pressure'] - row['entropy_normal']
        else:
            row['entropy_escalation_delta'] = np.nan
        rows.append(row)

    return pd.DataFrame(rows)


def load_clutch(tour):
    results_dir = os.path.join(REPO_ROOT, 'results', tour)
    if tour == 'atp':
        clutch = pd.read_csv(os.path.join(results_dir, 'step3_clutch_features.csv'))
    else:
        merged = pd.read_csv(os.path.join(results_dir, 'wta_merged.csv'))
        clutch = merged[['player', 'serve_clutch_p65', 'serve_clutch_p65_sufficient',
                          'return_clutch_p65', 'return_clutch_p65_sufficient']]
    return clutch


def run_tour(tour):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players = sr.load_pool(tour)
    matches, points = sr.load_raw(tour)
    relevant_matches = matches[matches['Player 1'].isin(players) | matches['Player 2'].isin(players)]
    relevant_points = points[points['match_id'].isin(set(relevant_matches['match_id']))]

    print("Computing normal vs. high-pressure conditional entropy...")
    escalation = compute_escalation(relevant_matches, relevant_points, players)

    out_path = os.path.join(REPO_ROOT, 'results', tour, 'entropy_pressure_escalation.csv')
    escalation.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")

    n_sufficient = escalation['sufficient'].sum()
    print(f"\n{n_sufficient}/{len(players)} players sufficient in both pressure buckets "
          f"(MIN_OBS={feat.MIN_OBS} per context, applied independently to each)")

    sufficient = escalation[escalation['sufficient']]
    delta = sufficient['entropy_escalation_delta']
    n_pos = (delta > 0).sum()
    n_neg = (delta < 0).sum()
    print(f"Escalation delta: mean={delta.mean():+.4f}, std={delta.std():.4f}, "
          f"median={delta.median():+.4f}")
    print(f"  {n_pos}/{len(delta)} players get MORE unpredictable under pressure (positive delta)")
    print(f"  {n_neg}/{len(delta)} players get MORE predictable under pressure (negative delta)")

    clutch = load_clutch(tour)
    merged = sufficient.merge(clutch, on='player', how='inner')

    role_results = []
    for role in ['serve', 'return']:
        suff_col = f'{role}_clutch_p65_sufficient'
        clean = merged[merged[suff_col]]
        if len(clean) < 4:
            print(f"\n{role}: n={len(clean)}, too small to test")
            continue
        r, p = stats.pearsonr(clean['entropy_escalation_delta'], clean[f'{role}_clutch_p65'])
        print(f"\n{role}: n={len(clean)}, r={r:+.4f}, p={p:.4f}")
        role_results.append({'tour': tour, 'role': role, 'n': len(clean), 'r': r, 'p': p})

    return role_results


if __name__ == '__main__':
    all_results = []
    for tour in ['atp', 'wta']:
        all_results.extend(run_tour(tour))

    print(f"\n{'=' * 70}\nSUMMARY AND BONFERRONI CORRECTION\n{'=' * 70}")
    for r in all_results:
        print(f"{r['tour'].upper():4s} {r['role']:7s}  n={r['n']:3d}  r={r['r']:+.4f}  p={r['p']:.4f}")

    pvals = []
    for r in all_results:
        pvals.append(r['p'])
    bonf = f.bonferroni_correction(pvals)
    print(f"\nBonferroni-corrected alpha for these {bonf['n_comparisons']} comparisons: "
          f"{bonf['corrected_alpha']:.4f}. Any significant: {any(bonf['significant'])}")
