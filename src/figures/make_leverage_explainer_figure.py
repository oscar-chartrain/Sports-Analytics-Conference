"""
make_leverage_explainer_figure.py -- explains what a high-leverage point is and how a clutch score is built.

Panel (a): leverage (how much winning rather than losing the point moves the server's chance of winning the
match, in percentage points) for the same point scores in three match situations, from the paper's win-probability
engine (constant 65% serve-point win probability, best of three).
Panel (b): the distribution of leverage over every ATP point in the pool, with the bottom and top quartiles that
define the "low" and "high" leverage points of the clutch score.
"""
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src', 'core'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src', 'robustness'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import formulas as f
import applications_analyses as aa

OUT = os.path.join(REPO_ROOT, 'results', 'figures', 'leverage_explainer_figure.png')
FMT = {'sets_to_win': 2, 'super_tb_target': 7, 'final_tb_code': '7'}
SCORES = ['0-0', '30-0', '15-15', '0-30', '40-0', '30-30', '15-40', '40-30', '30-40', '40-40', 'AD-40', '40-AD']
CONTEXTS = [
    ('Opening set, 1-1 in games', dict(Set1=0, Set2=0, Gm1=1, Gm2=1), '#1b78a3', 'o'),
    ('Second set, 4-4, server a set up', dict(Set1=1, Set2=0, Gm1=4, Gm2=4), '#c4640a', 's'),
    ('Deciding set, 5-5', dict(Set1=1, Set2=1, Gm1=5, Gm2=5), '#8a3fb0', '^'),
]


def lev(score, ctx):
    row = dict(Pts=score, Svr=1, **ctx)
    return 100 * f.compute_leverage(row, FMT, 0.65)


def main():
    plt.rcParams.update({'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 7.5, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6})
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.4), gridspec_kw={'width_ratios': [1.25, 1]})
    base = [lev(sc, CONTEXTS[0][1]) for sc in SCORES]
    order = np.argsort(base)
    scores = [SCORES[i] for i in order]
    x = np.arange(len(scores))
    for name, ctx, col, mk in CONTEXTS:
        y = [lev(sc, ctx) for sc in scores]
        a.scatter(x, y, color=col, marker=mk, s=16, edgecolors='white', linewidths=0.4, label=name, zorder=3)
    a.axvspan(len(scores) - 2.5, len(scores) - 0.5, color='0.92', zorder=0)
    a.text(len(scores) - 1.5, 41.5, 'break point', fontsize=6.5, ha='center', va='top', color='0.35')
    a.set_ylim(-1, 42)
    a.set_xticks(x)
    a.set_xticklabels(scores, rotation=45, ha='right', fontsize=6.5)
    a.set_ylabel('Leverage (pp of match-win chance)', fontsize=6.5)
    a.set_xlabel('Score in the game (server first)', fontsize=6.5)
    a.set_title('(a) The same score matters more late in a close match', fontsize=7.5, loc='left')
    a.legend(frameon=False, fontsize=6.5, loc='upper left')
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    a.tick_params(axis='y', labelsize=8)

    players, matches, half_map, summary, pts = aa.load_tour('atp')
    L = 100 * pts['leverage_p65'].values
    L = L[~np.isnan(L)]
    q25, q75 = np.percentile(L, [25, 75])
    bins = np.linspace(0, np.percentile(L, 99.5), 70)
    w = np.ones(len(L)) / len(L) * 100
    b.hist(L, bins=bins, weights=w, color='0.8', edgecolor='white', linewidth=0.3)
    b.axvspan(0, q25, color='#c4640a', alpha=0.25, linewidth=0)
    b.axvspan(q75, bins[-1], color='#1b78a3', alpha=0.25, linewidth=0)
    b.axvline(q25, color='#c4640a', linewidth=1.2)
    b.axvline(q75, color='#1b78a3', linewidth=1.2)
    top = b.get_ylim()[1]
    b.text(q25 / 2, top * 0.93, 'low\n(bottom\nquarter)', color='#8a4306', fontsize=6.5, ha='center', va='top')
    b.text((q75 + bins[-1]) / 2, top * 0.93, 'high\n(top quarter)', color='#124f6e', fontsize=6.5, ha='center', va='top')
    b.set_xlabel('Leverage of the point (pp)', fontsize=6.5)
    b.set_ylabel('Share of points (%)', fontsize=6.5)
    b.set_title('(b) The clutch score compares the two ends', fontsize=7.5, loc='left')
    for s in ('top', 'right'):
        b.spines[s].set_visible(False)
    b.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches='tight')
    print(f'Wrote {OUT}; quartile cut-offs {q25:.2f} and {q75:.2f} pp')


if __name__ == '__main__':
    main()
