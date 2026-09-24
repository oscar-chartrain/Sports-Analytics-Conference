"""
continuous_slope_reliability.py -- does a continuous-slope clutch
construction improve outcome reliability over the quartile-split version?
============================================================================
Implements the follow-up check pre-registered in
docs/atp/04_regression_results/split_half_reliability.md ("Follow-up:
does a continuous-slope construction improve outcome reliability?").

Reuses split_half_reliability.py's data loading and match-splitting (the
exact same half-A/half-B assignment, so results are directly comparable
to the original quartile-only check) and
build_clutch_features(return_points=True) to get the point-level leverage
table without duplicating any hitter-attribution/leverage logic.

For each player/role, both constructions are computed from the SAME
underlying points, gated by the SAME n >= MIN_OBS*4 total-point floor, so
any reliability difference is attributable to the construction choice,
not to comparing different player samples:
  - quartile: win_rate(top leverage quartile) - win_rate(bottom quartile),
    identical formula to quartile_clutch() in core/features.py
  - slope: OLS coefficient of 'won' on leverage_p65 across ALL of a
    player's points for that role, not just the quartile extremes

The quartile values computed here are cross-checked against
build_clutch_features()'s own summary output as a correctness check
before trusting either construction's reliability numbers.

Usage: python3 continuous_slope_reliability.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

import features as feat
import formulas as f
import split_half_reliability as sr


def compute_both(role_pts, min_obs=feat.MIN_OBS):
    """Quartile-split score and continuous-slope score from the same
    points, gated by the identical n >= min_obs*4 floor."""
    sub = role_pts.dropna(subset=['leverage_p65', 'won'])
    n = len(sub)
    if n < min_obs * 4:
        return np.nan, np.nan, n, False

    q_low = sub['leverage_p65'].quantile(0.25)
    q_high = sub['leverage_p65'].quantile(0.75)
    low = sub[sub['leverage_p65'] <= q_low]
    high = sub[sub['leverage_p65'] >= q_high]
    quartile_score = high['won'].mean() - low['won'].mean()

    X = sm.add_constant(sub['leverage_p65'])
    slope_score = sm.OLS(sub['won'], X).fit().params['leverage_p65']

    return quartile_score, slope_score, n, True


def build_half_both(matches_df, points_df, players, half_map, half_label):
    ids = set()  # match_ids belonging to this half
    for mid, h in half_map.items():
        if h == half_label:
            ids.add(mid)
    sub_matches = matches_df[matches_df['match_id'].isin(ids)]
    sub_points = points_df[points_df['match_id'].isin(ids)]
    summary, pts = feat.build_clutch_features(sub_matches, sub_points, players, return_points=True)
    summary = summary.set_index('player')

    quartile, slope = {}, {}
    for player in players:
        serve_pts = pts[pts['server'] == player].copy()
        serve_pts['won'] = serve_pts['server_won_point']
        return_pts = pts[pts['returner'] == player].copy()
        return_pts['won'] = 1 - return_pts['server_won_point']

        for role, role_pts in [('serve', serve_pts), ('return', return_pts)]:
            q, s, n, suf = compute_both(role_pts)
            if suf:
                quartile[(player, role)] = q
                slope[(player, role)] = s

    return quartile, slope, summary


def cross_check(quartile, summary, tour, half_label):
    """Verify the quartile values recomputed here match
    build_clutch_features()'s own summary output exactly, before trusting
    either construction's reliability numbers."""
    max_diff = 0.0
    n_checked = 0
    for (player, role), value in quartile.items():
        official = summary.loc[player, f'{role}_clutch_p65']
        if pd.notna(official):
            max_diff = max(max_diff, abs(value - official))
            n_checked += 1
    print(f"  Cross-check ({tour.upper()} half {half_label}): {n_checked} values compared "
          f"against build_clutch_features()'s own output, max diff = {max_diff:.2e}")


def reliability(name, half_a, half_b):
    keys = sorted(set(half_a) & set(half_b))
    n = len(keys)
    if n < 4:
        print(f"{name}: n={n}, too small to compute reliability")
        return np.nan
    a_list = []
    b_list = []
    for k in keys:
        a_list.append(half_a[k])
        b_list.append(half_b[k])
    a = np.array(a_list)
    b = np.array(b_list)
    r, p = stats.pearsonr(a, b)
    r_full = f.spearman_brown(r)
    print(f"{name}: n={n}, split-half r={r:+.4f} (p={p:.4f}), Spearman-Brown full-length={r_full:.4f}")
    return r_full


def run_tour(tour):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players = sr.load_pool(tour)
    matches, points = sr.load_raw(tour)
    half_map, relevant_matches = sr.split_matches(matches, players)
    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]

    print("Building both constructions on half A...")
    quartile_a, slope_a, summary_a = build_half_both(relevant_matches, relevant_points, players, half_map, 'A')
    cross_check(quartile_a, summary_a, tour, 'A')

    print("Building both constructions on half B...")
    quartile_b, slope_b, summary_b = build_half_both(relevant_matches, relevant_points, players, half_map, 'B')
    cross_check(quartile_b, summary_b, tour, 'B')

    for role in ['serve', 'return']:
        qa, qb, sa, sb = {}, {}, {}, {}
        for (p, r), v in quartile_a.items():
            if r == role:
                qa[p] = v
        for (p, r), v in quartile_b.items():
            if r == role:
                qb[p] = v
        for (p, r), v in slope_a.items():
            if r == role:
                sa[p] = v
        for (p, r), v in slope_b.items():
            if r == role:
                sb[p] = v
        print(f"\n{tour.upper()} {role}:")
        r_quartile = reliability("  quartile (existing construction)", qa, qb)
        r_slope = reliability("  continuous-slope (new)          ", sa, sb)
        if not (np.isnan(r_quartile) or np.isnan(r_slope)):
            delta = r_slope - r_quartile
            print(f"  Delta (slope - quartile): {delta:+.4f}")


if __name__ == '__main__':
    for tour in ['atp', 'wta']:
        run_tour(tour)
