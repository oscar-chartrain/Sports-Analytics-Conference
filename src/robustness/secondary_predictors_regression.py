"""
secondary_predictors_regression.py -- tests the four secondary/exploratory
predictors pre-registered in step3_variable_preregistration.md
(net_play_escalation_delta, wide_serve_escalation_delta,
return_depth_shift_delta, dropshot_rate) against clutch score, per the
pre-registration in
docs/atp/04_regression_results/secondary_predictors_regression.md.

Unlike every other follow-up check in this project, this one needs no
raw MCP data and no new extraction: all four predictors were already
computed in Step 2 and sit unused in the primary feature files. This
script only merges and correlates existing, already-committed numbers.

Usage: python3 secondary_predictors_regression.py
"""
import os

import pandas as pd
from scipy import stats

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

PREDICTORS = [
    ('net_play_escalation_delta', 'net_play_sufficient'),
    ('wide_serve_escalation_delta', 'serve_zone_sufficient'),
    ('return_depth_shift_delta', 'return_depth_sufficient'),
    ('dropshot_rate', 'dropshot_rate_sufficient'),
]
ROLES = ['serve', 'return']

TOUR_FILES = {
    'atp': ('results/atp/step2_full_pool_features.csv', 'results/atp/step3_clutch_features.csv'),
    'wta': ('results/wta/wta_full_pool_features.csv', 'results/wta/wta_clutch_features.csv'),
}


def load_merged(tour):
    feat_path, clutch_path = TOUR_FILES[tour]
    feat = pd.read_csv(os.path.join(REPO_ROOT, feat_path))
    clutch = pd.read_csv(os.path.join(REPO_ROOT, clutch_path))
    return feat.merge(clutch, on='player', how='inner')


def main():
    n_comparisons = len(PREDICTORS) * len(ROLES) * len(TOUR_FILES)
    bonferroni_alpha = 0.05 / n_comparisons

    results = []
    for tour in ['atp', 'wta']:
        df = load_merged(tour)
        for predictor, pred_suff_col in PREDICTORS:
            for role in ROLES:
                outcome_col = f'{role}_clutch_p65'
                outcome_suff_col = f'{role}_clutch_p65_sufficient'
                sub = df[df[pred_suff_col] & df[outcome_suff_col]].dropna(subset=[predictor, outcome_col])
                n = len(sub)
                r, p = stats.pearsonr(sub[predictor], sub[outcome_col])
                survives = p < bonferroni_alpha
                results.append({
                    'tour': tour.upper(), 'predictor': predictor, 'role': role,
                    'n': n, 'r': r, 'p': p, 'survives_bonferroni': survives,
                })
                if survives:
                    survives_note = '  ** SURVIVES **'
                else:
                    survives_note = ''
                print(f"{tour.upper():4s} {predictor:28s} {role:7s} n={n:3d}  r={r:+.4f}  p={p:.4f}"
                      f"{survives_note}")

    print(f"\n{'=' * 80}")
    print(f"Bonferroni-corrected alpha across {n_comparisons} comparisons: {bonferroni_alpha:.6f}")
    n_survive = sum(1 for r in results if r['survives_bonferroni'])
    print(f"Comparisons surviving correction: {n_survive}/{n_comparisons}")

    return results


if __name__ == '__main__':
    main()
