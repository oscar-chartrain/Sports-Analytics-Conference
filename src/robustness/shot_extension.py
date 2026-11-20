"""
shot_extension.py -- winners by shot type and point clutch by rally length, as defined in
docs/combined/shot_extension_preregistration.md (written 2026-11-20, before this script existed).

New outcomes (higher = better under pressure; thresholds from all the player's points, as R1 to R9):
  R10 winner clutch, forehand   R11 winner clutch, backhand   R12 winner clutch, slice
  R13 point clutch, short rallies (rally-decided points of 2 to 4 shots)
  R14 point clutch, long rallies  (rally-decided points of 5 or more shots)

Validation first (aborts before writing): hitter parity; the paper's serve and return original-split
reliabilities and the committed forehand-error outcome (R4) are reproduced within 0.001; family winners
never exceed all winners.

    python src/robustness/shot_extension.py [--splits N]
Writes results/applications/shot_extension_reliability.csv
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import argparse

import numpy as np
import pandas as pd

import applications_analyses as aa
import all_shots_analyses as asa

SEED = 20261123
N_SPLITS = 1000
MIN_PTS = asa.MIN_PTS
MIN_SHOTS = asa.MIN_SHOTS
NEW = ['R10_winner_forehand', 'R11_winner_backhand', 'R12_winner_slice', 'R13_short_rally', 'R14_long_rally']
LABELS = {'R10_winner_forehand': 'R10 Winner clutch, forehand', 'R11_winner_backhand': 'R11 Winner clutch, backhand',
          'R12_winner_slice': 'R12 Winner clutch, slice', 'R13_short_rally': 'R13 Point clutch, short rallies (2 to 4 shots)',
          'R14_long_rally': 'R14 Point clutch, long rallies (5 or more shots)'}
SHORT_MAX = 4


def player_arrays2(tab, players, gm):
    """asa.player_arrays plus total shots in the point and winners by family of the last shot."""
    base = asa.player_arrays(tab, players, gm)
    by_s = tab.groupby('server').indices
    by_r = tab.groupby('returner').indices
    for p in players:
        parts = []
        for role, idx in (('s', by_s.get(p, np.array([], dtype=int))), ('r', by_r.get(p, np.array([], dtype=int)))):
            d = tab.iloc[idx]
            is_s = role == 's'
            own = d['last_server'].values == (1 if is_s else 0)
            has_shot = d['phase'].values >= asa.PHASE['return']
            win_pt = (d['term'].values == '*') & own & has_shot
            lf = d['last_fam'].values
            rec = {'nsh': (d['ns'].values + d['nr'].values).astype(float)}
            for j, name in enumerate(asa.FAM_NAMES[:3]):
                rec[f'win_{name}'] = (win_pt & (lf == j)).astype(float)
            parts.append(rec)
        for k in parts[0]:
            base[p][k] = np.concatenate([parts[0][k], parts[1][k]])
    return base


def evaluate2(d, m):
    v = {k: x[m] for k, x in d.items()}
    keep = ~np.isnan(v['lev'])
    v = {k: x[keep] for k, x in v.items()}
    res = dict.fromkeys(NEW, np.nan)
    if len(v['lev']) < 4 * MIN_PTS:
        return res
    top, bot = asa._buckets(v['lev'])
    for name, fam in (('R10_winner_forehand', 'forehand'), ('R11_winner_backhand', 'backhand'), ('R12_winner_slice', 'slice')):
        res[name] = asa._rate_diff(v[f'win_{fam}'], v[f'sh_{fam}'], top, bot, +1.0, MIN_SHOTS)
    for name, sel in (('R13_short_rally', v['rally'] & (v['nsh'] <= SHORT_MAX)),
                      ('R14_long_rally', v['rally'] & (v['nsh'] > SHORT_MAX))):
        rt, rb = top & sel, bot & sel
        if rt.sum() >= MIN_PTS and rb.sum() >= MIN_PTS:
            res[name] = v['won'][rt].mean() - v['won'][rb].mean()
    return res


def half_values2(arrs, players, assign, fn, keys):
    va = np.full((len(players), len(keys)), np.nan)
    vb = np.full((len(players), len(keys)), np.nan)
    for j, p in enumerate(players):
        ra, rb = fn(arrs[p], assign[j]), fn(arrs[p], ~assign[j])
        va[j] = [ra[k] for k in keys]
        vb[j] = [rb[k] for k in keys]
    return va, vb


def median_events(arrs, players):
    out = {k: [] for k in NEW}
    for p in players:
        d = arrs[p]
        keep = ~np.isnan(d['lev'])
        v = {k: x[keep] for k, x in d.items()}
        top, bot = asa._buckets(v['lev'])
        tb = top | bot
        for name, fam in (('R10_winner_forehand', 'forehand'), ('R11_winner_backhand', 'backhand'), ('R12_winner_slice', 'slice')):
            out[name].append(v[f'sh_{fam}'][tb].sum())
        out['R13_short_rally'].append((tb & v['rally'] & (v['nsh'] <= SHORT_MAX)).sum())
        out['R14_long_rally'].append((tb & v['rally'] & (v['nsh'] > SHORT_MAX)).sum())
    return {k: float(np.median(x)) for k, x in out.items()}


def run_tour(tour, n_splits):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    arrs = player_arrays2(tab, players, gm)
    # validation 4: family winners never exceed all winners
    for p in players:
        d = arrs[p]
        if (d['win_forehand'] + d['win_backhand'] + d['win_slice'] > d['win'] + 1e-9).any():
            raise SystemExit(f"{tour.upper()}: family winners exceed all winners for {p}.")
    print("VALIDATION family winners <= all winners: PASS")
    orig_assign = np.array([half_map[m] == 'A' for m in sorted_ids])
    assign0 = [orig_assign[arrs[p]['gm']] for p in players]
    va, vb = asa.half_values(arrs, players, assign0)
    base = asa.split_rel(va, vb)
    ref = pd.read_csv(os.path.join(aa.OUT_DIR, 'allshots_reliability.csv'))
    ref = ref[ref.tour == tour].set_index('outcome')['original_split']
    for k in ('serve_clutch', 'return_clutch', 'R4_error_forehand'):
        new = base[asa.OUTCOMES.index(k)]
        old = aa.DOC_RELIABILITY[(tour, 'serve' if k == 'serve_clutch' else 'return')] if k != 'R4_error_forehand' else ref[k]
        print(f"VALIDATION {k}: new {new:+.4f} reference {old:+.4f}")
        if abs(new - old) > 0.001:
            raise SystemExit(f"{tour.upper()}: validation failed for {k}.")
    print("VALIDATION PASS")
    va2, vb2 = half_values2(arrs, players, assign0, evaluate2, NEW)
    orig = np.array([_rel(va2[:, k], vb2[:, k]) for k in range(len(NEW))])
    rng = np.random.default_rng(SEED)
    n_m = len(sorted_ids)
    draws = np.zeros((n_splits, len(NEW)))
    for s in range(n_splits):
        order = rng.permutation(n_m)
        assign = np.zeros(n_m, dtype=int)
        assign[order[1::2]] = 1
        in_a = assign == 0
        a, b = half_values2(arrs, players, [in_a[arrs[p]['gm']] for p in players], evaluate2, NEW)
        draws[s] = [_rel(a[:, k], b[:, k]) for k in range(len(NEW))]
        if (s + 1) % 100 == 0:
            print(f"  ...{s + 1}/{n_splits} splits")
    med_ev = median_events(arrs, players)
    rows = []
    for k, name in enumerate(NEW):
        d = draws[:, k]
        d = d[~np.isnan(d)]
        row = {'tour': tour, 'outcome': name, 'label': LABELS[name], 'original_split': orig[k],
               'median': np.median(d) if len(d) else np.nan, 'p2_5': np.percentile(d, 2.5) if len(d) else np.nan,
               'p97_5': np.percentile(d, 97.5) if len(d) else np.nan,
               'share_below_070': float((d < 0.70).mean()) if len(d) else np.nan,
               'share_at_or_above_070': float((d >= 0.70).mean()) if len(d) else np.nan,
               'n_valid_splits': len(d), 'median_events_top_bottom': med_ev[name]}
        rows.append(row)
        print(f"{LABELS[name]:48s} orig {orig[k]:+.3f}  median {row['median']:+.3f}  [{row['p2_5']:+.3f}, {row['p97_5']:+.3f}]"
              f"  share>=0.70 {row['share_at_or_above_070']:.1%}  events {med_ev[name]:,.0f}")
    return pd.DataFrame(rows)


def _rel(x, y):
    ok = ~np.isnan(x) & ~np.isnan(y)
    if ok.sum() < 10:
        return np.nan
    return asa.f.spearman_brown(np.corrcoef(x[ok], y[ok])[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=N_SPLITS)
    args = ap.parse_args()
    out = pd.concat([run_tour(t, args.splits) for t in ('atp', 'wta')])
    path = os.path.join(aa.OUT_DIR, 'shot_extension_reliability.csv')
    out.to_csv(path, index=False)
    print(f"\nWrote {path}")
    print('=== RUN END')


if __name__ == '__main__':
    main()
