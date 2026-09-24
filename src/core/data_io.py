"""
data_io.py -- loading MCP data files and recording provenance for outputs.

One of core/'s four modules (parsing, formulas, data_io, features),
consolidated from the old mcp_common.py's data-loading section and
data_snapshot.py.
"""

import json
import os
import time

import pandas as pd

pd.set_option('display.width', 140)


# =============================================================================
# DATA LOADING
# =============================================================================

def load_matches(path='charting-m-matches.csv'):
    return pd.read_csv(path, low_memory=False)


def load_points_data(decades=('2020s',), gender='m'):
    """Loads and combines MCP points files for the requested decades. The
    default, ('2020s',), only covers players whose whole career is in the
    2020s -- full-career pulls need decades=('2020s', '2010s', 'to-2009').
    gender is 'm' (ATP, default) or 'w' (WTA)."""
    frames = []
    for decade in decades:
        fname = f'charting-{gender}-points-{decade}.csv'  # e.g. charting-m-points-2020s.csv
        frames.append(pd.read_csv(fname, low_memory=False))
    return pd.concat(frames, ignore_index=True)


def compute_empirical_p(points_df):
    """Tour-wide empirical point-win-on-serve rate: fraction of points won
    by the server. A data-derived alternative to the fixed p60/p65/p70/
    tiered constants in formulas.py (see
    docs/atp/03_leverage_clutch/empirical_p_variant.md). Pass points already
    restricted to the qualified pool's matches, not the raw MCP file."""
    return (points_df['PtWinner'] == points_df['Svr']).mean()


def load_qualified_pool(path='qualified_player_pool_min40.csv'):
    """Load the Step 1 definitive player pool (>=40 charted matches)."""
    return pd.read_csv(path)


def get_qualified_player_pool(matches_df, min_matches=40):
    """Players with >= min_matches charted matches (as Player 1 or Player
    2), sorted by coverage descending. Counts match appearances only, so
    it's unaffected by the hitter-attribution bug in parsing.py."""
    p1 = matches_df['Player 1']
    p2 = matches_df['Player 2']
    counts = pd.concat([p1, p2]).value_counts()
    qualified = counts[counts >= min_matches].reset_index()
    qualified.columns = ['player', 'charted_matches']
    return qualified


# =============================================================================
# PROVENANCE LOGGING
# =============================================================================
# MCP updates periodically (~every 100 new charted matches), so exact row
# counts and derived numbers can drift slightly run to run -- expected, not
# a bug, but worth recording WHICH pull produced a given output file so
# "why don't my numbers match exactly" is a lookup, not a mystery.

def snapshot_data_sources(output_path, sources: dict, extra: dict = None):
    """
    Write a sidecar JSON recording provenance for an output file.

    output_path: path to the CSV/output this snapshot documents (e.g.
        'wta_full_pool_features.csv'). The snapshot is written alongside it
        as '<output_path>.snapshot.json'.
    sources: dict of {file_path: dataframe_or_none}. If a DataFrame is
        given, its row count is recorded. Pass None for the matches file
        itself if you just want its path recorded, since it doesn't have a
        row-count-per-se comparison purpose.
    extra: any additional metadata worth recording (player pool size,
        MIN_OBS threshold used, git commit hash if this is in a repo, etc).
    """
    record = {
        'output_file': output_path,
        'snapshot_taken_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'sources': {},
    }
    for path, df in sources.items():
        entry = {'exists': os.path.exists(path)}
        if entry['exists']:
            entry['size_bytes'] = os.path.getsize(path)
            entry['modified_utc'] = time.strftime(
                '%Y-%m-%dT%H:%M:%SZ', time.gmtime(os.path.getmtime(path)))
        if df is not None:
            entry['row_count'] = len(df)
        record['sources'][path] = entry
    if extra:
        record['extra'] = extra

    snapshot_path = f'{output_path}.snapshot.json'
    with open(snapshot_path, 'w') as out_file:
        json.dump(record, out_file, indent=2)
    return snapshot_path
