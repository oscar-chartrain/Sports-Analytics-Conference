"""
disattenuated_equivalence_bounds.py -- computes the true-score
(reliability-corrected) TOST equivalence bound for the primary
entropy-clutch null result, per the method in
docs/atp/04_regression_results/disattenuated_equivalence_bounds.md.

Finds the tightest observed-score bound via binary search over
formulas.tost_equivalence() (unmodified, called repeatedly) on the
real per-player data -- not on hand-transcribed r/n values -- so ATP's
recomputed bound can be checked against the already-documented figures
(serve < 0.213, return < 0.189) before trusting the new WTA numbers this
script produces for the first time.

Usage: python3 disattenuated_equivalence_bounds.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd

import formulas as f

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

TOUR_FILES = {
    'atp': ('results/atp/step2_full_pool_features.csv', 'results/atp/step3_clutch_features.csv'),
    'wta': ('results/wta/wta_full_pool_features.csv', 'results/wta/wta_clutch_features.csv'),
}

# Already-documented Spearman-Brown-corrected reliabilities.
# Source: docs/atp/04_regression_results/split_half_reliability.md (quartile)
#         docs/atp/04_regression_results/shrinkage_reliability.md (shrinkage)
ENTROPY_RELIABILITY = {'atp': 0.925, 'wta': 0.897}
CLUTCH_RELIABILITY = {
    'quartile': {
        ('atp', 'serve'): 0.572, ('atp', 'return'): 0.231,
        ('wta', 'serve'): 0.578, ('wta', 'return'): 0.055,
    },
    'shrinkage': {
        ('atp', 'serve'): 0.594, ('atp', 'return'): 0.371,
        ('wta', 'serve'): 0.624, ('wta', 'return'): 0.132,
    },
}

# ATP-only bounds already documented in step4_results_writeup.md, for
# cross-checking this script's recomputation before trusting it.
DOCUMENTED_ATP_BOUNDS = {'serve': 0.213, 'return': 0.189}


def load_merged(tour):
    feat_path, clutch_path = TOUR_FILES[tour]
    feat = pd.read_csv(os.path.join(REPO_ROOT, feat_path))
    clutch = pd.read_csv(os.path.join(REPO_ROOT, clutch_path))
    return feat.merge(clutch, on='player', how='inner')


def get_role_data(df, role):
    outcome_col = f'{role}_clutch_p65'
    outcome_suff = f'{role}_clutch_p65_sufficient'
    sub = df[df['transition_entropy_sufficient'] & df[outcome_suff]].dropna(
        subset=['conditional_normalized_entropy', outcome_col])
    return sub['conditional_normalized_entropy'].values, sub[outcome_col].values


def tightest_tost_bound(x, y, alpha=0.05, lo=1e-4, hi=0.999, tol=1e-5):
    """Binary search for the smallest symmetric bound B such that
    tost_equivalence(x, y, -B, B, alpha) succeeds. Reuses the existing,
    unmodified tost_equivalence() function rather than a hand-derived
    closed-form, to avoid introducing new, unvalidated math."""
    r, _ = None, None
    # r must clear the bound itself for TOST to ever succeed
    import scipy.stats as stats
    r, _ = stats.pearsonr(x, y)
    lo = max(lo, abs(r) + 1e-6)
    if not f.tost_equivalence(x, y, -hi, hi, alpha)['equivalent_at_alpha']:
        return None  # no bound within (0,1) achieves equivalence
    while hi - lo > tol:
        mid = (lo + hi) / 2
        result = f.tost_equivalence(x, y, -mid, mid, alpha)
        if result['equivalent_at_alpha']:
            hi = mid
        else:
            lo = mid
    return hi, r


def main():
    observed_bounds = {}
    for tour in ['atp', 'wta']:
        df = load_merged(tour)
        for role in ['serve', 'return']:
            x, y = get_role_data(df, role)
            n = len(x)
            bound, r = tightest_tost_bound(x, y)
            observed_bounds[(tour, role)] = bound
            print(f"{tour.upper():4s} {role:7s} n={n:3d}  r={r:+.4f}  "
                  f"observed-score TOST bound: |r| < {bound:.4f}")

    print(f"\n{'=' * 70}\nCross-check against documented ATP bounds\n{'=' * 70}")
    for role in ['serve', 'return']:
        computed = observed_bounds[('atp', role)]
        documented = DOCUMENTED_ATP_BOUNDS[role]
        diff = abs(computed - documented)
        if diff < 0.002:
            status = 'MATCH'
        else:
            status = 'MISMATCH -- DO NOT TRUST'
        print(f"ATP {role:7s}: recomputed={computed:.4f}  documented={documented:.4f}  "
              f"diff={diff:.4f}  [{status}]")

    print(f"\n{'=' * 70}\nDisattenuated (true-score) equivalence bounds\n{'=' * 70}")
    for tour in ['atp', 'wta']:
        for role in ['serve', 'return']:
            b_obs = observed_bounds[(tour, role)]
            rel_x = ENTROPY_RELIABILITY[tour]
            for version in ['quartile', 'shrinkage']:
                rel_y = CLUTCH_RELIABILITY[version][(tour, role)]
                attenuation = (rel_x * rel_y) ** 0.5
                b_true = b_obs / attenuation
                if b_true >= 1.0:
                    flag = '  ** EXCEEDS 1 -- VACUOUS BOUND **'
                else:
                    flag = ''
                print(f"{tour.upper():4s} {role:7s} ({version:9s}): "
                      f"rel_x={rel_x:.3f} rel_y={rel_y:.3f} attenuation={attenuation:.3f}  "
                      f"B_obs={b_obs:.4f} -> B_true={b_true:.4f}{flag}")


if __name__ == '__main__':
    main()
