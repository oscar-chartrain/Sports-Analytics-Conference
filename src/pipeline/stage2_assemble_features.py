"""
Stage 2 of the full-pool driver: load the four cached extraction tables from
Stage 1 (entropy_extraction_stage1.py, renamed from stage1_extract.py) and
assemble one feature row per player in the qualified pool, with formal
data-sufficiency floors applied throughout.

This is the actual Step 2 deliverable Step 3 needs: a clean CSV, one row per
player, with every variable's sufficiency explicitly flagged rather than
silently computed on whatever data happens to exist.

Note: superseded for reproduction by run_pipeline.py, see the note atop
entropy_extraction_stage1.py. Kept for its original validation narrative.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import data_io as dio
import features as feat
import step2_entropy_pipeline as s2
import pandas as pd
import numpy as np
import time

t0 = time.time()
print("Loading qualified pool and cached extraction tables...")
pool = dio.load_qualified_pool()
players = pool['player'].tolist()

core_shots = pd.read_pickle('cache_core_shots.pkl')
extended_shots = pd.read_pickle('cache_extended_shots.pkl')
transitions = pd.read_pickle('cache_transitions.pkl')
pressure = pd.read_pickle('cache_pressure.pkl')
print(f"Loaded in {time.time()-t0:.1f}s: "
      f"{len(core_shots)} core shots, {len(extended_shots)} extended shots, "
      f"{len(transitions)} transitions, {len(pressure)} pressure rows")

rows = []
t0 = time.time()
for i, player in enumerate(players):
    row = {'player': player}
    row['charted_matches'] = pool.loc[pool['player'] == player, 'charted_matches'].iloc[0]

    # --- Core pooled entropy (6-cell forehand/backhand x direction) ---
    core_result = s2.compute_player_entropy(core_shots, player, min_obs_per_cell=feat.MIN_OBS)
    row['total_core_shots'] = core_result['total_shots']
    row['pooled_normalized_entropy'] = core_result['normalized_entropy']
    row['pooled_entropy_sufficient'] = core_result['data_sufficient']

    # --- Transition (conditional) entropy -- the PRIMARY style variable ---
    trans_result = s2.compute_transition_entropy(transitions, player, min_obs_per_context=feat.MIN_OBS)
    if trans_result is not None:
        row['total_transitions'] = trans_result['total_transitions']
        row['conditional_normalized_entropy'] = trans_result['conditional_normalized']
        row['marginal_normalized_entropy_transitions'] = trans_result['marginal_normalized']
        row['info_gain_relative'] = trans_result['info_gain_relative']
        row['transition_low_context_count'] = len(trans_result['low_contexts'])
        row['transition_entropy_sufficient'] = len(trans_result['low_contexts']) == 0
    else:
        row['total_transitions'] = 0
        row['conditional_normalized_entropy'] = np.nan
        row['marginal_normalized_entropy_transitions'] = np.nan
        row['info_gain_relative'] = np.nan
        row['transition_low_context_count'] = np.nan
        row['transition_entropy_sufficient'] = False

    # --- Dropshot (Extension 1) ---
    dropshot_result = feat.compute_dropshot_features(extended_shots, player, min_obs=feat.MIN_OBS)
    row.update(dropshot_result)

    # --- Pressure-ladder reductions (Extensions 2-4) ---
    pressure_result = feat.reduce_pressure_features(pressure, player, min_obs=feat.MIN_OBS)
    row.update(pressure_result)

    rows.append(row)
    if (i + 1) % 20 == 0:
        print(f"  processed {i+1}/{len(players)} players...")

print(f"Feature computation took {time.time()-t0:.1f}s")

feature_df = pd.DataFrame(rows)
feature_df.to_csv('step2_full_pool_features.csv', index=False)
print(f"\nSaved step2_full_pool_features.csv: {len(feature_df)} players x {len(feature_df.columns)} columns")

# --- Summary: how many players actually clear each floor ---
print("\n" + "=" * 70)
print("DATA-SUFFICIENCY SUMMARY (MIN_OBS = %d)" % feat.MIN_OBS)
print("=" * 70)
sufficiency_cols = [
    'pooled_entropy_sufficient', 'transition_entropy_sufficient',
    'dropshot_rate_sufficient', 'dropshot_entropy_sufficient',
    'serve_zone_sufficient', 'net_play_sufficient', 'return_depth_sufficient',
]
for col in sufficiency_cols:
    n_sufficient = feature_df[col].sum()
    print(f"  {col:35s}: {n_sufficient:3d} / {len(feature_df)} players ({n_sufficient/len(feature_df):.1%})")

print("\n" + "=" * 70)
print("PRIMARY VARIABLE DISTRIBUTION: conditional_normalized_entropy")
print("=" * 70)
valid = feature_df[feature_df['transition_entropy_sufficient']]['conditional_normalized_entropy']
print(valid.describe())

print("\n" + "=" * 70)
print("Sinner / Alcaraz spot-check against full-pool numbers")
print("=" * 70)
print(feature_df[feature_df['player'].isin(['Jannik Sinner', 'Carlos Alcaraz'])][
    ['player', 'charted_matches', 'conditional_normalized_entropy', 'info_gain_relative',
     'dropshot_rate', 'net_play_escalation_delta', 'wide_serve_escalation_delta']
].to_string(index=False))
