"""
make_null_forest_figure.py -- forest plot of the primary entropy-clutch
correlation (r, 95% CI) across ATP, WTA, and pooled, split by role.

Visualizes what the abstract's prose already states in words: every cut
of the data clusters near zero. No new analysis -- reuses
formulas.fisher_z_meta_analysis() (already used for the pooled
Fisher z cross-check in docs/combined/pooled_regression.md) to compute a
95% CI for each individual (r, n) pair, and to recompute the two-tour
pooled estimate as a check that it reproduces the documented pooled_r
values before trusting the plot.

Primary r/n values are the documented, pre-registered p65 results:
docs/atp/04_regression_results/step4_results_writeup.md (ATP) and
docs/wta/wta_README.md (WTA).

Usage: python3 make_null_forest_figure.py
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from formulas import fisher_z_meta_analysis

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

PRIMARY = {
    'serve': {'ATP': (-0.0413, 91), 'WTA': (-0.259, 55)},
    'return': {'ATP': (+0.0164, 91), 'WTA': (+0.196, 55)},
}

# documented pooled Fisher z cross-check values, for a sanity check only
DOCUMENTED_POOLED = {
    'serve': (-0.124, -0.282, 0.041),
    'return': (+0.084, -0.081, 0.245),
}

COLORS = {'ATP': '#1f6f8b', 'WTA': '#c2554d', 'Pooled': '#444444'}


def row_for(label, r, n):
    res = fisher_z_meta_analysis([(r, n)])
    return {'label': label, 'r': res['r_pooled'], 'lo': res['ci_low'], 'hi': res['ci_high'], 'n': n}


def rows_for_role(role):
    rows = []
    for tour, (r, n) in PRIMARY[role].items():
        rows.append(row_for(tour, r, n))
    pooled = fisher_z_meta_analysis(list(PRIMARY[role].values()))
    rows.append({'label': 'Pooled', 'r': pooled['r_pooled'],
                 'lo': pooled['ci_low'], 'hi': pooled['ci_high'], 'n': 146})

    doc_r, doc_lo, doc_hi = DOCUMENTED_POOLED[role]
    assert abs(pooled['r_pooled'] - doc_r) < 0.001, f"{role} pooled r mismatch: {pooled['r_pooled']} vs {doc_r}"
    assert abs(pooled['ci_low'] - doc_lo) < 0.001, f"{role} pooled CI-low mismatch"
    assert abs(pooled['ci_high'] - doc_hi) < 0.001, f"{role} pooled CI-high mismatch"
    return rows


def plot_panel(ax, rows, title):
    ys = list(range(len(rows)))[::-1]
    for y, row in zip(ys, rows):
        color = COLORS[row['label']]
        ax.errorbar(row['r'], y, xerr=[[row['r'] - row['lo']], [row['hi'] - row['r']]],
                     fmt='o', color=color, capsize=4, markersize=7, linewidth=1.6)
    ax.axvline(0, color='gray', linestyle='--', linewidth=1, zorder=0)
    ax.set_yticks(ys)
    labels = []
    for r in rows:
        labels.append(f"{r['label']} (n={r['n']})")
    ax.set_yticklabels(labels)
    ax.set_xlabel('r (95% CI)')
    ax.set_title(title, fontsize=11)
    ax.set_xlim(-0.5, 0.5)


def main():
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.2))
    plot_panel(axes[0], rows_for_role('serve'), 'Serve')
    plot_panel(axes[1], rows_for_role('return'), 'Return')
    fig.suptitle('Entropy-clutch correlation: every cut of the data near zero',
                 fontsize=11, y=1.03)
    fig.tight_layout()

    out_path = os.path.join(FIG_DIR, 'null_forest_figure.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
