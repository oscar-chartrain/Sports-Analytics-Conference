"""
confound_check_era_surface.py -- tests whether the primary entropy-clutch
null result survives controlling for player era and surface mix, per the
pre-registration in
docs/atp/04_regression_results/confound_check_era_surface.md.

No raw points data needed -- only each tour's small match-metadata file
(already local) for era/surface, and the already-committed primary
feature/clutch files. Cheap: runs in seconds, no background job needed.

Usage: python3 confound_check_era_surface.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

import data_io as dio

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

TOUR_FILES = {
    'atp': ('results/atp/step2_full_pool_features.csv', 'results/atp/step3_clutch_features.csv',
            'results/atp/charting-m-matches.csv'),
    'wta': ('results/wta/wta_full_pool_features.csv', 'results/wta/wta_clutch_features.csv',
            'results/wta/charting-w-matches.csv'),
}

VALID_SURFACES = {'Hard', 'Clay', 'Grass'}

# Already-documented simple bivariate results, for direct comparison.
# Source: docs/atp/04_regression_results/step4_results_writeup.md (ATP),
#         docs/wta/wta_README.md (WTA).
SIMPLE_RESULT = {
    ('atp', 'serve'): {'r': -0.0413, 'p': 0.6972},
    ('atp', 'return'): {'r': +0.0164, 'p': 0.8774},
    ('wta', 'serve'): {'r': -0.259, 'p': 0.056},
    ('wta', 'return'): {'r': +0.196, 'p': 0.151},
}


def compute_player_covariates(matches_df, players):
    rows = []
    for player in players:
        pm = matches_df[(matches_df['Player 1'] == player) | (matches_df['Player 2'] == player)]

        dates = pd.to_numeric(pm['Date'], errors='coerce').dropna()
        years = (dates // 10000).astype(int)
        if len(years):
            era_proxy = years.median()
        else:
            era_proxy = np.nan

        surf = pm[pm['Surface'].isin(VALID_SURFACES)]
        n_surf = len(surf)
        if n_surf:
            pct_clay = (surf['Surface'] == 'Clay').sum() / n_surf
            pct_grass = (surf['Surface'] == 'Grass').sum() / n_surf
        else:
            pct_clay = np.nan
            pct_grass = np.nan

        rows.append({'player': player, 'era_proxy': era_proxy,
                     'pct_clay': pct_clay, 'pct_grass': pct_grass,
                     'n_matches_for_surface': n_surf, 'n_matches_for_era': len(years)})
    return pd.DataFrame(rows)


def load_merged(tour):
    feat_path, clutch_path, matches_path = TOUR_FILES[tour]
    feat = pd.read_csv(os.path.join(REPO_ROOT, feat_path))
    clutch = pd.read_csv(os.path.join(REPO_ROOT, clutch_path))
    matches = dio.load_matches(os.path.join(REPO_ROOT, matches_path))

    players = feat['player'].tolist()
    covariates = compute_player_covariates(matches, players)

    merged = feat.merge(clutch, on='player', how='inner').merge(covariates, on='player', how='inner')
    return merged


def run_regression(df, role):
    outcome_col = f'{role}_clutch_p65'
    outcome_suff = f'{role}_clutch_p65_sufficient'
    sub = df[df['transition_entropy_sufficient'] & df[outcome_suff]].dropna(
        subset=['conditional_normalized_entropy', outcome_col, 'era_proxy', 'pct_clay', 'pct_grass'])

    n = len(sub)
    era_centered = sub['era_proxy'] - sub['era_proxy'].mean()
    X = pd.DataFrame({
        'entropy': sub['conditional_normalized_entropy'].values,
        'era_centered': era_centered.values,
        'pct_clay': sub['pct_clay'].values,
        'pct_grass': sub['pct_grass'].values,
    })
    X = sm.add_constant(X)
    y = sub[outcome_col].values
    model = sm.OLS(y, X).fit()

    return {
        'n': n,
        'entropy_coef': model.params['entropy'],
        'entropy_se': model.bse['entropy'],
        'entropy_t': model.tvalues['entropy'],
        'entropy_p': model.pvalues['entropy'],
        'r_squared': model.rsquared,
    }


def main():
    all_results = []
    for tour in ['atp', 'wta']:
        df = load_merged(tour)
        n_missing_era = df['era_proxy'].isna().sum()
        n_missing_surface = df['pct_clay'].isna().sum()
        print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
        print(f"Players missing era_proxy: {n_missing_era}, missing surface mix: {n_missing_surface}")

        for role in ['serve', 'return']:
            result = run_regression(df, role)
            simple = SIMPLE_RESULT[(tour, role)]
            print(f"\n{role}:")
            print(f"  simple bivariate:      r={simple['r']:+.4f}  p={simple['p']:.4f}")
            print(f"  multivariate (n={result['n']}): entropy coef={result['entropy_coef']:+.4f}  "
                  f"se={result['entropy_se']:.4f}  t={result['entropy_t']:+.3f}  p={result['entropy_p']:.4f}  "
                  f"model R^2={result['r_squared']:.4f}")
            all_results.append({'tour': tour, 'role': role, **result, 'simple_r': simple['r'], 'simple_p': simple['p']})

    n_comparisons = len(all_results)
    bonferroni_alpha = 0.05 / n_comparisons
    print(f"\n{'=' * 70}\nBonferroni-corrected alpha across {n_comparisons} comparisons: {bonferroni_alpha:.4f}")
    for r in all_results:
        survives = r['entropy_p'] < bonferroni_alpha
        if survives:
            verdict = '** SURVIVES **'
        else:
            verdict = '(does not survive)'
        print(f"{r['tour'].upper():4s} {r['role']:7s}  multivariate p={r['entropy_p']:.4f}  {verdict}")


if __name__ == '__main__':
    main()
