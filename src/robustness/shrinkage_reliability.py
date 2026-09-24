"""
shrinkage_reliability.py -- tests whether an empirical-Bayes shrinkage
estimator improves the clutch score's split-half reliability, per the
pre-registration in
docs/atp/04_regression_results/shrinkage_reliability.md.

For each tour, role, and half independently (no information crosses
between halves): shrink each player's raw quartile clutch score toward
that half's pool mean, weighted by how much data backs their own
estimate (players with more high/low-leverage points get shrunk less).
Then compute split-half reliability (Pearson r between shrunk half-A and
shrunk half-B, Spearman-Brown corrected) exactly as for the raw quartile
and continuous-slope constructions already reported in
split_half_reliability.md.

Reads results/figures/split_half_raw_{atp,wta}.csv, which must already
have the n_{role}_{high,low}_leverage_{a,b} columns added by
export_split_half_clutch_counts.py.

Usage: python3 shrinkage_reliability.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
import pandas as pd
from scipy import stats

import formulas as f

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')


def shrink_half(raw, n_high, n_low):
    """Independent empirical-Bayes shrinkage for one half's values.
    raw, n_high, n_low: aligned arrays (same players, this half only)."""
    var_i = 0.25 * (1.0 / n_high + 1.0 / n_low)
    mean_raw = raw.mean()
    var_across = raw.var(ddof=1)
    mean_var_i = var_i.mean()
    tau2 = max(0.0, var_across - mean_var_i)
    b_i = tau2 / (tau2 + var_i)
    shrunk = mean_raw + b_i * (raw - mean_raw)
    return shrunk, tau2, var_i.mean(), b_i.mean()


def run_tour_role(df, tour, role):
    cols = [f'{role}_clutch_a', f'{role}_clutch_b',
            f'n_{role}_high_leverage_a', f'n_{role}_low_leverage_a',
            f'n_{role}_high_leverage_b', f'n_{role}_low_leverage_b']
    sub = df.dropna(subset=cols).copy()
    n = len(sub)
    if n < 4:
        print(f"{tour.upper()} {role}: n={n}, too small")
        return None

    shrunk_a, tau2_a, meanvar_a, meanb_a = shrink_half(
        sub[f'{role}_clutch_a'].values,
        sub[f'n_{role}_high_leverage_a'].values,
        sub[f'n_{role}_low_leverage_a'].values,
    )
    shrunk_b, tau2_b, meanvar_b, meanb_b = shrink_half(
        sub[f'{role}_clutch_b'].values,
        sub[f'n_{role}_high_leverage_b'].values,
        sub[f'n_{role}_low_leverage_b'].values,
    )

    r_raw, _ = stats.pearsonr(sub[f'{role}_clutch_a'], sub[f'{role}_clutch_b'])
    r_shrunk, p_shrunk = stats.pearsonr(shrunk_a, shrunk_b)
    r_full_raw = f.spearman_brown(r_raw)
    r_full_shrunk = f.spearman_brown(r_shrunk)

    print(f"\n{tour.upper()} {role}: n={n}")
    print(f"  half A: tau^2={tau2_a:.6f}  mean(Var_i)={meanvar_a:.6f}  mean(B_i)={meanb_a:.3f}")
    print(f"  half B: tau^2={tau2_b:.6f}  mean(Var_i)={meanvar_b:.6f}  mean(B_i)={meanb_b:.3f}")
    print(f"  raw quartile:      r_half={r_raw:+.4f}  r_full(SB)={r_full_raw:.4f}")
    print(f"  shrunk (this check): r_half={r_shrunk:+.4f} (p={p_shrunk:.4f})  r_full(SB)={r_full_shrunk:.4f}")
    print(f"  delta (shrunk - raw), full-length: {r_full_shrunk - r_full_raw:+.4f}")

    return {
        'tour': tour, 'role': role, 'n': n,
        'r_full_raw': r_full_raw, 'r_full_shrunk': r_full_shrunk,
        'delta': r_full_shrunk - r_full_raw,
        'tau2_a': tau2_a, 'tau2_b': tau2_b,
        'mean_b_a': meanb_a, 'mean_b_b': meanb_b,
    }


def main():
    results = []
    for tour in ['atp', 'wta']:
        df = pd.read_csv(os.path.join(FIG_DIR, f'split_half_raw_{tour}.csv'))
        for role in ['serve', 'return']:
            r = run_tour_role(df, tour, role)
            if r:
                results.append(r)

    print(f"\n{'=' * 70}\nSUMMARY (vs. quartile / continuous-slope from split_half_reliability.md)\n{'=' * 70}")
    reference_quartile = {('atp', 'serve'): 0.572, ('atp', 'return'): 0.231,
                          ('wta', 'serve'): 0.578, ('wta', 'return'): 0.055}
    reference_slope = {('atp', 'serve'): 0.465, ('atp', 'return'): 0.256,
                        ('wta', 'serve'): 0.542, ('wta', 'return'): -0.026}
    for r in results:
        key = (r['tour'], r['role'])
        if abs(r['r_full_raw'] - reference_quartile[key]) < 0.005:
            match_note = 'yes'
        else:
            match_note = 'NO -- MISMATCH'
        print(f"{r['tour'].upper():4s} {r['role']:7s}  "
              f"quartile={reference_quartile[key]:.3f}  "
              f"continuous-slope={reference_slope[key]:+.3f}  "
              f"shrinkage={r['r_full_shrunk']:.3f}  "
              f"(matches doc's quartile figure: {match_note})")


if __name__ == '__main__':
    main()
