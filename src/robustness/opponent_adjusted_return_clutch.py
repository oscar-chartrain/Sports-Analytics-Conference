"""
opponent_adjusted_return_clutch.py -- tests whether adjusting return
clutch for the serving opponent's own strength improves split-half
reliability, per the pre-registration in
docs/atp/04_regression_results/opponent_adjusted_return_clutch.md.

Reuses build_clutch_features(..., return_points=True) unmodified
(already built and validated for continuous_slope_reliability.py) for
the point-level table (server, returner, server_won_point,
leverage_p65), and split_half_reliability.py's load_pool/load_raw/
split_matches unmodified for the half split. No new parsing or
hitter-attribution logic anywhere in this script.

For each half independently: each opponent's serve-win-rate is
estimated leave-one-out (excluding the specific target player's own
matches against them, to avoid the circularity of using an opponent's
average strength to adjust a score partly built from points against
that very opponent), with a tour-wide empirical-p fallback for
opponents with fewer than MIN_OBS remaining points after exclusion.
Return clutch is then recomputed on the residual (won - expected_win)
instead of the raw win indicator, same leverage-quartile buckets as the
primary construction.

Usage: python3 opponent_adjusted_return_clutch.py
Needs the raw MCP data already present locally in results/{tour}/, same
as split_half_reliability.py. Same slow cost profile (one clutch
extraction pass per half, per tour; no entropy extraction needed).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
import pandas as pd
from scipy import stats

import data_io as dio
import features as feat
import formulas as f
import split_half_reliability as sr

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MIN_OBS = feat.MIN_OBS


def compute_opponent_adjusted_half(matches_df, points_df, players, half_map, half_label, min_obs=MIN_OBS):
    ids = set()  # match_ids belonging to this half
    for mid, h in half_map.items():
        if h == half_label:
            ids.add(mid)
    sub_matches = matches_df[matches_df['match_id'].isin(ids)]
    sub_points = points_df[points_df['match_id'].isin(ids)]

    p_empirical = dio.compute_empirical_p(sub_points)
    _, pts = feat.build_clutch_features(sub_matches, sub_points, players, return_points=True)

    server_totals = pts.groupby('server')['server_won_point'].agg(tot_sum='sum', tot_cnt='count')

    values = {}
    fallback_count = 0
    lookup_count = 0
    for player in players:
        rp = pts[pts['returner'] == player].copy()
        if len(rp) < min_obs * 4:
            continue
        rp['won'] = 1 - rp['server_won_point']

        opp_within = rp.groupby('server')['server_won_point'].agg(m_sum='sum', m_cnt='count')

        rp = rp.merge(server_totals, left_on='server', right_index=True, how='left')
        rp = rp.merge(opp_within, left_on='server', right_index=True, how='left')
        rp['m_sum'] = rp['m_sum'].fillna(0)
        rp['m_cnt'] = rp['m_cnt'].fillna(0)
        loo_sum = rp['tot_sum'] - rp['m_sum']
        loo_cnt = rp['tot_cnt'] - rp['m_cnt']
        sufficient_loo = loo_cnt >= min_obs
        safe_loo_cnt = loo_cnt.replace(0, np.nan)
        opp_rate = np.where(sufficient_loo, loo_sum / safe_loo_cnt, p_empirical)
        rp['expected_win'] = 1 - opp_rate
        rp['residual'] = rp['won'] - rp['expected_win']

        lookup_count += len(rp)
        fallback_count += int((~sufficient_loo).sum())

        q_low = rp['leverage_p65'].quantile(0.25)
        q_high = rp['leverage_p65'].quantile(0.75)
        low = rp[rp['leverage_p65'] <= q_low]
        high = rp[rp['leverage_p65'] >= q_high]
        if len(low) >= min_obs and len(high) >= min_obs:
            values[player] = high['residual'].mean() - low['residual'].mean()

    if lookup_count:
        fallback_rate = fallback_count / lookup_count
    else:
        fallback_rate = float('nan')
    return values, fallback_rate


def run_tour(tour):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players = sr.load_pool(tour)
    matches, points = sr.load_raw(tour)
    half_map, relevant_matches = sr.split_matches(matches, players)
    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]

    print("Computing opponent-adjusted return clutch on half A...")
    values_a, fallback_a = compute_opponent_adjusted_half(relevant_matches, relevant_points, players, half_map, 'A')
    print("Computing opponent-adjusted return clutch on half B...")
    values_b, fallback_b = compute_opponent_adjusted_half(relevant_matches, relevant_points, players, half_map, 'B')

    print(f"Fallback rate (opponent had <{MIN_OBS} leave-one-out points, used tour-wide empirical p): "
          f"half A {fallback_a:.1%}, half B {fallback_b:.1%}")

    common = sorted(set(values_a) & set(values_b))
    n = len(common)
    if n < 4:
        print(f"n={n}, too small to compute reliability")
        return None
    a_list = []
    b_list = []
    for p in common:
        a_list.append(values_a[p])
        b_list.append(values_b[p])
    a = np.array(a_list)
    b = np.array(b_list)
    r_half, p = stats.pearsonr(a, b)
    r_full = f.spearman_brown(r_half)
    print(f"n={n} (players sufficient in both halves)")
    print(f"opponent-adjusted return clutch: r_half={r_half:+.4f} (p={p:.4f})  r_full(SB)={r_full:.4f}")

    return {'tour': tour, 'n': n, 'r_half': r_half, 'p': p, 'r_full': r_full,
            'fallback_a': fallback_a, 'fallback_b': fallback_b}


def main():
    results = []
    for tour in ['atp', 'wta']:
        r = run_tour(tour)
        if r:
            results.append(r)

    print(f"\n{'=' * 70}\nSUMMARY (vs. existing return-clutch reliability constructions)\n{'=' * 70}")
    reference = {
        'atp': {'quartile': 0.231, 'continuous_slope': 0.256, 'shrinkage': 0.371},
        'wta': {'quartile': 0.055, 'continuous_slope': -0.026, 'shrinkage': 0.132},
    }
    for r in results:
        ref = reference[r['tour']]
        print(f"{r['tour'].upper():4s}  quartile={ref['quartile']:.3f}  "
              f"continuous-slope={ref['continuous_slope']:+.3f}  "
              f"shrinkage={ref['shrinkage']:.3f}  "
              f"opponent-adjusted={r['r_full']:.3f}")


if __name__ == '__main__':
    main()
