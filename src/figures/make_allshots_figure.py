"""
make_allshots_figure.py -- Figure 4 of the paper: split-half reliability of
clutch measured on every kind of shot, by tour.

Reads results/applications/allshots_reliability.csv (written by
src/robustness/all_shots_analyses.py). Each row is one outcome: the dot is the
median Spearman-Brown reliability over 1,000 random balanced splits and the
line is the 2.5th to 97.5th percentile. The dotted line is the 0.70 threshold
used throughout the paper. Colours are the validated ATP/WTA pair used in the
other figures.
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(REPO_ROOT, 'results', 'applications', 'allshots_reliability.csv')
OUT = os.path.join(REPO_ROOT, 'results', 'figures', 'allshots_reliability_figure.png')
COLORS = {'atp': '#1b78a3', 'wta': '#c2554d'}
NAMES = {'atp': 'ATP (91 players)', 'wta': 'WTA (55 players)'}

ROWS = [  # (outcome key, axis label, group)
    ('serve_clutch', 'Serve points, whole point', 0),
    ('return_clutch', 'Return points, whole point', 0),
    ('R1_rally_point', 'Rally-decided points (R1)', 1),
    ('R2_error_all', 'Unforced errors, all shots (R2)', 2),
    ('R3_winner_all', 'Winners, all shots (R3)', 2),
    ('R4_error_forehand', 'Errors, forehand (R4)', 3),
    ('R5_error_backhand', 'Errors, backhand (R5)', 3),
    ('R6_error_slice', 'Errors, slice (R6)', 3),
    ('R7_error_net', 'Errors, net game (R7)', 3),
    ('R8_double_fault', 'Double faults, serve (R8)', 4),
    ('R9_ace', 'Aces, serve (R9)', 4),
]


def main():
    df = pd.read_csv(SRC)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    offset = {'atp': -0.17, 'wta': 0.17}
    last_group = 0
    for i, (key, label, grp) in enumerate(ROWS):
        if grp != last_group:
            ax.axhline(i - 0.5, color='0.88', linewidth=0.8, zorder=0)
            last_group = grp
        for tour in ('atp', 'wta'):
            row = df[(df['tour'] == tour) & (df['outcome'] == key)].iloc[0]
            y = i + offset[tour]
            if pd.isna(row['median']):
                ax.text(-0.52, y, 'not estimable (too few shots)', fontsize=7.5, color=COLORS[tour],
                        va='center', ha='left')
                continue
            ax.plot([row['p2_5'], row['p97_5']], [y, y], color=COLORS[tour], linewidth=1.6, zorder=2,
                    solid_capstyle='round')
            ax.scatter([row['median']], [y], s=46, color=COLORS[tour], zorder=3,
                       edgecolors='white', linewidths=0.8)
    ax.axvline(0.70, color='0.35', linestyle=':', linewidth=1.2, zorder=1)
    ax.text(0.705, -0.75, 'acceptable\n(0.70)', fontsize=8, color='0.3', va='top', ha='left')
    ax.axvline(0.0, color='0.8', linewidth=0.8, zorder=0)
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([r[1] for r in ROWS], fontsize=9)
    ax.set_ylim(len(ROWS) - 0.4, -1.3)
    ax.set_xlim(-0.55, 0.9)
    ax.set_xlabel('Split-half reliability (Spearman-Brown); dot = median, line = 95% range over 1,000 random splits',
                  fontsize=8.5)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', labelsize=9)
    handles = [plt.Line2D([0], [0], marker='o', color=COLORS[t], linewidth=1.6, markersize=6,
                          markeredgecolor='white', label=NAMES[t]) for t in ('atp', 'wta')]
    ax.legend(handles=handles, loc='upper left', frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches='tight')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
