"""
consistency_fixes.py -- the two consistency checks pre-registered in
docs/combined/consistency_fixes_preregistration.md (written 2026-11-11, before
this script existed):

  1. Break-point conversion/save reliability over the same 1,000 random
     balanced splits used for the clutch measures (Table 1 of the paper), so
     Table 5 no longer rests on the single original split.
  2. Reliability-corrected TOST equivalence bounds recomputed at the
     random-split median (and 2.5th/97.5th percentile) clutch reliability,
     replacing a back-of-envelope figure for WTA return.

Reuses, unchanged: applications_analyses (cached point table, split helpers),
applications_extensions.load_categories (break-point classification) and
disattenuated_equivalence_bounds (TOST bound search and data loaders).
Fix 1's validation step aborts the script if the original alternating
assignment does not reproduce the reported Table 5 values within 0.001; Fix 2
aborts if the recomputed ATP observed bounds miss the documented figures.

Usage: python3 consistency_fixes.py [--splits N]
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse

import numpy as np
import pandas as pd

import applications_analyses as aa
import applications_extensions as ext
import disattenuated_equivalence_bounds as deb
import formulas as f

SEED = ext.SEED
N_SPLITS = ext.N_SPLITS
OUT_DIR = aa.OUT_DIR
MIN_BP = aa.MIN_OBS

# Reported Table 5 (original split), checked by validation.
TABLE5 = {
    ('atp', 'serve', 'raw'): 0.7543, ('atp', 'serve', 'diff'): 0.3998,
    ('atp', 'return', 'raw'): 0.6174, ('atp', 'return', 'diff'): 0.0535,
    ('wta', 'serve', 'raw'): 0.4391, ('wta', 'serve', 'diff'): 0.1181,
    ('wta', 'return', 'raw'): 0.0634, ('wta', 'return', 'diff'): -0.2895,
}
LABEL = {'serve': 'BP save (serve)', 'return': 'BP conversion (return)'}


# =============================================================================
# FIX 1: BREAK-POINT RELIABILITY OVER RANDOM SPLITS
# =============================================================================

def build_matrices(pts, players, sorted_ids):
    """For each role and category ('bp', 'base'): player-by-match matrices of
    point counts (n) and points won (w), so any half's totals are a matrix
    product with a 0/1 match-indicator vector."""
    pidx = {p: i for i, p in enumerate(players)}
    midx = {m: i for i, m in enumerate(sorted_ids)}
    P, M = len(players), len(sorted_ids)
    mats = {}
    for role in ('serve', 'return'):
        if role == 'serve':
            who, won = pts['server'], pts['server_won_point']
        else:
            who, won = pts['returner'], 1 - pts['server_won_point']
        d = pd.DataFrame({'player': who, 'match_id': pts['match_id'], 'cat': pts['cat'], 'won': won})
        d = d[d['player'].isin(pidx) & d['cat'].isin(['bp', 'base'])]
        g = d.groupby(['player', 'match_id', 'cat'])['won'].agg(['size', 'sum']).reset_index()
        for cat in ('bp', 'base'):
            sub = g[g['cat'] == cat]
            n = np.zeros((P, M))
            w = np.zeros((P, M))
            rows = sub['player'].map(pidx).to_numpy()
            cols = sub['match_id'].map(midx).to_numpy()
            n[rows, cols] = sub['size'].to_numpy()
            w[rows, cols] = sub['sum'].to_numpy()
            mats[(role, cat)] = (n, w)
    return mats


def stats_for_assignment(mats, assign):
    """Per role: (raw, diff, sufficient) arrays across players for one split."""
    in_a = (assign == 0).astype(float)
    in_b = 1.0 - in_a
    out = {}
    for role in ('serve', 'return'):
        vals = {}
        ok = np.ones(mats[(role, 'bp')][0].shape[0], dtype=bool)
        for h, ind in (('a', in_a), ('b', in_b)):
            n_bp = mats[(role, 'bp')][0] @ ind
            w_bp = mats[(role, 'bp')][1] @ ind
            n_ba = mats[(role, 'base')][0] @ ind
            w_ba = mats[(role, 'base')][1] @ ind
            ok &= (n_bp >= MIN_BP)
            with np.errstate(divide='ignore', invalid='ignore'):
                raw = w_bp / n_bp
                base = w_ba / n_ba
            vals[h] = (raw, raw - base)
        out[role] = (vals, ok)
    return out


def reliabilities(mats, assign):
    res = {}
    out = stats_for_assignment(mats, assign)
    for role, (vals, ok) in out.items():
        for k, name in ((0, 'raw'), (1, 'diff')):
            a, b = vals['a'][k][ok], vals['b'][k][ok]
            r = np.corrcoef(a, b)[0, 1]
            res[(role, name)] = (f.spearman_brown(r), int((~ok).sum()))
    return res


def fix1(tour, players, pts, half_map, n_splits):
    print(f"\n{'=' * 70}\nFIX 1 -- {tour.upper()}: break-point reliability over {n_splits} random splits\n{'=' * 70}")
    sorted_ids = sorted(half_map.keys())
    n_matches = len(sorted_ids)
    mats = build_matrices(pts, players, sorted_ids)

    orig_assign = np.array([0 if half_map[m] == 'A' else 1 for m in sorted_ids])
    orig = reliabilities(mats, orig_assign)
    worst = 0.0
    for (role, name), (val, n_excl) in orig.items():
        ref = TABLE5[(tour, role, name)]
        worst = max(worst, abs(val - ref))
        print(f"VALIDATION {LABEL[role]:24s} {name:4s} new code {val:+.4f}  reported {ref:+.4f}  "
              f"(players excluded {n_excl})")
    if worst > 0.001:
        raise SystemExit(f"{tour.upper()}: Fix 1 validation failed (max diff {worst:.4f}); stop and investigate.")
    print("VALIDATION PASS: original assignment reproduces Table 5 within 0.001")

    rng = np.random.default_rng(SEED)
    draws = {k: [] for k in orig}
    excl = {k: [] for k in orig}
    for s in range(n_splits):
        order = rng.permutation(n_matches)
        assign = np.zeros(n_matches, dtype=int)
        assign[order[1::2]] = 1
        res = reliabilities(mats, assign)
        for k, (val, n_excl) in res.items():
            draws[k].append(val)
            excl[k].append(n_excl)

    rows = []
    for (role, name), vals in draws.items():
        d = np.array(vals)
        lo, hi = np.percentile(d, [2.5, 97.5])
        row = {'tour': tour, 'measure': f"{LABEL[role]}, {'raw rate' if name == 'raw' else 'differential'}",
               'original_split': orig[(role, name)][0], 'median': float(np.median(d)),
               'p2_5': lo, 'p97_5': hi, 'share_below_070': float((d < 0.70).mean()),
               'original_in_range': bool(lo <= orig[(role, name)][0] <= hi),
               'mean_players_excluded': float(np.mean(excl[(role, name)])), 'n_splits': n_splits}
        rows.append(row)
        print(f"{row['measure']:50s} original {row['original_split']:+.3f}  median {row['median']:+.3f}  "
              f"95% range [{lo:+.3f}, {hi:+.3f}]  share<0.70: {row['share_below_070']:.1%}  "
              f"original typical: {'yes' if row['original_in_range'] else 'NO'}")
    return pd.DataFrame(rows)


# =============================================================================
# FIX 2: CORRECTED EQUIVALENCE BOUNDS AT RANDOM-SPLIT RELIABILITIES
# =============================================================================

def fix2():
    print(f"\n{'=' * 70}\nFIX 2 -- reliability-corrected TOST bounds at random-split reliabilities\n{'=' * 70}")
    rs = pd.read_csv(os.path.join(OUT_DIR, 'ext_a_random_splits.csv'))
    labels = {'serve': 'Serve quartile clutch', 'return': 'Return quartile clutch'}
    rows = []
    for tour in ('atp', 'wta'):
        df = deb.load_merged(tour)
        for role in ('serve', 'return'):
            x, y = deb.get_role_data(df, role)
            b_obs, r = deb.tightest_tost_bound(x, y)
            if tour == 'atp':
                doc = deb.DOCUMENTED_ATP_BOUNDS[role]
                if abs(b_obs - doc) > 0.001:
                    raise SystemExit(f"Fix 2 cross-check failed: ATP {role} bound {b_obs:.4f} vs documented {doc}")
            rel_ent = deb.ENTROPY_RELIABILITY[tour]
            row_rs = rs[(rs['tour'] == tour) & (rs['measure'] == labels[role])].iloc[0]
            versions = {'original split': row_rs['original_split'], 'random-split median': row_rs['median'],
                        'random-split 97.5th pct (best case)': row_rs['p97_5'],
                        'random-split 2.5th pct (worst case)': row_rs['p2_5']}
            for ver, rel in versions.items():
                if rel <= 0:
                    b_true, note = np.nan, 'vacuous (reliability <= 0)'
                else:
                    b_true = b_obs / np.sqrt(rel_ent * rel)
                    note = 'vacuous (bound > 1)' if b_true > 1 else ''
                rows.append({'tour': tour, 'role': role, 'version': ver, 'rel_clutch': rel,
                             'rel_entropy': rel_ent, 'B_obs': b_obs, 'B_true': b_true, 'note': note})
                shown = 'n/a' if np.isnan(b_true) else f'{b_true:.3f}'
                print(f"{tour.upper()} {role:7s} {ver:38s} rel={rel:+.3f}  B_obs={b_obs:.4f} -> B_true={shown}  {note}")
    return pd.DataFrame(rows)


# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=N_SPLITS)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    res1 = []
    for tour in ('atp', 'wta'):
        players, matches, half_map, summary, pts = aa.load_tour(tour, use_cache=True)
        pts = pts.copy()
        pts['cat'] = ext.load_categories(tour, pts)
        res1.append(fix1(tour, players, pts, half_map, args.splits))
    res2 = fix2()

    pd.concat(res1).to_csv(os.path.join(OUT_DIR, 'fix1_breakpoint_random_splits.csv'), index=False)
    res2.to_csv(os.path.join(OUT_DIR, 'fix2_corrected_bounds.csv'), index=False)
    print(f"\nWrote outputs to {OUT_DIR}")


if __name__ == '__main__':
    main()
