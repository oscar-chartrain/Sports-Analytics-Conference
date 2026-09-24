"""
power_and_robustness.py -- power/MDES, match-count-weighted regression, and
MIN_OBS threshold sensitivity for the primary ATP/WTA regression
============================================================================
Implements the three checks pre-registered in
docs/atp/04_regression_results/power_and_robustness.md, in that order.

Checks 1 and 2 and the clutch-side half of check 3 only need the existing
committed CSVs. The entropy-side half of check 3 re-derives per-context
transition counts via step2_entropy_pipeline.get_player_shot_transitions(),
which needs the raw MCP data present locally in results/{tour}/ (this repo
never commits it; fetch per the root README's Reproduce section first).

Usage: python3 power_and_robustness.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats

import data_io as dio
import formulas as f
import step2_entropy_pipeline as s2

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load_atp_merged():
    features = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'atp', 'step2_full_pool_features.csv'))
    clutch = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'atp', 'step3_clutch_features.csv'))
    merged = features.merge(clutch, on='player', how='inner', validate='one_to_one')
    merged['tour'] = 'atp'
    return merged


def load_wta_merged():
    merged = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'wta', 'wta_merged.csv'))
    merged['tour'] = 'wta'
    return merged


def gated(df, role, min_obs=None):
    """Sufficiency gating for {role}_clutch_p65. With min_obs=None, uses
    the committed {role}_clutch_p65_sufficient flag (MIN_OBS=30, the
    original). With an explicit min_obs, re-derives sufficiency from the
    saved bucket-size columns (n_{role}_high_leverage / n_{role}_low_leverage)
    instead -- valid because the quartile split itself doesn't depend on
    MIN_OBS, only whether the resulting score is flagged reliable, and
    every player in the committed data already cleared the original
    MIN_OBS=30*4 total-point floor (confirmed: 100% sufficiency at 30 for
    both tours), so no player's true bucket size was ever suppressed by
    the early-return path in quartile_clutch()."""
    base = df[df['transition_entropy_sufficient']]
    if min_obs is None:
        return base[base[f'{role}_clutch_p65_sufficient']].copy()
    nh = base[f'n_{role}_high_leverage']
    nl = base[f'n_{role}_low_leverage']
    return base[(nh >= min_obs) & (nl >= min_obs)].copy()


# =============================================================================
# 1. Power / MDES
# =============================================================================

def run_power_analysis():
    print(f"\n{'=' * 70}\n1. POWER ANALYSIS / MDES\n{'=' * 70}")
    sizes = [(91, 'ATP'), (55, 'WTA'), (146, 'Pooled')]
    print("Minimum detectable effect size (80% power, alpha=0.05, two-sided):")
    for n, label in sizes:
        mdes = f.mdes_correlation(n)
        print(f"  {label:8s} (n={n:3d}): |r| >= {mdes:.3f}")

    print("\nAchieved power to detect Cohen's conventional effect sizes:")
    for n, label in sizes:
        for r_true, size_name in [(0.1, 'small'), (0.3, 'medium'), (0.5, 'large')]:
            power = f.power_for_correlation(n, r_true)
            print(f"  {label:8s} (n={n:3d}): power for r={r_true} ({size_name}): {power:.1%}")


# =============================================================================
# 2. Match-count-weighted regression
# =============================================================================

def run_weighted_regression():
    print(f"\n{'=' * 70}\n2. MATCH-COUNT-WEIGHTED REGRESSION\n{'=' * 70}")
    atp = load_atp_merged()
    wta = load_wta_merged()
    for tour_name, df in [('ATP', atp), ('WTA', wta)]:
        cutoff = df['charted_matches'].quantile(0.75)
        for role in ['serve', 'return']:
            clean = gated(df, role)
            y_col = f'{role}_clutch_p65'

            X = sm.add_constant(clean['conditional_normalized_entropy'])
            m_unweighted = sm.OLS(clean[y_col], X).fit()
            m_wls = sm.WLS(clean[y_col], X, weights=clean['charted_matches']).fit()

            print(f"\n{tour_name} {role}: n={len(clean)}")
            print(f"  Unweighted OLS: beta={m_unweighted.params['conditional_normalized_entropy']:+.4f}, "
                  f"p={m_unweighted.pvalues['conditional_normalized_entropy']:.4f}")
            print(f"  Weighted WLS:   beta={m_wls.params['conditional_normalized_entropy']:+.4f}, "
                  f"p={m_wls.pvalues['conditional_normalized_entropy']:.4f} "
                  f"(weights = charted_matches)")

            high_data = clean[clean['charted_matches'] >= cutoff]
            if len(high_data) >= 4:
                r, p = stats.pearsonr(high_data['conditional_normalized_entropy'], high_data[y_col])
                print(f"  High-data subsample (top quartile by charted_matches, "
                      f">={cutoff:.0f} matches, n={len(high_data)}): r={r:+.4f}, p={p:.4f}")
            else:
                print(f"  High-data subsample (>={cutoff:.0f} matches): n={len(high_data)}, too small to test")


# =============================================================================
# 3a. MIN_OBS sensitivity -- clutch-side gating (no data refetch needed)
# =============================================================================

def clutch_side_sensitivity():
    print(f"\n{'=' * 70}\n3a. MIN_OBS SENSITIVITY -- CLUTCH-SIDE GATING\n{'=' * 70}")
    atp = load_atp_merged()
    wta = load_wta_merged()
    for tour_name, df in [('ATP', atp), ('WTA', wta)]:
        for role in ['serve', 'return']:
            y_col = f'{role}_clutch_p65'
            print(f"\n{tour_name} {role}:")
            for min_obs in [20, 30, 50, 100]:
                clean = gated(df, role, min_obs=min_obs)
                if len(clean) >= 4:
                    r, p = stats.pearsonr(clean['conditional_normalized_entropy'], clean[y_col])
                    print(f"  MIN_OBS={min_obs:3d}: n={len(clean)}, r={r:+.4f}, p={p:.4f}")
                else:
                    print(f"  MIN_OBS={min_obs:3d}: n={len(clean)}, too small to test")


# =============================================================================
# 3b. MIN_OBS sensitivity -- entropy-side (per-context) gating
# =============================================================================

def entropy_side_sensitivity():
    print(f"\n{'=' * 70}\n3b. MIN_OBS SENSITIVITY -- ENTROPY-SIDE (PER-CONTEXT) GATING\n{'=' * 70}")
    for tour in ['atp', 'wta']:
        if tour == 'atp':
            gender = 'm'
            features_filename = 'step2_full_pool_features.csv'
        else:
            gender = 'w'
            features_filename = 'wta_full_pool_features.csv'
        results_dir = os.path.join(REPO_ROOT, 'results', tour)
        features_path = os.path.join(results_dir, features_filename)
        features = pd.read_csv(features_path)
        players = features['player'].tolist()

        old_cwd = os.getcwd()
        os.chdir(results_dir)
        try:
            matches = dio.load_matches(f'charting-{gender}-matches.csv')
            points = dio.load_points_data(decades=('2020s', '2010s', 'to-2009'), gender=gender)
        finally:
            os.chdir(old_cwd)

        relevant_matches = matches[matches['Player 1'].isin(players) | matches['Player 2'].isin(players)]
        target_ids = set(relevant_matches['match_id'])
        relevant_points = points[points['match_id'].isin(target_ids)]

        print(f"\nExtracting transitions for {tour.upper()} ({len(players)} players)...")
        transitions = s2.get_player_shot_transitions(relevant_matches, relevant_points, players)

        player_context_counts = {
            player: transitions[transitions['target_player'] == player].groupby('context').size()
            for player in players
        }

        for min_obs in [20, 30, 50, 100]:
            n_sufficient = sum(
                1 for counts in player_context_counts.values()
                if len(counts) > 0 and (counts >= min_obs).all()
            )
            print(f"  MIN_OBS={min_obs:3d}: {n_sufficient}/{len(players)} players sufficient on transition-entropy")


if __name__ == '__main__':
    run_power_analysis()
    run_weighted_regression()
    clutch_side_sensitivity()
    entropy_side_sensitivity()
