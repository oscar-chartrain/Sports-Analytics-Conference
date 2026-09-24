"""
make_reliability_figure.py -- builds the split-half reliability figure
for paper/abstract.md: entropy (the predictor), serve clutch, and return
clutch (the outcome, both roles) half-A/half-B scatter plots, side by
side, same axes convention.

Reads results/figures/split_half_raw_{atp,wta}.csv (produced by
export_split_half_data.py, which reuses split_half_reliability.py's own
functions unchanged) and makes no new calculation beyond the Pearson r
already reported in docs/atp/04_regression_results/split_half_reliability.md
-- this script is visualization only.

The legend reports the Spearman-Brown-corrected r_full (not the raw
split-half r) so the number shown here matches the number quoted in
paper/abstract.md's prose exactly (0.925/0.897 entropy, 0.572/0.578
serve clutch, 0.231/0.055 return clutch) -- a cold-read review flagged
the earlier raw-r legend as a source of apparent (if explained)
inconsistency with the text; showing the same statistic in both places
removes the discrepancy by construction instead of just annotating it.

spearman_brown() now lives in core/formulas.py (see that module's
docstring for the other four places this used to be copy-pasted).

Usage: python3 make_reliability_figure.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

import formulas as f

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

COLORS = {'atp': '#1f6f8b', 'wta': '#c2554d'}
LABELS = {'atp': 'ATP', 'wta': 'WTA'}


def load(tour):
    return pd.read_csv(os.path.join(FIG_DIR, f'split_half_raw_{tour}.csv'))


def plot_panel(ax, dfs, col, title):
    all_vals = []
    for tour, df in dfs.items():
        sub = df.dropna(subset=[f'{col}_a', f'{col}_b'])
        a, b = sub[f'{col}_a'], sub[f'{col}_b']
        r_half, _ = stats.pearsonr(a, b)
        r_full = f.spearman_brown(r_half)
        ax.scatter(a, b, s=22, alpha=0.75, color=COLORS[tour],
                   label=f'{LABELS[tour]} (r={r_full:.2f})', edgecolors='none')
        all_vals.extend([a.min(), a.max(), b.min(), b.max()])

    lo, hi = min(all_vals), max(all_vals)
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad
    ax.plot([lo, hi], [lo, hi], color='gray', linestyle='--', linewidth=1, zorder=0)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel('Half A')
    ax.set_ylabel('Half B')
    ax.set_title(title, fontsize=10.5)
    ax.legend(loc='upper left', fontsize=8, frameon=False)
    ax.set_aspect('equal', adjustable='box')


def main():
    dfs = {'atp': load('atp'), 'wta': load('wta')}

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    plot_panel(axes[0], dfs, 'entropy',
               'Predictor: conditional entropy\n(reliable)')
    plot_panel(axes[1], dfs, 'serve_clutch',
               'Outcome: serve clutch score\n(below acceptable)')
    plot_panel(axes[2], dfs, 'return_clutch',
               'Outcome: return clutch score\n(poor, esp. WTA)')
    fig.suptitle('Split-half reliability (Spearman-Brown corrected r): same player, two independent halves of their career',
                 fontsize=11, y=1.03)
    fig.tight_layout()

    out_path = os.path.join(FIG_DIR, 'split_half_reliability_figure.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
