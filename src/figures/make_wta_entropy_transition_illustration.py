"""
make_wta_entropy_transition_illustration.py -- WTA counterpart to
make_entropy_transition_illustration.py (the ATP/Sinner-Alcaraz version).
Same purpose: make "conditional Shannon entropy" concrete by plotting
the actual (preceding shot -> this shot) transition probability matrix
a player's entropy number is computed from.

Player pair: Iga Swiatek and Bianca Andreescu, not Sinner/Alcaraz's WTA
"equivalent" in any narrative sense (no such pair is named anywhere in
this project's docs or abstract) -- chosen instead for the two things
that actually matter for this illustration: both are well-charted
(226 and 186 matches, both far above the 40-match qualifying floor) and
they show the clearest entropy contrast among well-charted WTA players
(0.778 vs 0.817), which is what a reader needs to see visually to
understand what "more/less predictable" looks like cell by cell. A
current-rivalry pair (Swiatek/Sabalenka) was considered and rejected:
Sabalenka has only 57 charted matches and an entropy value 0.002 away
from Swiatek's -- correct, but visually indistinguishable, which would
undercut the figure's one job.

Not one of the abstract's two figures. For
docs/wta/wta_README.md, where there's no word or figure limit.

No new analysis. Reuses step2_entropy_pipeline.get_player_shot_transitions()
and compute_transition_entropy() unchanged. Unlike the ATP version, there
is no prose-documented per-player entropy value to check against in
docs/wta/ (only the pooled outputs are documented), so this script
instead asserts its recomputed conditional_normalized entropy for both
players against the already-committed, pipeline-produced
results/wta/wta_full_pool_features.csv -- the same cross-check
discipline, against the closest thing WTA has to a documented ground
truth. The heatmap shows only the 6 core context rows, same caveat as
the ATP version regarding the small serve/lob/other context bucket.

Needs the raw MCP WTA points files locally (results/wta/charting-w-points-*.csv,
results/wta/charting-w-matches.csv) -- see DATA.md; not committed to the repo.

Usage: run from inside results/wta/:
    cd results/wta && python3 ../../src/figures/make_wta_entropy_transition_illustration.py
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))
import parsing as pr
import data_io as dio
from step2_entropy_pipeline import get_player_shot_transitions, compute_transition_entropy

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

PLAYERS = ['Iga Swiatek', 'Bianca Andreescu']
GROUND_TRUTH_PATH = os.path.join(REPO_ROOT, 'results', 'wta', 'wta_full_pool_features.csv')

CELL_LABELS = ['FH-1', 'FH-2', 'FH-3', 'BH-1', 'BH-2', 'BH-3']


def build_matrix(transitions_df, player):
    """Row-normalized P(current | context) over the 6 core cells only --
    see the ATP script for why (small serve/lob/other context bucket
    dropped from the display, kept in the entropy cross-check)."""
    p_trans = transitions_df[transitions_df['target_player'] == player]
    mat = np.zeros((len(pr.ENTROPY_CATEGORIES), len(pr.ENTROPY_CATEGORIES)))
    for i, ctx in enumerate(pr.ENTROPY_CATEGORIES):
        sub = p_trans[p_trans['context'] == ctx]
        n = len(sub)
        if n == 0:
            continue
        counts = sub.groupby('current').size()
        for j, cur in enumerate(pr.ENTROPY_CATEGORIES):
            mat[i, j] = counts.get(cur, 0) / n
    return mat


def plot_panel(ax, mat, player, entropy_val):
    im = ax.imshow(mat, cmap='Blues', vmin=0, vmax=mat.max())
    ax.set_xticks(range(6))
    ax.set_xticklabels(CELL_LABELS, fontsize=8)
    ax.set_yticks(range(6))
    ax.set_yticklabels(CELL_LABELS, fontsize=8)
    ax.set_xlabel('This shot')
    ax.set_ylabel('Preceding shot (context)')
    ax.set_title(f'{player}\nconditional entropy = {entropy_val:.2f}', fontsize=10.5)
    for i in range(6):
        for j in range(6):
            val = mat[i, j]
            color = 'white' if val > mat.max() * 0.6 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=7, color=color)
    return im


def main():
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH).set_index('player')['conditional_normalized_entropy'].to_dict()

    matches = dio.load_matches('charting-w-matches.csv')
    points = dio.load_points_data(decades=('2020s', '2010s', 'to-2009'), gender='w')
    transitions = get_player_shot_transitions(matches, points, PLAYERS)

    entropy_vals = {}
    for player in PLAYERS:
        result = compute_transition_entropy(transitions, player)
        entropy_vals[player] = result['conditional_normalized']
        documented = ground_truth[player]
        diff = abs(result['conditional_normalized'] - documented)
        assert diff < 0.001, (
            f"{player} conditional entropy mismatch: {result['conditional_normalized']:.4f} "
            f"vs wta_full_pool_features.csv's {documented:.4f} -- do not trust this figure")

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
    for ax, player in zip(axes, PLAYERS):
        mat = build_matrix(transitions, player)
        im = plot_panel(ax, mat, player, entropy_vals[player])

    fig.suptitle(
        'What conditional entropy measures: P(this shot | preceding shot) -- WTA\n'
        "Swiatek's rows are more sharply peaked (lower entropy); Andreescu's spread wider (higher entropy) -- neither is \"no pattern\"",
        fontsize=10.5, y=1.06)
    fig.tight_layout()
    cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
    cbar.set_label('P(this shot | preceding shot)', fontsize=9)

    fig.text(
        0.5, -0.05,
        "FH/BH = forehand/backhand. Direction 1/2/3, per the Match Charting Project's own shot\n"
        "notation: 1 = toward a right-hander's forehand side, 2 = down the middle, 3 = toward a\n"
        "right-hander's backhand side (mirrored for left-handed players, so the same code always\n"
        "means the same court side regardless of who hit the shot).",
        ha='center', va='top', fontsize=8, color='0.3')

    out_path = os.path.join(FIG_DIR, 'wta_entropy_transition_illustration.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f'Wrote {out_path}')
    for player in PLAYERS:
        print(f'{player}: conditional_normalized entropy = {entropy_vals[player]:.4f} '
              f'(wta_full_pool_features.csv: {ground_truth[player]:.4f})')


if __name__ == '__main__':
    main()
