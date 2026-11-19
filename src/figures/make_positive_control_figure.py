"""
make_positive_control_figure.py -- reliability against the size of a planted stable clutch difference.

Reads results/applications/positive_control.csv (written by src/robustness/positive_control.py).
Each line is one outcome: the median split-half reliability (Spearman-Brown) over 1,000 simulated
splits at each planted true standard deviation (percentage points), with the 2.5th to 97.5th
percentile band. The dotted line is the 0.70 threshold. The filled marker on each line is the
estimated true spread of the real data (Table 3); the hollow marker beside it is the reliability
actually observed there, so the two agree when the simulation reproduces the data.
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(REPO_ROOT, 'results', 'applications', 'positive_control.csv')
OUT = os.path.join(REPO_ROOT, 'results', 'figures', 'positive_control_figure.png')
STYLE = {'S': ('#1b78a3', 'o', 'Serve'), 'Rt': ('#c4640a', 's', 'Return'), 'R1': ('#8a3fb0', '^', 'Rally points')}
OBS = {('atp', 'S'): 0.53, ('atp', 'Rt'): 0.24, ('atp', 'R1'): 0.44,
       ('wta', 'S'): 0.41, ('wta', 'Rt'): 0.27, ('wta', 'R1'): 0.25}
TITLES = {'atp': 'ATP (91 players)', 'wta': 'WTA (55 players)'}


def main():
    df = pd.read_csv(SRC)
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.5), sharey=True)
    for ax, tour in zip(axes, ('atp', 'wta')):
        for k, (col, mk, name) in STYLE.items():
            g = df[(df['tour'] == tour) & (df['outcome'] == k)]
            gr = g[g['kind'] == 'grid'].sort_values('planted_sd_pp')
            ax.fill_between(gr['planted_sd_pp'], gr['p2_5'], gr['p97_5'], color=col, alpha=0.07, linewidth=0)
            ax.plot(gr['planted_sd_pp'], gr['median'], color=col, linewidth=1.6, marker=mk, markersize=4.5,
                    markeredgecolor='white', markeredgewidth=0.6, label=name, zorder=3)
            e = g[g['kind'] == 'estimated'].iloc[0]
            ax.scatter([e['planted_sd_pp']], [OBS[(tour, k)]], s=38, facecolors='white', edgecolors=col,
                       linewidths=1.4, zorder=4)
        ax.axhline(0.70, color='0.35', linestyle=':', linewidth=1.2, zorder=1)
        ax.axhline(0, color='0.85', linewidth=0.8, zorder=0)
        ax.set_title(TITLES[tour], fontsize=10, loc='left')
        ax.set_xlim(-0.1, 6.1)
        ax.set_ylim(-0.25, 1.0)
        ax.set_xlabel('Planted true spread between players (SD, percentage points)', fontsize=8.5)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8.5)
    axes[0].set_ylabel('Split-half reliability (median, 95% range)', fontsize=8.5)
    axes[0].text(0.05, 0.725, 'acceptable (0.70)', fontsize=7.5, color='0.3', va='bottom')
    h = [plt.Line2D([0], [0], color=c, marker=m, linewidth=1.6, markersize=5, markeredgecolor='white', label=n)
         for c, m, n in STYLE.values()]
    h.append(plt.Line2D([0], [0], color='0.3', marker='o', markerfacecolor='white', linewidth=0, markersize=6,
                        label='Real data (estimated spread, observed reliability)'))
    axes[1].legend(handles=h, loc='lower right', frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches='tight')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
