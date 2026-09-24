"""
rerun_primary_regression.py -- minimal reproduction of the Step 4 numbers
============================================================================
Given an existing {tour}_merged.csv (produced by run_pipeline.py), reproduce
exactly the numbers reported in the results write-up, with no data fetching
and no pipeline orchestration -- just the regression itself. Useful for a
reviewer who wants to check the arithmetic without re-running the full
data pipeline.

Usage: python3 rerun_primary_regression.py atp_merged.csv
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd
import statsmodels.api as sm
from scipy import stats

import formulas as f


def main(merged_csv_path):
    df = pd.read_csv(merged_csv_path)
    print(f"n = {len(df)}\n")

    for role in ['serve', 'return']:
        y = df[f'{role}_clutch_p65']
        X = sm.add_constant(df['conditional_normalized_entropy'])
        m = sm.OLS(y, X).fit()
        r, p_r = stats.pearsonr(df['conditional_normalized_entropy'], y)
        ci = m.conf_int().loc['conditional_normalized_entropy']
        print(f"{role}: r={r:+.4f} (p={p_r:.4f}), beta={m.params['conditional_normalized_entropy']:+.4f}, "
              f"95% CI=[{ci[0]:.4f}, {ci[1]:.4f}], R2={m.rsquared:.4f}")

    print()
    for role in ['serve', 'return']:
        lo, hi = 0.001, 0.9
        col = f'{role}_clutch_p65'
        for _ in range(60):
            mid = (lo + hi) / 2
            res = f.tost_equivalence(df['conditional_normalized_entropy'], df[col], -mid, mid)
            if res['equivalent_at_alpha']:
                hi = mid
            else:
                lo = mid
        print(f"{role} TOST equivalence bound: |r| < {hi:.3f}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = 'atp_merged.csv'
    main(csv_path)
