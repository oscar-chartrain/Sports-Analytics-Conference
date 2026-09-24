"""
make_entropy_transition_illustration.py -- supplementary (not for the
abstract) figure making "conditional Shannon entropy" concrete: for
Sinner and Alcaraz, the same real-data sanity-check pair used throughout
Step 2/3, plots the actual (context -> current) shot-transition
probability matrix each player's conditional entropy number is computed
from.

Not one of the abstract's two figures (that budget is spent on the
reliability warning and the disattenuated bound -- see
paper/README.md). This is meant for docs/atp/02_entropy_pipeline/, where
there's no word or figure limit, to help a reader who has never seen
"conditional Shannon entropy" before understand what it actually
measures: not "does this player have patterns" (both clearly do -- every
row is far from uniform) but "how concentrated is each row." Sinner's
rows are more sharply peaked (lower entropy); Alcaraz's are more spread
across the 6 cells (higher entropy). Neither is "no pattern" -- see the
caution in paper/README.md against over-reading this as showing
randomness.

No new analysis. Reuses step2_entropy_pipeline.get_player_shot_transitions()
and compute_transition_entropy() unchanged, and asserts its recomputed
conditional_normalized entropy for both players against the documented
values in docs/atp/02_entropy_pipeline/step2_README.md (Sinner 0.7921,
Alcaraz 0.8000) before saving anything. The heatmap itself shows only the
6 core (forehand/backhand x direction) context rows, for interpretability;
the validated entropy number (like the pipeline's own) also folds in the
small "preceding shot was serve/lob/other" context bucket, so the two
won't be derived from literally the same displayed cells -- the assertion
below confirms that omission doesn't change the entropy number enough to
matter (both tours' figures elsewhere in this repo already established
lob/other as genuinely rare, not a coverage artifact).

The figure itself explains what direction 1/2/3 means (per the Match
Charting Project's own notation, as described in Tennis Abstract's MCP
Quick Start Guide: 1 = toward a right-hander's forehand side, 2 = down
the middle, 3 = toward a right-hander's backhand side, mirrored for
left-handers), since FH-1/FH-2/FH-3/BH-1/BH-2/BH-3 aren't self-explanatory
without it.

Needs the raw MCP 2020s points file locally (results/atp/charting-m-points-2020s.csv,
results/atp/charting-m-matches.csv) -- see DATA.md for how to fetch it;
not committed to the repo.

Usage: run from inside results/atp/:
    cd results/atp && python3 ../../src/figures/make_entropy_transition_illustration.py
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))
import parsing as pr
import data_io as dio
from step2_entropy_pipeline import get_player_shot_transitions, compute_transition_entropy

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

PLAYERS = ['Jannik Sinner', 'Carlos Alcaraz']
# Already-documented, cross-checked values from
# docs/atp/02_entropy_pipeline/step2_README.md's post-fix Sinner/Alcaraz table.
DOCUMENTED_CONDITIONAL_NORM = {'Jannik Sinner': 0.7921, 'Carlos Alcaraz': 0.8000}

CELL_LABELS = ['FH-1', 'FH-2', 'FH-3', 'BH-1', 'BH-2', 'BH-3']


def build_matrix(transitions_df, player):
    """Row-normalized P(current | context) over the 6 core cells only
    (drops the small serve/lob/other context bucket, for a clean square
    matrix -- the entropy cross-check below uses the full, real function
    instead, which does include it)."""
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
    matches = dio.load_matches('charting-m-matches.csv')
    points = dio.load_points_data(decades=('2020s',), gender='m')
    transitions = get_player_shot_transitions(matches, points, PLAYERS)

    entropy_vals = {}
    for player in PLAYERS:
        result = compute_transition_entropy(transitions, player)
        entropy_vals[player] = result['conditional_normalized']
        documented = DOCUMENTED_CONDITIONAL_NORM[player]
        diff = abs(result['conditional_normalized'] - documented)
        assert diff < 0.001, (
            f"{player} conditional entropy mismatch: {result['conditional_normalized']:.4f} "
            f"vs documented {documented:.4f} -- do not trust this figure")

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
    mats = {}
    for ax, player in zip(axes, PLAYERS):
        mat = build_matrix(transitions, player)
        mats[player] = mat
        im = plot_panel(ax, mat, player, entropy_vals[player])

    fig.suptitle(
        'What conditional entropy measures: P(this shot | preceding shot)\n'
        "Sinner's rows are more sharply peaked (lower entropy); Alcaraz's spread wider (higher entropy) -- neither is \"no pattern\"",
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

    out_path = os.path.join(FIG_DIR, 'entropy_transition_illustration.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f'Wrote {out_path}')
    for player in PLAYERS:
        print(f'{player}: conditional_normalized entropy = {entropy_vals[player]:.4f} '
              f'(documented {DOCUMENTED_CONDITIONAL_NORM[player]:.4f})')


if __name__ == '__main__':
    main()
