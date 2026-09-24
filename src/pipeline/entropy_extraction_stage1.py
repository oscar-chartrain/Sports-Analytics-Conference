"""
Stage 1 of the full-pool driver: run the four expensive per-point extraction
passes once, for the full qualified player pool across all three decades of
data, and cache each result to disk (pickle) so Stage 2 (feature assembly)
doesn't have to re-run them.

Each extraction pass is O(total points) with per-character notation parsing,
so this is the expensive part of the pipeline (a single pass over the full
~1.28M-row combined points file took ~260s in testing). Running all four
takes roughly 15-20 minutes; staged and cached so a failure partway through
doesn't waste the earlier work.

Note: superseded for reproduction by run_pipeline.py, which recomputes the
same full-pool entropy features in one in-memory pass with no disk caching.
Kept because this is the original two-stage version the Step 2 README's
numbers and sanity checks actually ran against, and because the disk-cached
staging here is still useful for iterating on Stage 2 without re-running
the expensive Stage 1 extraction each time. Renamed from stage1_extract.py,
which collided visually with step1_validation.py despite being an
unrelated, later-stage script (see root README's reorg notes).
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import data_io as dio
import parsing as pr
import step2_entropy_pipeline as s2
import pandas as pd
import time

if len(sys.argv) > 1:
    STAGE = sys.argv[1]
else:
    STAGE = 'all'

print("Loading match metadata, full player pool, and all-decade points data...")
matches = dio.load_matches('charting-m-matches.csv')
pool = dio.load_qualified_pool()
players = pool['player'].tolist()
print(f"Qualified pool: {len(players)} players")

points = dio.load_points_data(decades=('2020s', '2010s', 'to-2009'))
print(f"Total points rows (all decades): {len(points)}")

print("\n--- Hitter-parity regression guard ---")
match_rate, n_checked = pr.verify_hitter_parity(matches, points)
print(f"Hitter attribution matches PtWinner ground truth: {match_rate:.1%} of {n_checked} points")

if STAGE in ('all', 'core'):
    print("\n[1/4] Extracting core (wing, direction) shots for full pool...")
    t0 = time.time()
    shot_df = s2.get_player_shots(matches, points, players)
    print(f"  done in {time.time()-t0:.0f}s, {len(shot_df)} rows")
    shot_df.to_pickle('cache_core_shots.pkl')

if STAGE in ('all', 'extended'):
    print("\n[2/4] Extracting extended (dropshot-aware) shots for full pool...")
    t0 = time.time()
    ext_shot_df = s2.get_player_shots_extended(matches, points, players)
    print(f"  done in {time.time()-t0:.0f}s, {len(ext_shot_df)} rows")
    ext_shot_df.to_pickle('cache_extended_shots.pkl')

if STAGE in ('all', 'transitions'):
    print("\n[3/4] Extracting shot transitions (context->current) for full pool...")
    t0 = time.time()
    trans_df = s2.get_player_shot_transitions(matches, points, players)
    print(f"  done in {time.time()-t0:.0f}s, {len(trans_df)} rows")
    trans_df.to_pickle('cache_transitions.pkl')

if STAGE in ('all', 'pressure'):
    print("\n[4/4] Extracting pressure-situation features for full pool...")
    t0 = time.time()
    pressure_df = s2.get_pressure_features(matches, points, players)
    print(f"  done in {time.time()-t0:.0f}s, {len(pressure_df)} rows")
    pressure_df.to_pickle('cache_pressure.pkl')

print("\nStage 1 extraction complete for requested stage(s):", STAGE)
