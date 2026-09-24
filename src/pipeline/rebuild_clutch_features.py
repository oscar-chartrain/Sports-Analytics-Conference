"""
rebuild_clutch_features.py -- regenerate clutch features (new p-variants
etc.) without re-running the expensive entropy extraction. Never overwrites
a committed primary results file.
============================================================================
build_clutch_features() (leverage/clutch) is much cheaper than
build_entropy_features() (per-character shot-notation parsing over ~1.28M
points), see run_pipeline.py's [2/4] vs [3/4] steps. When only the
clutch/leverage side changes (e.g. adding a new p-variant to
core/features.py), there's no need to redo entropy extraction: this
script re-fetches matches/points, rebuilds only the clutch features against
the pool already on disk, and re-merges with the existing, unchanged
{tour}_full_pool_features.csv (or step2_full_pool_features.csv for ATP,
which predates the {tour}_ naming convention, see root README's naming-era
note).

Provenance finding, from running this script for the tour-specific
empirical-p variant: rebuilding WTA's clutch features this way reproduces
the committed wta_clutch_features.csv exactly (max diff = 0 across all
shared columns), which is expected, since that file has always been
build_clutch_features()'s own output. Rebuilding ATP's does not exactly
reproduce the committed step3_clutch_features.csv: clutch scores differ by
up to ~0.005 and per-player quartile-bucket point counts differ by up to
136 (concentrated in high-volume players like Federer), even though the
aggregate relevant-match/relevant-point counts match exactly (6,652
matches, 1,132,053 points, both matching step3_README.md's documented
figures). This is a newly-quantified instance of a gap already disclosed in
core/features.py's own docstring: the original ATP script that
produced step3_clutch_features.csv is "not recoverable," and this
reconstruction was previously checked only against a handful of spot
numbers (Sinner/Alcaraz clutch values, the BLR convergent-validity
correlation), never a full-table diff. Running this script is the first
time that gap has been measured directly.

Because of that, this script never overwrites a tour's existing primary
clutch/merged CSV. It always writes to a "_reconstructed" suffixed path
instead, and prints a diff summary against the primary file if one exists,
so the provenance gap (or its absence, as for WTA) is visible every time
this runs, not just once.

Requires the raw MCP files already present in results/{tour}/ (this repo
never commits them; fetch per the root README's Reproduce section first).

Usage: python3 rebuild_clutch_features.py --tour atp
       python3 rebuild_clutch_features.py --tour wta
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import pandas as pd

import data_io as dio
import features as feat

# Two levels up from src/pipeline/ to reach the actual repo
# root (src/ itself is one level up, the repo root is two).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def diff_against_primary(primary_path, rebuilt_df):
    if not os.path.exists(primary_path):
        print(f"No existing primary file at {primary_path} -- nothing to diff against.")
        return
    primary = pd.read_csv(primary_path).set_index('player').sort_index()
    rebuilt = rebuilt_df.set_index('player').sort_index()

    shared_cols = []
    for c in primary.columns:
        if c in rebuilt.columns:
            shared_cols.append(c)
    num_cols = primary[shared_cols].select_dtypes('number').columns
    max_diff = 0.0
    diffs = {}
    for c in num_cols:
        d = (primary[c] - rebuilt[c]).abs().max()
        if d > 1e-9:
            diffs[c] = d
            max_diff = max(max_diff, d)
    if not diffs:
        print(f"Rebuilt output matches {os.path.basename(primary_path)} EXACTLY "
              f"(max diff = 0 across {len(num_cols)} shared numeric columns).")
    else:
        print(f"Rebuilt output DIFFERS from {os.path.basename(primary_path)} "
              f"on {len(diffs)}/{len(num_cols)} shared numeric columns (max diff {max_diff:.4f}):")
        for c, d in sorted(diffs.items(), key=lambda kv: -kv[1]):
            print(f"    {c}: max diff {d:.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tour', choices=['atp', 'wta'], required=True)
    args = parser.parse_args()
    tour = args.tour
    if tour == 'atp':
        gender = 'm'
        features_filename = 'step2_full_pool_features.csv'
    else:
        gender = 'w'
        features_filename = 'wta_full_pool_features.csv'
    results_dir = os.path.join(REPO_ROOT, 'results', tour)

    features_path = os.path.join(results_dir, features_filename)
    features = pd.read_csv(features_path)
    players = features['player'].tolist()
    print(f"Loaded {len(players)} pool players from {features_path}")

    old_cwd = os.getcwd()
    os.chdir(results_dir)
    try:
        matches = dio.load_matches(f'charting-{gender}-matches.csv')
        points = dio.load_points_data(decades=('2020s', '2010s', 'to-2009'), gender=gender)
    finally:
        os.chdir(old_cwd)

    relevant_matches = matches[matches['Player 1'].isin(players) | matches['Player 2'].isin(players)]
    target_ids = set(relevant_matches['match_id'])
    relevant_points = points[points['match_id'].isin(target_ids)]
    print(f"{len(relevant_matches)} relevant matches, {len(relevant_points)} relevant points")

    clutch = feat.build_clutch_features(relevant_matches, relevant_points, players)

    if tour == 'atp':
        primary_filename = 'step3_clutch_features.csv'
        reconstructed_filename = 'step3_clutch_features_reconstructed.csv'
    else:
        primary_filename = 'wta_clutch_features.csv'
        reconstructed_filename = 'wta_clutch_features_reconstructed.csv'

    primary_clutch_path = os.path.join(results_dir, primary_filename)
    diff_against_primary(primary_clutch_path, clutch)

    clutch_path = os.path.join(results_dir, reconstructed_filename)
    clutch.to_csv(clutch_path, index=False)
    print(f"Wrote {clutch_path} (never overwrites the primary file)")

    merged = features.merge(clutch, on='player', how='inner', validate='one_to_one')
    merged_path = os.path.join(results_dir, f'{tour}_merged_reconstructed.csv')
    merged.to_csv(merged_path, index=False)
    print(f"Wrote {merged_path}")

    return merged


if __name__ == '__main__':
    main()
