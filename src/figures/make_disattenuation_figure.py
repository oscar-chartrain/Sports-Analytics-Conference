"""
make_disattenuation_figure.py -- visualizes the disattenuated (true-score)
TOST equivalence bounds from
docs/atp/04_regression_results/disattenuated_equivalence_bounds.md: for
each tour/role, the observed-scale equivalence bound on |r| widens once
corrected for both variables' own split-half reliability, and WTA return's
corrected bound exceeds 1 -- a correlation cannot exceed 1 in magnitude, so
a bound past that point is vacuous, not just loose.

No new analysis -- reuses disattenuated_equivalence_bounds.py's own
tightest_tost_bound() binary search and its already-documented, cross-checked
quartile-reliability dictionaries unchanged, so this figure cannot silently
drift from the numbers already reported in docs/. Recomputes the ATP bounds
and asserts them against DOCUMENTED_ATP_BOUNDS before trusting anything
plotted, the same cross-check the source script itself performs.

Uses the quartile (primary, pre-registered) clutch reliabilities, matching
split_half_reliability_figure.png's basis -- not the shrinkage-corrected
version -- so the two figures stay on the same reliability footing.

Usage: python3 make_disattenuation_figure.py
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'robustness'))
import disattenuated_equivalence_bounds as deb

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

COLORS = {'atp': '#1f6f8b', 'wta': '#c2554d'}
LABELS = {'atp': 'ATP', 'wta': 'WTA'}
ROWS = [('atp', 'serve'), ('atp', 'return'), ('wta', 'serve'), ('wta', 'return')]


def compute_bounds():
    """Observed-scale and quartile-reliability disattenuated bounds for
    all 4 tour/role combinations, recomputed from real per-player data."""
    observed, true = {}, {}
    for tour in ['atp', 'wta']:
        df = deb.load_merged(tour)
        for role in ['serve', 'return']:
            x, y = deb.get_role_data(df, role)
            b_obs, _ = deb.tightest_tost_bound(x, y)
            rel_x = deb.ENTROPY_RELIABILITY[tour]
            rel_y = deb.CLUTCH_RELIABILITY['quartile'][(tour, role)]
            attenuation = (rel_x * rel_y) ** 0.5
            observed[(tour, role)] = b_obs
            true[(tour, role)] = b_obs / attenuation

    for role in ['serve', 'return']:
        documented = deb.DOCUMENTED_ATP_BOUNDS[role]
        computed = observed[('atp', role)]
        assert abs(computed - documented) < 0.002, (
            f"ATP {role} observed bound mismatch: {computed:.4f} vs "
            f"documented {documented:.4f} -- do not trust this figure")
    return observed, true


def main():
    observed, true = compute_bounds()

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    n = len(ROWS)
    ys = list(range(n))[::-1]

    for y, (tour, role) in zip(ys, ROWS):
        b_obs, b_true = observed[(tour, role)], true[(tour, role)]
        color = COLORS[tour]
        ax.plot([b_obs, b_true], [y, y], color=color, linewidth=2, zorder=1,
                solid_capstyle='round')
        ax.scatter([b_obs], [y], color=color, s=70, zorder=3, marker='o')
        ax.scatter([b_true], [y], facecolors='white', edgecolors=color,
                   linewidths=2, s=70, zorder=3, marker='o')
        ax.annotate(f'{b_obs:.2f} → {b_true:.2f}',
                    xy=(max(b_obs, b_true), y), xytext=(8, 0),
                    textcoords='offset points', va='center', fontsize=9,
                    color=color)

    # A correlation can't exceed 1 in magnitude -- a bound landing past
    # that point isn't weak evidence, it's no evidence (vacuous).
    ax.axvspan(1.0, 2.05, color='0.88', zorder=0)
    ax.axvline(1.0, color='0.55', linewidth=1, zorder=0)
    ax.text(1.03, n - 0.7, 'impossible for a\ncorrelation (vacuous)',
            fontsize=8, color='0.35', va='top')

    ax.axvline(0.3, color='gray', linestyle=':', linewidth=1, zorder=0)
    ax.text(0.3, -0.75, "Cohen's “medium” (0.3)", fontsize=8,
            color='gray', ha='center', va='bottom')

    ax.set_yticks(ys)
    ax.set_yticklabels([f'{LABELS[t]} {r.capitalize()}' for t, r in ROWS])
    ax.set_xlim(0, 2.05)
    ax.set_ylim(-1.1, n - 1 + 1.1)
    ax.set_xlabel('Equivalence bound on |r| (TOST, 95%)')

    ax.scatter([], [], color='0.3', s=70, marker='o', label='Observed-scale bound')
    ax.scatter([], [], facecolors='white', edgecolors='0.3', linewidths=2,
               s=70, marker='o', label='True-score bound (disattenuated)')
    ax.legend(loc='lower right', fontsize=8.5, frameon=False)

    fig.suptitle('Correcting the equivalence bound for measurement error',
                 fontsize=11, y=1.02)
    fig.tight_layout()

    out_path = os.path.join(FIG_DIR, 'disattenuation_figure.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f'Wrote {out_path}')
    for tour, role in ROWS:
        b_obs, b_true = observed[(tour, role)], true[(tour, role)]
        flag = '  ** VACUOUS **' if b_true >= 1.0 else ''
        print(f'{LABELS[tour]:4s}{role:7s}: {b_obs:.4f} -> {b_true:.4f}{flag}')


if __name__ == '__main__':
    main()
