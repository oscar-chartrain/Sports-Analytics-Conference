"""
pooled_regression.py -- combined ATP+WTA test of the primary hypothesis
==========================================================================
Implements the analysis pre-registered in docs/combined/pooled_regression.md
(written before this script was run). If something in the output is
surprising, that goes in the results section, not a change to the model
spec above it.

Reconstructs the ATP merged (entropy + clutch) table from the two separate
results/atp/ CSVs (no atp_merged.csv currently exists, see the root
README's reorg notes), loads results/wta/wta_merged.csv directly (already
merged), tags each with a tour column, and for each role (serve, return):

  Model A (interaction):   {role}_clutch_p65 ~ conditional_normalized_entropy * tour
  Model B (pooled, no interaction): {role}_clutch_p65 ~ conditional_normalized_entropy + tour

plus a Fisher z meta-analytic pooling of the two independent per-tour r's
as an assumption-light cross-check on Model B.

Usage: python3 pooled_regression.py
(run from anywhere, paths below are relative to the repo root)
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from scipy import stats

import formulas as f

# Two levels up from src/robustness/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load_atp():
    features = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'atp', 'step2_full_pool_features.csv'))
    clutch = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'atp', 'step3_clutch_features.csv'))
    merged = features.merge(clutch, on='player', how='inner', validate='one_to_one')
    merged['tour'] = 'atp'
    return merged


def load_wta():
    merged = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'wta', 'wta_merged.csv'))
    merged['tour'] = 'wta'
    return merged


def gated(df, role):
    suff_col = f'{role}_clutch_p65_sufficient'
    return df[df['transition_entropy_sufficient'] & df[suff_col]].copy()


def run_role(pooled, role):
    print(f"\n{'='*70}\n{role.upper()} (p65, pooled ATP+WTA)\n{'='*70}")
    clean = gated(pooled, role)
    n_atp = (clean['tour'] == 'atp').sum()
    n_wta = (clean['tour'] == 'wta').sum()
    print(f"n = {len(clean)} (ATP {n_atp}, WTA {n_wta}) after sufficiency gating")

    y_col = f'{role}_clutch_p65'

    # Model A: interaction (does the slope differ by tour?)
    model_a = smf.ols(f"{y_col} ~ conditional_normalized_entropy * tour", data=clean).fit()
    interact_term = None  # the coefficient name statsmodels gave the interaction term, e.g. "conditional_normalized_entropy:tour[T.wta]"
    for c in model_a.params.index:
        if ':' in c:
            interact_term = c
            break
    beta_interact = model_a.params[interact_term]
    p_interact = model_a.pvalues[interact_term]
    print(f"\nModel A (interaction): {interact_term}")
    print(f"  beta={beta_interact:+.4f}, p={p_interact:.4f}")
    if p_interact < 0.05:
        print("  SIGNIFICANT -- slopes differ by tour")
    else:
        print("  not significant -- no evidence slopes differ by tour")

    # Model B: pooled main effect (no interaction) -- only meaningful if A's interaction is null
    model_b = smf.ols(f"{y_col} ~ conditional_normalized_entropy + tour", data=clean).fit()
    beta_pooled = model_b.params['conditional_normalized_entropy']
    p_pooled = model_b.pvalues['conditional_normalized_entropy']
    ci = model_b.conf_int().loc['conditional_normalized_entropy']
    print(f"\nModel B (pooled main effect, common slope assumed):")
    print(f"  beta={beta_pooled:+.4f}, p={p_pooled:.4f}, 95% CI=[{ci[0]:.4f}, {ci[1]:.4f}], "
          f"R2={model_b.rsquared:.4f}, n={len(clean)}")

    # Meta-analytic cross-check: Fisher z pooling of the two independent per-tour r's
    atp_clean = clean[clean['tour'] == 'atp']
    wta_clean = clean[clean['tour'] == 'wta']
    r_atp, _ = stats.pearsonr(atp_clean['conditional_normalized_entropy'], atp_clean[y_col])
    r_wta, _ = stats.pearsonr(wta_clean['conditional_normalized_entropy'], wta_clean[y_col])
    meta = f.fisher_z_meta_analysis([(r_atp, len(atp_clean)), (r_wta, len(wta_clean))])
    print(f"\nFisher z meta-analytic pooling:")
    print(f"  ATP r={r_atp:+.4f} (n={len(atp_clean)}), WTA r={r_wta:+.4f} (n={len(wta_clean)})")
    print(f"  pooled r={meta['r_pooled']:+.4f}, 95% CI=[{meta['ci_low']:.4f}, {meta['ci_high']:.4f}], "
          f"p={meta['p_value']:.4f}, total n={meta['total_n']}")
    if meta['q_p_value'] < 0.05:
        heterogeneity_note = 'heterogeneous -- pooling questionable'
    else:
        heterogeneity_note = 'homogeneous -- pooling defensible'
    print(f"  Cochran's Q={meta['cochrans_q']:.4f} (df={meta['q_df']}), p={meta['q_p_value']:.4f} "
          f"({heterogeneity_note})")

    # Pooled TOST equivalence bound (n=146), same method as the ATP-only write-up
    lo, hi = 0.001, 0.9
    for _ in range(60):
        mid = (lo + hi) / 2
        res = f.tost_equivalence(clean['conditional_normalized_entropy'], clean[y_col], -mid, mid)
        if res['equivalent_at_alpha']:
            hi = mid
        else:
            lo = mid
    print(f"\nPooled TOST equivalence bound (n={len(clean)}): |r| < {hi:.3f} at 95% confidence")

    return {
        'role': role, 'n': len(clean), 'n_atp': n_atp, 'n_wta': n_wta,
        'interaction_beta': beta_interact, 'interaction_p': p_interact,
        'pooled_beta': beta_pooled, 'pooled_p': p_pooled,
        'pooled_ci_low': ci[0], 'pooled_ci_high': ci[1], 'pooled_r2': model_b.rsquared,
        'r_atp': r_atp, 'r_wta': r_wta, 'meta_r': meta['r_pooled'],
        'meta_ci_low': meta['ci_low'], 'meta_ci_high': meta['ci_high'], 'meta_p': meta['p_value'],
        'q': meta['cochrans_q'], 'q_p': meta['q_p_value'], 'tost_bound': hi,
    }


def main():
    atp = load_atp()
    wta = load_wta()
    pooled = pd.concat([atp, wta], ignore_index=True)

    results = []
    for role in ['serve', 'return']:
        results.append(run_role(pooled, role))

    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    for r in results:
        print(f"{r['role']}: interaction p={r['interaction_p']:.4f}  |  "
              f"pooled beta={r['pooled_beta']:+.4f} (p={r['pooled_p']:.4f})  |  "
              f"meta r={r['meta_r']:+.4f} (p={r['meta_p']:.4f})  |  "
              f"TOST bound |r|<{r['tost_bound']:.3f}")

    return results


if __name__ == '__main__':
    main()
