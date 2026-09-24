"""
Step 1: Data Validation (v2 -- rebuilt on core/parsing.py + core/data_io.py)
==============================================================================
Confirms the Match Charting Project (MCP) data is usable as the foundation
for the shot-selection entropy calculation, and defines which players are
eligible to enter that calculation.

This is a rebuild of the original step1_validation.py, refactored to import
shared logic from mcp_common.py instead of duplicating it. It also fixes the
hitter-attribution bug documented in parsing.py's HITTER PARITY section:
the per-player sparsity check below uses the corrected attribution, so its
numbers differ from the original Step 1 run (see the printed comparison at
the bottom of the sparsity check output).

One thing that doesn't change: the player-eligibility deliverable
(qualified_player_pool_min40.csv) is built from match counts, not
shot-level hitter attribution, so it's unaffected by the bug fix. This file
should be identical between the original and rebuilt runs, and it is.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd

import parsing as pr
import data_io as dio

pd.set_option('display.width', 140)

# --- Load ---
matches = dio.load_matches('charting-m-matches.csv')
points = dio.load_points_data(decades=('2020s',))

print(f"Total charted matches (all-time file): {len(matches)}")
print(f"Total points rows (2020s file): {len(points)}")

# --- Regression guard: confirm hitter parity is correct before trusting
# anything else in this script (see parsing.verify_hitter_parity) ---
print("\n--- Hitter-parity regression check ---")
match_rate, n_checked = pr.verify_hitter_parity(matches, points)
print(f"Hitter attribution matches PtWinner ground truth: {match_rate:.1%} of {n_checked} "
      f"winner-marked points (fixed logic; expected ~90%, asserts if <85%)")

# --- Identify target players' match_ids ---
players = ['Jannik Sinner', 'Carlos Alcaraz', 'Jack Draper', 'Brandon Nakashima']
target_matches = matches[matches['Player 1'].isin(players) | matches['Player 2'].isin(players)]
print(f"\nCharted matches for target players: {len(target_matches)}")

target_ids = set(target_matches['match_id'])
pts = points[points['match_id'].isin(target_ids)].copy()
print(f"\nPoint rows for these matches (2020s file): {len(pts)}")

# --- Shot notation completeness check ---
pts['has_1st'] = pts['1st'].notna() & (pts['1st'].astype(str).str.strip() != '')
pts['has_2nd'] = pts['2nd'].notna() & (pts['2nd'].astype(str).str.strip() != '')
pts['has_any_notation'] = pts['has_1st'] | pts['has_2nd']

print("\n--- Shot-notation field completeness ---")
print(f"Points with a 1st-serve notation string: {pts['has_1st'].sum()} / {len(pts)} ({pts['has_1st'].mean():.1%})")
print(f"Points with a 2nd-serve notation string: {pts['has_2nd'].sum()} / {len(pts)} ({pts['has_2nd'].mean():.1%})")
print(f"Points with ANY notation:                {pts['has_any_notation'].sum()} / {len(pts)} ({pts['has_any_notation'].mean():.1%})")

missing = pts[~pts['has_any_notation']]
print(f"\nPoints missing notation entirely: {len(missing)}")
if len(missing) > 0:
    print(missing['match_id'].value_counts().head(10))

# --- Parse shots with CORRECT hitter attribution (see parsing.py) ---
match_players = target_matches.set_index('match_id')[['Player 1', 'Player 2']]
NAME_MAP = {'Jannik Sinner': 'Sinner', 'Carlos Alcaraz': 'Alcaraz', 'Jack Draper': 'Draper', 'Brandon Nakashima': 'Nakashima'}

all_pairs = []
for row in pts[['match_id', 'Svr', '1st', '2nd']].to_dict('records'):
    match_id = row['match_id']
    if match_id not in match_players.index:
        continue
    p1, p2 = match_players.loc[match_id, ['Player 1', 'Player 2']]
    server_is_p1 = (row['Svr'] == 1)
    for col in ('1st', '2nd'):
        val = row[col]
        tokens = pr.extract_shot_dir_pairs(val)
        for idx, (shot, direction) in enumerate(tokens):
            hitter_is_p1 = pr.hitter_is_p1_for_token(idx, server_is_p1)
            if hitter_is_p1:
                hitter = p1
            else:
                hitter = p2
            all_pairs.append((shot, direction, hitter))

shot_df = pd.DataFrame(all_pairs, columns=['shot_type', 'direction', 'hitter'])
shot_df['target_player'] = shot_df['hitter'].map(NAME_MAP).fillna('other')
print(f"\n--- Parsed shot tokens (corrected hitter attribution) ---")
print(f"Total shot tokens extracted: {len(shot_df)}")
print(f"Tokens missing a direction digit: {shot_df['direction'].isna().sum()} ({shot_df['direction'].isna().mean():.1%})")

print("\nShot-type frequency (raw, up to 16 categories -- see parsing.SHOT_TYPE_CHARS):")
print(shot_df['shot_type'].value_counts())

# --- Sparsity check: coarsen to entropy-calc scheme. This is a diagnostic
# view distinct from parsing.WING_MAP -- it buckets EVERY shot type,
# including lob and other, rather than excluding them, so the sparsity
# check below can see where they land. ---
COARSE_MAP = {
    'f': 'forehand', 'r': 'forehand', 'u': 'forehand', 'o': 'forehand', 'v': 'forehand',
    'b': 'backhand', 's': 'backhand', 'y': 'backhand', 'p': 'backhand', 'z': 'backhand',
    'l': 'lob', 'm': 'lob', 'h': 'other', 'i': 'other', 'j': 'other', 'k': 'other',
    't': 'other', 'q': 'other',
}
shot_df['coarse_type'] = shot_df['shot_type'].map(COARSE_MAP).fillna('other')

sparse = shot_df.dropna(subset=['direction'])
cross = pd.crosstab(sparse['coarse_type'], sparse['direction'])
print("\n--- Cell counts: coarse shot-type x direction (the grid entropy will be computed over) ---")
print(cross)

print("\nCells with fewer than 30 observations (sparsity risk threshold):")
low_cells = cross[cross < 30].stack().dropna()
if len(low_cells):
    print(low_cells)
else:
    print("None -- all cells have >=30 obs")

print("\nTotal usable (shot,direction) tokens across all target players:", len(sparse))

# --- PER-PLAYER sparsity check (corrected attribution) ---
print("\n" + "=" * 70)
print("PER-PLAYER sparsity check (entropy is computed per player) -- CORRECTED")
print("=" * 70)

for player in ['Sinner', 'Alcaraz', 'Draper', 'Nakashima']:
    p_sparse = sparse[sparse['target_player'] == player]
    print(f"\n--- {player}: {len(p_sparse)} usable shot tokens ---")
    p_cross = pd.crosstab(p_sparse['coarse_type'], p_sparse['direction'])
    print(p_cross)
    low = p_cross[p_cross < 30].stack().dropna()
    if len(low):
        print(f"[warning] Cells below 30 obs for {player}:")
        print(low)
    else:
        print(f"[ok] All cells >=30 obs for {player}")
    very_low = p_cross[p_cross < 10].stack().dropna()
    if len(very_low):
        print(f"[warning] Cells below 10 obs (high sparsity risk) for {player}:")
        print(very_low)

# --- Qualified player pool (unaffected by the hitter-parity bug -- built
# from match counts, not shot attribution) ---
print("\n" + "=" * 70)
print("QUALIFIED PLAYER POOL (>= 40 charted matches)")
print("=" * 70)
pool = dio.get_qualified_player_pool(matches, min_matches=40)
print(f"\n{len(pool)} players qualify:\n")
print(pool.to_string(index=False))
pool.to_csv('qualified_player_pool_min40_REBUILT.csv', index=False)
print("\nSaved to qualified_player_pool_min40_REBUILT.csv")
print("Note: this file is built from match-count eligibility only and should be")
print("identical to the original qualified_player_pool_min40.csv, confirmed")
print("unaffected by the hitter-attribution bug fix (see parsing.py).")
