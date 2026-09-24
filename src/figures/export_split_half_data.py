"""
export_split_half_data.py -- dumps per-player half-A/half-B raw values
for entropy and clutch (serve/return) to CSV.

Purely additive: reuses split_half_reliability.py's functions unchanged
(same split, same MIN_OBS floor, same leverage engine at p=0.65). Adds no
new computation and changes no methodology; it just persists the
per-player values that script already computes internally but never
writes to disk, so they can be plotted (paper/abstract.md's reliability
figure).

Usage: python3 export_split_half_data.py
Needs the raw MCP data already present locally in results/{tour}/, same
as split_half_reliability.py.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'robustness'))

import pandas as pd

import split_half_reliability as shr

# Two levels up from src/figures/ to reach the actual repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def export_tour(tour):
    players = shr.load_pool(tour)
    matches, points = shr.load_raw(tour)
    half_map, relevant_matches = shr.split_matches(matches, players)
    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]

    print(f"[{tour}] computing entropy halves...")
    entropy_a = shr.build_entropy_half(relevant_matches, relevant_points, players, half_map, 'A')
    entropy_b = shr.build_entropy_half(relevant_matches, relevant_points, players, half_map, 'B')

    print(f"[{tour}] computing clutch halves...")
    clutch_a = shr.build_clutch_half(relevant_matches, relevant_points, players, half_map, 'A')
    clutch_b = shr.build_clutch_half(relevant_matches, relevant_points, players, half_map, 'B')

    rows = []
    for p in players:
        row = {'tour': tour, 'player': p}
        if p in entropy_a and p in entropy_b:
            row['entropy_a'] = entropy_a[p]
            row['entropy_b'] = entropy_b[p]
        for role in ['serve', 'return']:
            suff_col = f'{role}_clutch_p65_sufficient'
            if p in clutch_a.index and p in clutch_b.index:
                if clutch_a.loc[p, suff_col] and clutch_b.loc[p, suff_col]:
                    row[f'{role}_clutch_a'] = clutch_a.loc[p, f'{role}_clutch_p65']
                    row[f'{role}_clutch_b'] = clutch_b.loc[p, f'{role}_clutch_p65']
        rows.append(row)

    df = pd.DataFrame(rows)
    out_dir = os.path.join(REPO_ROOT, 'results', 'figures')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'split_half_raw_{tour}.csv')
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows)")


if __name__ == '__main__':
    for t in ['atp', 'wta']:
        export_tour(t)
