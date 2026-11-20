"""
make_interpretation_figure.py -- Figure 3 of the full paper (two panels, no new analysis).

(a) 95% match-level bootstrap rank intervals, serve and return clutch, for the nine most charted ATP players in the pool
    (selection rule fixed in docs/combined/interpretation_additions_plan.md; most charted = charted_matches in
    results/atp/step2_full_pool_features.csv). Reads results/applications/a3c_cluster_bootstrap_players.csv.
(b) How often a top-quartile clutch label is right, from results/applications/label_accuracy.csv (normal-model
    projection), with the 0.70 and 0.90 reference cases computed by label_accuracy.accuracy.

Writes results/figures/interpretation_figure.png.   Usage: python src/figures/make_interpretation_figure.py
"""
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src', 'robustness'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from label_accuracy import accuracy

OUT = os.path.join(REPO_ROOT, 'results', 'figures', 'interpretation_figure.png')
SERVE, RETURN = '#1f6fb4', '#d9822b'
ATP, WTA, REF = '#4a6fa5', '#b4c7e0', '#8a8a8a'
INK, MUTED = '#222222', '#666666'


def panel_a(ax):
    ranks = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'applications', 'a3c_cluster_bootstrap_players.csv'))
    ranks = ranks[ranks.tour == 'atp']
    feats = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'atp', 'step2_full_pool_features.csv'))[['player', 'charted_matches']]
    top = feats.sort_values('charted_matches', ascending=False).head(9).reset_index(drop=True)
    n_pool = ranks[ranks.measure == 'serve'].shape[0]
    for i, r in top.iterrows():
        y = i
        for off, meas, col in ((-0.17, 'serve', SERVE), (0.17, 'return', RETURN)):
            q = ranks[(ranks.measure == meas) & (ranks.player == r['player'])].iloc[0]
            ax.plot([q['rank_lo'], q['rank_hi']], [y + off, y + off], color=col, lw=2.0, solid_capstyle='butt', zorder=2)
            ax.plot(q['rank'], y + off, 'o', color=col, ms=3.6, zorder=3, mec='white', mew=0.5)
    ax.axvline((n_pool + 1) / 2, color=MUTED, lw=0.7, ls=':', zorder=1)
    ax.text((n_pool + 1) / 2, -0.75, 'middle of pool', fontsize=6.3, color=MUTED, ha='center', va='bottom')
    labels = [f"{p.split()[-1]} ({int(m)})" for p, m in zip(top['player'], top['charted_matches'])]
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(labels)
    ax.set_ylim(len(top) - 0.4, -0.95)
    ax.set_xlim(0, n_pool + 1)
    ax.set_xlabel('Rank among 91 ATP players (1 = most clutch)')
    ax.set_title('(a) A named player\'s rank is wide open', loc='left', fontsize=7.5, fontweight='bold')
    ax.grid(axis='x', alpha=0.2)
    ax.tick_params(length=2)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.plot([], [], color=SERVE, lw=2.0, label='Serve')
    ax.plot([], [], color=RETURN, lw=2.0, label='Return')
    ax.legend(loc='upper left', bbox_to_anchor=(0.0, 0.93), fontsize=6.3, frameon=False, handlelength=1.4, borderaxespad=0.1)


def panel_b(ax):
    la = pd.read_csv(os.path.join(REPO_ROOT, 'results', 'applications', 'label_accuracy.csv'))
    cats = [('Serve clutch', 'Serve quartile clutch'), ('Return clutch', 'Return quartile clutch'),
            ('Errors, all shots', 'R2 Unforced-error clutch, all shots'), ('Winners, all shots', 'R3 Winner clutch, all shots')]
    rows = []
    for nice, lab in cats:
        for tour in ('atp', 'wta'):
            x = la[(la.tour == tour) & (la.label == lab)].iloc[0]
            rows.append((nice, tour, x.precision * 100, x.precision_lo * 100, x.precision_hi * 100))
    refs = [('Reliability 0.70', 0.70), ('Reliability 0.90', 0.90)]
    ypos, y = [], 0.0
    ticks, ticklabels = [], []
    for ci, (nice, _) in enumerate(cats):
        for k, tour in enumerate(('atp', 'wta')):
            _, _, v, lo, hi = rows[ci * 2 + k]
            yy = y + (-0.2 if k == 0 else 0.2)
            ax.barh(yy, v, height=0.36, color=ATP if tour == 'atp' else WTA, zorder=2)
            ax.plot([lo, hi], [yy, yy], color=INK, lw=0.9, zorder=3)
            ax.plot([lo, lo], [yy - 0.07, yy + 0.07], color=INK, lw=0.9, zorder=3)
            ax.plot([hi, hi], [yy - 0.07, yy + 0.07], color=INK, lw=0.9, zorder=3)
            ax.text(max(hi, v) + 1.5, yy, f"{v:.0f}%", va='center', fontsize=6.3, color=INK)
        ticks.append(y)
        ticklabels.append(nice)
        y += 1.0
    y += 0.3
    for nice, rho in refs:
        v = accuracy(rho)[0] * 100
        ax.barh(y, v, height=0.5, color=REF, zorder=2, hatch='////', edgecolor='white', lw=0)
        ax.text(v + 1.5, y, f"{v:.0f}%", va='center', fontsize=6.3, color=INK)
        ticks.append(y)
        ticklabels.append(nice)
        y += 1.0
    ax.axvline(25, color=MUTED, lw=0.8, ls='--', zorder=1)
    ax.text(25.8, -0.78, '25% by chance', fontsize=6.3, color=MUTED, ha='left', va='bottom')
    ax.set_yticks(ticks)
    ax.set_yticklabels(ticklabels)
    ax.set_ylim(y - 0.5, -0.9)
    ax.set_xlim(0, 100)
    ax.set_xlabel('Players labelled top quartile who truly are (%)')
    ax.set_title('(b) A top-quartile label is often wrong', loc='left', fontsize=7.5, fontweight='bold')
    ax.grid(axis='x', alpha=0.2)
    ax.tick_params(length=2)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ATP, label='ATP'), Patch(color=WTA, label='WTA')], loc='center right', bbox_to_anchor=(1.0, 0.55), fontsize=6.3, frameon=False, handlelength=1.2, borderaxespad=0.1)


def main():
    plt.rcParams.update({'font.size': 7, 'axes.labelsize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.8})
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 3.0), gridspec_kw={'width_ratios': [1.0, 1.0]})
    panel_a(a)
    panel_b(b)
    fig.tight_layout(w_pad=1.6)
    fig.savefig(OUT, dpi=220, facecolor='white')
    print(f"Wrote {OUT}")


if __name__ == '__main__':
    main()
