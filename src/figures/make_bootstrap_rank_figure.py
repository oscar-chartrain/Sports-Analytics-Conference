"""
make_bootstrap_rank_figure.py -- Figure 3 of the full paper: 95% bootstrap
rank intervals for every player in the ATP pool, serve and return clutch,
with Sinner, Alcaraz, Djokovic and Federer highlighted.

Reads results/applications/a3c_cluster_bootstrap_players.csv (written by
src/robustness/cluster_bootstrap_ranks.py); no new analysis. Writes
results/figures/bootstrap_rank_figure.png.

Usage: python3 make_bootstrap_rank_figure.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(REPO_ROOT, 'results', 'applications', 'a3c_cluster_bootstrap_players.csv')
OUT = os.path.join(REPO_ROOT, 'results', 'figures', 'bootstrap_rank_figure.png')

HIGHLIGHT = {
    'Jannik Sinner': '#d95f02',
    'Carlos Alcaraz': '#1b9e77',
    'Novak Djokovic': '#7570b3',
    'Roger Federer': '#e7298a',
}


def panel(ax, df, title):
    df = df.sort_values('rank').reset_index(drop=True)
    n = len(df)
    for i, row in df.iterrows():
        color = HIGHLIGHT.get(row['player'], '#b0b0b0')
        width = 2.2 if row['player'] in HIGHLIGHT else 0.9
        ax.plot([i + 1, i + 1], [row['rank_lo'], row['rank_hi']], color=color, lw=width * 0.7, zorder=2)
        ax.plot(i + 1, row['rank'], 'o', color=color, ms=2.6 if row['player'] in HIGHLIGHT else 1.4, zorder=3)
    ax.plot([1, n], [1, n], color='black', lw=0.6, ls=':', zorder=1)
    ax.set_xlim(0, n + 1)
    ax.set_ylim(n + 2, -1)
    ax.set_xlabel('Rank by point estimate (1 = most clutch)')
    ax.set_title(title, fontsize=7.5)
    ax.grid(alpha=0.2)


def main():
    df = pd.read_csv(SRC)
    atp = df[df['tour'] == 'atp']
    plt.rcParams.update({'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 7.5, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6})
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.4), sharey=True)
    panel(axes[0], atp[atp['measure'] == 'serve'], 'Serve clutch')
    panel(axes[1], atp[atp['measure'] == 'return'], 'Return clutch')
    axes[0].set_ylabel('Bootstrap rank (95% interval)')
    handles = [plt.Line2D([0], [0], color=c, lw=2.2, label=n) for n, c in HIGHLIGHT.items()]
    axes[1].legend(handles=handles, loc='lower left', fontsize=6, frameon=True)
    fig.suptitle('ATP pool (n = 91): 95% bootstrap rank intervals, B = 2,000', fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200)
    print(f"Wrote {OUT}")


if __name__ == '__main__':
    main()
