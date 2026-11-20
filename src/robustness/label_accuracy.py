"""
label_accuracy.py -- how often is a clutch label right? (plan: docs/combined/shot_extension_preregistration.md, part B)

Model: observed score X = true score T + independent noise, both standardized and normal; corr(X, T) = sqrt(rho) and the
correlation between two equally long records is rho, where rho is the full-length (Spearman-Brown) reliability. For the
"top-quartile label" (X above its 75th percentile) exact bivariate-normal probabilities:
  precision    P(T in the top quartile | X in the top quartile)
  gross error  P(T below the median    | X in the top quartile)
  repeat       P(X' in the top quartile | X in the top quartile), X' from a fresh record of the same length
(chance: 25%, 50%, 25%). Evaluated at each outcome's random-split median reliability and at its 2.5th and 97.5th percentile
(negative rho set to 0, rho capped at 0.99). A derived projection, not a test.

    python src/robustness/label_accuracy.py
Reads the committed reliability CSVs; writes results/applications/label_accuracy.csv
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy.stats import norm, multivariate_normal

import applications_analyses as aa

Z = norm.ppf(0.75)


def _phi2(a, b, c):
    c = float(np.clip(c, -0.9999, 0.9999))
    return multivariate_normal(mean=[0, 0], cov=[[1, c], [c, 1]]).cdf([a, b])


def both_top(c):
    return 1 - 2 * norm.cdf(Z) + _phi2(Z, Z, c)


def accuracy(rho):
    rho = float(np.clip(rho, 0.0, 0.99))
    c = np.sqrt(rho)
    precision = both_top(c) / 0.25
    gross = (0.5 - _phi2(0.0, Z, c)) / 0.25
    repeat = both_top(rho) / 0.25
    return precision, gross, repeat


def main():
    d = aa.OUT_DIR
    a = pd.read_csv(os.path.join(d, 'ext_a_random_splits.csv'))
    a = a[a.measure.isin(['Serve quartile clutch', 'Return quartile clutch', 'BLR (faithful, primary)', 'Pooled LR'])]
    a = a.rename(columns={'measure': 'label'})
    a['label'] = a['label'].replace({'BLR (faithful, primary)': 'BLR (faithful)', 'Pooled LR': 'Pooled LR (exploratory)'})
    b = pd.read_csv(os.path.join(d, 'allshots_reliability.csv'))
    b = b[~b.outcome.isin(['serve_clutch', 'return_clutch'])]
    c = pd.read_csv(os.path.join(d, 'shot_extension_reliability.csv'))
    parts = [a[['tour', 'label', 'median', 'p2_5', 'p97_5']], b[['tour', 'label', 'median', 'p2_5', 'p97_5']],
             c[['tour', 'label', 'median', 'p2_5', 'p97_5']]]
    t = pd.concat(parts, ignore_index=True).dropna(subset=['median'])
    rows = []
    for _, r in t.iterrows():
        m, lo, hi = accuracy(r['median']), accuracy(r['p2_5']), accuracy(r['p97_5'])
        rows.append({'tour': r['tour'], 'label': r['label'], 'reliability_median': r['median'],
                     'reliability_p2_5': r['p2_5'], 'reliability_p97_5': r['p97_5'],
                     'precision': m[0], 'precision_lo': lo[0], 'precision_hi': hi[0],
                     'gross_error': m[1], 'gross_error_lo': hi[1], 'gross_error_hi': lo[1],
                     'repeat': m[2], 'repeat_lo': lo[2], 'repeat_hi': hi[2]})
    out = pd.DataFrame(rows)
    # self-check against a direct simulation at three reliabilities
    rng = np.random.default_rng(7)
    for rho in (0.24, 0.53, 0.70):
        n = 1_000_000
        T = rng.standard_normal(n)
        e = np.sqrt((1 - rho) / rho)
        x1, x2 = T + e * rng.standard_normal(n), T + e * rng.standard_normal(n)
        qa, qb = x1 >= np.quantile(x1, 0.75), x2 >= np.quantile(x2, 0.75)
        tq = T >= np.quantile(T, 0.75)
        sim = (tq[qa].mean(), (T < 0)[qa].mean(), qb[qa].mean())
        ex = accuracy(rho)
        print(f"SELF-CHECK rho {rho:.2f}: exact {ex[0]:.3f} {ex[1]:.3f} {ex[2]:.3f}  simulated {sim[0]:.3f} {sim[1]:.3f} {sim[2]:.3f}")
        if max(abs(np.array(ex) - np.array(sim))) > 0.01:
            raise SystemExit('self-check failed')
    print(out.round(3).to_string(index=False))
    out.to_csv(os.path.join(d, 'label_accuracy.csv'), index=False)
    print('=== RUN END')


if __name__ == '__main__':
    main()
