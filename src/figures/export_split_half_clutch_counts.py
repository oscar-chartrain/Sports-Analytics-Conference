"""
export_split_half_clutch_counts.py -- adds the per-half leverage-bucket
point counts (n_{role}_high_leverage / n_{role}_low_leverage) to the
already-exported results/figures/split_half_raw_{tour}.csv files, needed
for shrinkage_reliability.py's per-player sampling-variance weighting.

Purely additive, like export_split_half_data.py: reuses
split_half_reliability.py's functions unchanged, and only calls
build_clutch_half() (not build_entropy_half()), since this check needs
no entropy values, only clutch scores' underlying point counts. Skipping
the entropy extraction pass is what makes this meaningfully faster than
export_split_half_data.py's full run.

Usage: python3 export_split_half_clutch_counts.py
Needs the raw MCP data already present locally in results/{tour}/, same
as split_half_reliability.py, and the split_half_raw_{tour}.csv files
already produced by export_split_half_data.py.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'robustness'))

import pandas as pd

import split_half_reliability as shr

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')


def export_tour(tour):
    existing_path = os.path.join(FIG_DIR, f'split_half_raw_{tour}.csv')
    existing = pd.read_csv(existing_path)

    players = shr.load_pool(tour)
    matches, points = shr.load_raw(tour)
    half_map, relevant_matches = shr.split_matches(matches, players)
    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]

    print(f"[{tour}] computing clutch halves (counts only, no entropy)...")
    clutch_a = shr.build_clutch_half(relevant_matches, relevant_points, players, half_map, 'A')
    clutch_b = shr.build_clutch_half(relevant_matches, relevant_points, players, half_map, 'B')

    count_cols = ['n_serve_high_leverage', 'n_serve_low_leverage',
                  'n_return_high_leverage', 'n_return_low_leverage']
    rows = []
    for p in players:
        row = {'player': p}
        for suffix, clutch_df in [('a', clutch_a), ('b', clutch_b)]:
            if p in clutch_df.index:
                for col in count_cols:
                    row[f'{col}_{suffix}'] = clutch_df.loc[p, col]
        rows.append(row)
    counts_df = pd.DataFrame(rows)

    merged = existing.merge(counts_df, on='player', how='left')
    merged.to_csv(existing_path, index=False)
    print(f"Updated {existing_path} ({len(merged)} rows, added {len(count_cols) * 2} count columns)")


if __name__ == '__main__':
    for t in ['atp', 'wta']:
        export_tour(t)
