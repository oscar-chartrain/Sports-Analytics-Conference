"""Positive control: how large must a stable clutch difference be before the pipeline calls it reliable?

Plan: docs/combined/positive_control_preregistration.md (written before this script was run).
Plants N(0, s) per-player shifts on top-leverage-quartile points in the real design (same players,
points, leverage, matches), redraws outcomes as Bernoulli around each player's own role win rate,
and runs the paper's split-half reliability routine over random balanced splits.

    python src/robustness/positive_control.py [--draws 40] [--splits 25] [--tours atp wta] [--validate-only]
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

import applications_analyses as aa
import all_shots_analyses as asa
import rally_extension as rx

SEED = 20261121
OUTS = ['S', 'Rt', 'R1']
KEEP = ('lev', 'won', 'is_serve', 'gm', 'rally')
GRID = [0.0, 0.01, 0.02, 0.03, 0.04, 0.06]
EST = {('atp', 'S'): 0.0215, ('atp', 'Rt'): 0.0122, ('atp', 'R1'): 0.0162,
       ('wta', 'S'): 0.0188, ('wta', 'Rt'): 0.0131, ('wta', 'R1'): 0.0106}
OBS = {('atp', 'S'): 0.53, ('atp', 'Rt'): 0.24, ('atp', 'R1'): 0.44,
       ('wta', 'S'): 0.41, ('wta', 'Rt'): 0.27, ('wta', 'R1'): 0.25}
KEY = {'S': 'serve_clutch', 'Rt': 'return_clutch', 'R1': 'R1_rally_point'}
OUT_DIR = aa.OUT_DIR


def log(*a):
    print(*a, flush=True)


def fail(msg):
    raise SystemExit(f"VALIDATION FAILED: {msg}")


def simulate(arrs, players, k, s, rng):
    """Copy of the arrays with outcomes for outcome k redrawn under planted spread s."""
    out = {}
    for p in players:
        a = arrs[p]
        won = a['won'].astype(float).copy()
        lev = a['lev']
        ok = ~np.isnan(lev)
        d = rng.normal(0, s) if s > 0 else 0.0
        if k in ('S', 'Rt'):
            sub = ok & (a['is_serve'] == (k == 'S'))
            top = np.zeros(len(lev), dtype=bool)
            top[sub] = lev[sub] >= np.quantile(lev[sub], 0.75)
            base = np.full(len(lev), won[sub].mean())
            sel = sub
        else:
            top = np.zeros(len(lev), dtype=bool)
            top[ok] = lev[ok] >= np.quantile(lev[ok], 0.75)
            top &= a['rally']
            sel = ok & a['rally']
            base = np.where(a['is_serve'], won[sel & a['is_serve']].mean(), won[sel & ~a['is_serve']].mean())
        p_win = np.clip(base + d * top, 0.02, 0.98)
        new = won.copy()
        new[sel] = (rng.random(sel.sum()) < p_win[sel]).astype(float)
        b = {key: a[key] for key in KEEP}
        b['won'] = new
        out[p] = b
    return out


def split_rel(arrs, players, k, n_m, rng, n_splits):
    gms = [arrs[p]['gm'] for p in players]
    vals = np.full(n_splits, np.nan)
    for i in range(n_splits):
        perm = rng.permutation(n_m)
        a = np.zeros(n_m, dtype=bool)
        a[perm[: n_m // 2]] = True
        da = np.full(len(players), np.nan)
        db = da.copy()
        for j, p in enumerate(players):
            sa = rx.sums(arrs[p], a[gms[j]], k)
            sb = rx.sums(arrs[p], ~a[gms[j]], k)
            if sa is not None:
                da[j] = rx.diff_se(sa)[0]
            if sb is not None:
                db[j] = rx.diff_se(sb)[0]
        vals[i] = rx.rel_from(da, db)
    return vals


def run_tour(tour, n_draws, n_splits, validate_only):
    t0 = time.time()
    log(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    n_m = len(sorted_ids)
    full = asa.player_arrays(tab, players, gm)
    arrs = {p: {k: full[p][k] for k in KEEP} for p in players}
    # V3: real-data original-split reliability reproduces the committed values
    orig = np.array([half_map[m] == 'A' for m in sorted_ids])
    ref = pd.read_csv(os.path.join(OUT_DIR, 'allshots_reliability.csv'))
    ref = ref[ref['tour'] == tour].set_index('outcome')['original_split']
    for k in OUTS:
        da = np.full(len(players), np.nan)
        db = da.copy()
        for j, p in enumerate(players):
            sa = rx.sums(arrs[p], orig[arrs[p]['gm']], k)
            sb = rx.sums(arrs[p], ~orig[arrs[p]['gm']], k)
            if sa is not None:
                da[j] = rx.diff_se(sa)[0]
            if sb is not None:
                db[j] = rx.diff_se(sb)[0]
        r = rx.rel_from(da, db)
        if abs(r - ref[KEY[k]]) > 0.001:
            fail(f"V3 {tour} {k}: {r:.4f} vs committed {ref[KEY[k]]:.4f}")
        log(f"V3 {tour} {k}: original-split reliability {r:+.4f} equals committed {ref[KEY[k]]:+.4f}")
    rng = np.random.default_rng(SEED + (0 if tour == 'atp' else 1000))
    rows = []
    nd, ns = (1, 8) if validate_only else (n_draws, n_splits)
    for k in OUTS:
        grid = [('grid', s) for s in GRID] + [('estimated', EST[(tour, k)])]
        for kind, s in grid:
            v = []
            for _ in range(nd):
                sim = simulate(arrs, players, k, s, rng)
                v.append(split_rel(sim, players, k, n_m, rng, ns))
            v = np.concatenate(v)
            v = v[~np.isnan(v)]
            r = dict(tour=tour, outcome=k, kind=kind, planted_sd_pp=100 * s, median=float(np.median(v)),
                     p2_5=float(np.percentile(v, 2.5)), p97_5=float(np.percentile(v, 97.5)),
                     share_ge_070=float((v >= 0.70).mean()), n=len(v),
                     meets_criterion=bool(np.median(v) >= 0.70 and (v >= 0.70).mean() >= 0.95))
            rows.append(r)
            log(f"PC {tour} {k:>2s} {kind:>9s} s={100 * s:4.2f} pp: median {r['median']:+.3f} "
                f"[{r['p2_5']:+.3f}, {r['p97_5']:+.3f}] share>=0.70 {r['share_ge_070']:.1%}")
            if kind == 'grid' and s == 0 and not validate_only and abs(r['median']) > 0.15:
                fail(f"V1 {tour} {k}: null median {r['median']:+.3f} is not within 0.15 of zero")
            if kind == 'estimated' and not validate_only:
                if abs(r['median'] - OBS[(tour, k)]) > 0.15:
                    log(f"V2 NOTE {tour} {k}: simulated {r['median']:+.3f} vs observed {OBS[(tour, k)]:.2f} differ by more than 0.15")
                else:
                    log(f"V2 {tour} {k}: simulated {r['median']:+.3f} within 0.15 of observed {OBS[(tour, k)]:.2f}")
    log(f"{tour.upper()} done in {time.time() - t0:.0f}s")
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draws', type=int, default=40)
    ap.add_argument('--splits', type=int, default=25)
    ap.add_argument('--tours', nargs='+', default=['atp', 'wta'])
    ap.add_argument('--validate-only', action='store_true')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    for tour in args.tours:
        df = run_tour(tour, args.draws, args.splits, args.validate_only)
        if not args.validate_only:
            df.to_csv(os.path.join(OUT_DIR, f'positive_control_{tour}{args.tag}.csv'), index=False)
    log("=== RUN END")


if __name__ == '__main__':
    main()
