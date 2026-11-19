"""
selection_checks.py -- the selection checks pre-registered in
docs/combined/selection_checks_preregistration.md (written 2026-11-18, before this script was run).

  C1  player-volume cutoff: pools with >= 20, 30, 40 (paper), 60, 80 charted matches
  C2  tournament-blocked splits (whole tournament editions go to one half)
  C3  Grand Slam against other matches: within-stratum reliability, mean shift, cross-stratum r
  C4  charted-match count and Slam share against the full-sample score (Spearman)

Outcomes S (serve clutch), Rt (return clutch), R1 (rally-point clutch), the paper's definitions;
the per-half routine is rally_extension.sums / diff_se, already validated against the paper's code.
Validation first (the script aborts if any check fails): see the pre-registration, V1 to V5.

Usage: python src/robustness/selection_checks.py [--splits N] [--validate-only] [--tours atp wta]
                                                  [--tasks c1_20 c1_30 c1_40 c1_60 c1_80 c2 c3 c4] [--tag T]
       python src/robustness/selection_checks.py --merge
Tasks are independent (seeds depend on the task, not the process), so they can run in parallel; each
writes a part file, and --merge assembles results/applications/selection_checks_*.csv (and adds the
matched-split comparison for C2). Logs: results/applications/run_log_selection_checks*.txt (via tee).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse
import time

import numpy as np
import pandas as pd
from scipy import stats

import applications_analyses as aa
import all_shots_analyses as asa
import rally_extension as rx
import formulas as f
import confound_adjusted_clutch as cac

SEED = 20261120
CUTOFFS = [40, 20, 30, 60, 80]            # 40 first: V3 runs right after it
OUTS = ['S', 'Rt', 'R1']
KEEP = ('lev', 'won', 'is_serve', 'gm', 'rally')
OUT_DIR = aa.OUT_DIR
ALPHA_C4 = 0.05 / 12


def log(*a):
    print(*a, flush=True)


def fail(msg):
    raise SystemExit(f"VALIDATION FAILED: {msg}")


# =============================================================================
# data: the extended point table
# =============================================================================

def lev_row(fmt, r):
    m = fmt.get(r['match_id'])
    if m is None or m.get('sets_to_win') is None:
        return np.nan
    return f.compute_leverage(r, m, p=0.65)


def extended_table(tour, matches, base_half_map, base_pts, rng):
    """Point table for every match involving a player with >= min(CUTOFFS) charted matches. Rows of
    the paper's table are reused; leverage is computed (paper's function, p = 0.65) for the rest.
    Returns (pool_lo, half_map_E, tab, sorted_ids, gm)."""
    _, points = aa.shr.load_raw(tour)
    cnt = pd.concat([matches['Player 1'], matches['Player 2']]).value_counts()
    pool_lo = sorted(cnt[cnt >= min(CUTOFFS)].index)
    half_map_E, relM = aa.shr.split_matches(matches, pool_lo)
    raw = points[points['match_id'].isin(set(half_map_E))].reset_index(drop=True)
    old = raw['match_id'].isin(set(base_half_map)).values
    if not (raw.loc[old, 'match_id'].values == base_pts['match_id'].values).all():
        fail("V1: raw rows of the paper's matches do not align with the cached table")
    fmt = f.build_match_format_lookup_ext(relM)
    cols = ['match_id', 'Svr', 'Pts', 'Gm1', 'Gm2', 'Set1', 'Set2', 'PtWinner']
    recs = raw[cols].to_dict('records')
    lev = np.full(len(raw), np.nan)
    lev[old] = base_pts['leverage_p65'].values
    new_idx = np.where(~old)[0]
    t0 = time.time()
    for i in new_idx:
        lev[i] = lev_row(fmt, recs[i])
    log(f"leverage computed for {len(new_idx):,} new points in {time.time() - t0:.0f}s")
    # V2: the new code path reproduces cached leverage on random paper rows
    old_idx = np.where(old)[0]
    chk = rng.choice(len(old_idx), 300, replace=False)
    worst = 0.0
    for j in chk:
        a, b = lev_row(fmt, recs[old_idx[j]]), base_pts['leverage_p65'].values[j]
        if np.isnan(a) != np.isnan(b):
            fail("V2: NaN pattern differs on a paper row")
        if not np.isnan(a):
            worst = max(worst, abs(a - b))
    log(f"V2 leverage recomputed on 300 paper rows: max abs diff {worst:.2e}")
    if worst > 1e-12:
        fail("V2: recomputed leverage differs from the cached one")
    mp = relM.drop_duplicates('match_id').set_index('match_id')[['Player 1', 'Player 2']]
    pts = pd.DataFrame({'match_id': raw['match_id'], 'Svr': raw['Svr'], 'PtWinner': raw['PtWinner'],
                        'leverage_p65': lev}).join(mp, on='match_id')
    pts['server'] = pts['Player 1'].where(pts['Svr'] == 1, pts['Player 2'])
    pts['returner'] = pts['Player 2'].where(pts['Svr'] == 1, pts['Player 1'])
    pts['server_won_point'] = (pts['PtWinner'] == pts['Svr']).astype(float)
    # V1 (rows): the paper's rows are unchanged inside the extended table
    sub = pts[old].reset_index(drop=True)
    same = ((sub['match_id'].values == base_pts['match_id'].values).all()
            and (sub['server'].values == base_pts['server'].values).all()
            and (sub['returner'].values == base_pts['returner'].values).all()
            and (sub['server_won_point'].values == base_pts['server_won_point'].values).all()
            and np.array_equal(sub['leverage_p65'].values, base_pts['leverage_p65'].values, equal_nan=True))
    if not same:
        fail("V1: the paper's rows changed inside the extended table")
    log(f"V1 extended table: {len(pts):,} points, {len(half_map_E):,} matches; paper rows identical")
    tab = asa.build_point_table(tour, matches, half_map_E, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map_E))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    return pool_lo, half_map_E, tab, sorted_ids, gm


# =============================================================================
# per-half machinery
# =============================================================================

def half_vals(arrs, players, k, masks_a, masks_b):
    da = np.full(len(players), np.nan)
    db = da.copy()
    for j, p in enumerate(players):
        a = rx.sums(arrs[p], masks_a[j], k)
        b = rx.sums(arrs[p], masks_b[j], k)
        if a is not None:
            da[j] = rx.diff_se(a)[0]
        if b is not None:
            db[j] = rx.diff_se(b)[0]
    return da, db


def full_scores(arrs, players, k, row_mask=None):
    out = np.full(len(players), np.nan)
    for j, p in enumerate(players):
        m = np.ones(len(arrs[p]['lev']), dtype=bool) if row_mask is None else row_mask[j]
        s = rx.sums(arrs[p], m, k)
        if s is not None:
            out[j] = rx.diff_se(s)[0]
    return out


def assign_random(uni, n_m, rng):
    order = rng.permutation(len(uni))
    a, b = np.zeros(n_m, dtype=bool), np.zeros(n_m, dtype=bool)
    a[uni[order[0::2]]] = True
    b[uni[order[1::2]]] = True
    return a, b


def assign_blocked(uni, n_m, rng, block_codes, check=False):
    blk = block_codes[uni]
    ub, inv = np.unique(blk, return_inverse=True)
    sizes = np.bincount(inv)
    order = rng.permutation(len(ub))
    side = np.zeros(len(ub), dtype=bool)
    na = nb = 0
    for bidx in order:
        if na <= nb:
            side[bidx] = True
            na += sizes[bidx]
        else:
            nb += sizes[bidx]
    a, b = np.zeros(n_m, dtype=bool), np.zeros(n_m, dtype=bool)
    a[uni[side[inv]]] = True
    b[uni[~side[inv]]] = True
    if check:        # V4
        if (a & b).any() or (a | b).sum() != len(uni):
            fail("V4: blocked halves overlap or do not cover the universe")
        if abs(int(a.sum()) - int(b.sum())) > sizes.max():
            fail("V4: blocked halves are not balanced within the largest block")
        for code in ub[:200]:
            sel = uni[blk == code]
            if not (a[sel].all() or b[sel].all()):
                fail("V4: a tournament block was split across halves")
    return a, b


def split_loop(arrs, players, uni, n_m, rng, n_splits, blocked_codes=None, label=''):
    gms = [arrs[p]['gm'] for p in players]
    draws = {k: np.full(n_splits, np.nan) for k in OUTS}
    npl = {k: np.zeros(n_splits) for k in OUTS}
    for s in range(n_splits):
        a, b = (assign_blocked(uni, n_m, rng, blocked_codes, check=(s < 20)) if blocked_codes is not None
                else assign_random(uni, n_m, rng))
        ma = [a[g] for g in gms]
        mb = [b[g] for g in gms]
        for k in OUTS:
            da, db = half_vals(arrs, players, k, ma, mb)
            draws[k][s] = rx.rel_from(da, db)
            npl[k][s] = int((~np.isnan(da) & ~np.isnan(db)).sum())
        if (s + 1) % 250 == 0:
            log(f"  {label} {s + 1}/{n_splits} splits")
    return draws, npl


def summarize(d, n):
    v = d[~np.isnan(d)]
    if len(v) == 0:
        return dict(median=np.nan, p2_5=np.nan, p97_5=np.nan, share_ge_070=np.nan, n_valid=0, players_median=np.nan)
    return dict(median=float(np.median(v)), p2_5=float(np.percentile(v, 2.5)), p97_5=float(np.percentile(v, 97.5)),
                share_ge_070=float((v >= 0.70).mean()), n_valid=len(v), players_median=float(np.median(n[~np.isnan(d)])))


# =============================================================================
# main per tour
# =============================================================================

def run_tour(tour, n_splits, validate_only, tasks):
    t0 = time.time()
    log(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    base_players, matches, base_half_map, summary, base_pts = aa.load_tour(tour)
    rng = np.random.default_rng(SEED)
    pool_lo, half_map_E, tab, sorted_ids, gm = extended_table(tour, matches, base_half_map, base_pts, rng)
    n_m = len(sorted_ids)
    arrs_full = asa.player_arrays(tab, pool_lo, gm)
    arrs = {p: {k: arrs_full[p][k] for k in KEEP} for p in pool_lo}
    cnt = pd.concat([matches['Player 1'], matches['Player 2']]).value_counts()
    if set(cnt[cnt >= 40].index) != set(base_players):
        fail("V1: the 40-match pool differs from the paper's player list")
    log(f"V1 40-match pool equals the paper's {len(base_players)} players")
    in_match = {m: i for i, m in enumerate(sorted_ids)}
    base_idx = np.array(sorted(in_match[m] for m in base_half_map))

    meta = matches.drop_duplicates('match_id').set_index('match_id').reindex(sorted_ids)
    tn = meta['Tournament'].astype(str).str.strip().str.lower().values
    block_key = np.array([f"{t}|{i[:4]}" for t, i in zip(tn, sorted_ids)])
    block_codes = pd.factorize(block_key)[0]
    mc, _ = cac.match_covariates(matches, sorted_ids)
    slam = mc[:, 5].astype(bool)
    if slam.sum() != int(pd.Series(tn).isin(cac.SLAMS).sum()):
        fail("V5: Grand Slam flag differs from the tournament list")
    if (slam | ~slam).sum() != n_m:
        fail("V5: strata do not partition the matches")
    log(f"V5 Grand Slam flag: {int(slam.sum())} of {n_m} matches; blocks (tournament editions): "
        f"{len(np.unique(block_codes))}")

    committed = pd.read_csv(os.path.join(OUT_DIR, 'allshots_reliability.csv'))
    committed = committed[committed['tour'] == tour].set_index('outcome')['median']
    cutoffs = [c for c in CUTOFFS if f'c1_{c}' in tasks]
    rows_c1, rows_c2, rows_c3, rows_c4 = [], [], [], []

    # ---- C1 ----
    for c in cutoffs:
        pool = [p for p in pool_lo if cnt[p] >= c]
        pset = set(pool)
        involved = (meta['Player 1'].isin(pset) | meta['Player 2'].isin(pset)).values
        uni = np.where(involved)[0]
        ns = 100 if validate_only else n_splits
        draws, npl = split_loop(arrs, pool, uni, n_m, np.random.default_rng(SEED + c), ns, label=f"C1 cutoff {c}")
        for k in OUTS:
            sd = np.nanstd(full_scores(arrs, pool, k), ddof=1)
            r = dict(tour=tour, cutoff=c, outcome=k, players=len(pool), median_charted=float(np.median([cnt[p] for p in pool])),
                     universe_matches=len(uni), sd_full_sample=float(sd), **summarize(draws[k], npl[k]))
            rows_c1.append(r)
            log(f"C1 {tour} >= {c:3d} {k:>2s}: players {len(pool):3d}, median {r['median']:+.3f} "
                f"[{r['p2_5']:+.3f}, {r['p97_5']:+.3f}] share>=0.70 {r['share_ge_070']:.1%}  SD {100 * sd:.2f} pp")
        if c == 40:
            for k in OUTS:
                key = {'S': 'serve_clutch', 'Rt': 'return_clutch', 'R1': 'R1_rally_point'}[k]
                d = abs(summarize(draws[k], npl[k])['median'] - committed[key])
                log(f"V3 cutoff 40 {k}: new median vs committed {committed[key]:+.4f}, diff {d:.4f}")
                if d > 0.02:
                    fail(f"V3: {tour} {k} median differs from the committed one by {d:.3f}")
        if validate_only and c == 40:
            break
    # ---- C2 ----
    if validate_only or 'c2' in tasks:
        base_players_l = [p for p in base_players]
        ns = 20 if validate_only else n_splits
        dB, nB = split_loop(arrs, base_players_l, base_idx, n_m, np.random.default_rng(SEED + 500), ns,
                            blocked_codes=block_codes, label="C2 blocked")
        for k in OUTS:
            r = dict(tour=tour, outcome=k, **summarize(dB[k], nB[k]))
            rows_c2.append(r)
            log(f"C2 {tour} blocked {k:>2s}: median {r['median']:+.3f} [{r['p2_5']:+.3f}, {r['p97_5']:+.3f}] "
                f"share>=0.70 {r['share_ge_070']:.1%}; players {r['players_median']:.0f}")
    if validate_only:
        log(f"validation complete for {tour.upper()} in {time.time() - t0:.0f}s")
        return None
    # ---- C3 ----
    bp = base_players
    gms = [arrs[p]['gm'] for p in bp]
    strata = {'slam': np.intersect1d(base_idx, np.where(slam)[0]), 'other': np.intersect1d(base_idx, np.where(~slam)[0])}
    rel_med = {}
    for name, uni in (strata.items() if 'c3' in tasks else []):
        d3, n3 = split_loop(arrs, bp, uni, n_m, np.random.default_rng(SEED + 600 + len(name)), n_splits,
                            label=f"C3 {name}")
        for k in OUTS:
            s = summarize(d3[k], n3[k])
            rel_med[(name, k)] = s['median']
            rows_c3.append(dict(tour=tour, kind='reliability', stratum=name, outcome=k, matches=len(uni), **s))
            log(f"C3 {tour} {name:>5s} {k:>2s}: matches {len(uni)}, players ~{s['players_median']:.0f}, median {s['median']:+.3f} "
                f"[{s['p2_5']:+.3f}, {s['p97_5']:+.3f}] share>=0.70 {s['share_ge_070']:.1%}")
    for k in (OUTS if 'c3' in tasks else []):
        a = full_scores(arrs, bp, k, [slam[g] for g in gms])
        b = full_scores(arrs, bp, k, [~slam[g] for g in gms])
        ok = ~np.isnan(a) & ~np.isnan(b)
        dif = a[ok] - b[ok]
        r = np.corrcoef(a[ok], b[ok])[0, 1] if ok.sum() > 3 else np.nan
        ra, rb = rel_med[('slam', k)], rel_med[('other', k)]
        att = np.sqrt(ra * rb) if (not np.isnan(ra) and not np.isnan(rb) and ra > 0 and rb > 0) else np.nan
        rows_c3.append(dict(tour=tour, kind='contrast', outcome=k, players=int(ok.sum()),
                            mean_slam_minus_other_pp=100 * dif.mean(), se_pp=100 * dif.std(ddof=1) / np.sqrt(len(dif)),
                            r_slam_other=r, disattenuated_r=(r / att if not np.isnan(att) else np.nan)))
        log(f"C3 {tour} {k:>2s}: Slam - other {100 * dif.mean():+.2f} pp (SE {100 * dif.std(ddof=1) / np.sqrt(len(dif)):.2f}, "
            f"n {int(ok.sum())}); r(Slam, other) {r:+.3f}; disattenuated {r / att if not np.isnan(att) else float('nan'):+.2f}")
    # ---- C4 ----
    allm = matches.drop_duplicates('match_id')
    long = pd.concat([allm[['match_id', 'Player 1', 'Tournament']].rename(columns={'Player 1': 'p'}),
                      allm[['match_id', 'Player 2', 'Tournament']].rename(columns={'Player 2': 'p'})])
    long['slam'] = long['Tournament'].astype(str).str.strip().str.lower().isin(cac.SLAMS)
    share = long.groupby('p')['slam'].mean()
    counts = long.groupby('p')['slam'].size()
    for k in (OUTS if 'c4' in tasks else []):
        sc_ = full_scores(arrs, bp, k)
        ok = ~np.isnan(sc_)
        for pred_name, pred in (('charted_matches', counts), ('slam_share', share)):
            x = np.array([pred[p] for p in bp])
            rho, pv = stats.spearmanr(x[ok], sc_[ok])
            rows_c4.append(dict(tour=tour, outcome=k, predictor=pred_name, n=int(ok.sum()), spearman=rho, p=pv,
                                significant_bonferroni_12=bool(pv < ALPHA_C4)))
            log(f"C4 {tour} {k:>2s} vs {pred_name:<16s}: rho {rho:+.3f} p {pv:.3f} n {int(ok.sum())}")
    log(f"{tour.upper()} done in {time.time() - t0:.0f}s")
    return pd.DataFrame(rows_c1), pd.DataFrame(rows_c2), pd.DataFrame(rows_c3), pd.DataFrame(rows_c4)


PART_DIR = os.path.join(OUT_DIR, '_selection_parts')
NAMES = ['cutoff', 'blocked', 'strata', 'charting']


def merge():
    out = {}
    for nme in NAMES:
        files = sorted(x for x in os.listdir(PART_DIR) if x.startswith(f'{nme}__'))
        if not files:
            raise SystemExit(f"no part files for {nme}")
        out[nme] = pd.concat([pd.read_csv(os.path.join(PART_DIR, x)) for x in files], ignore_index=True)
    c1, c2 = out['cutoff'], out['blocked']
    ref = c1[c1['cutoff'] == 40].set_index(['tour', 'outcome'])['median']
    c2['matched_split_median'] = [ref[(t, o)] for t, o in zip(c2['tour'], c2['outcome'])]
    c2['blocked_minus_matched'] = c2['median'] - c2['matched_split_median']
    out['blocked'] = c2
    out['cutoff'] = c1.sort_values(['tour', 'outcome', 'cutoff']).reset_index(drop=True)
    for nme, d in out.items():
        d.to_csv(os.path.join(OUT_DIR, f'selection_checks_{nme}.csv'), index=False)
    log("wrote results/applications/selection_checks_{cutoff,blocked,strata,charting}.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=1000)
    ap.add_argument('--validate-only', action='store_true')
    ap.add_argument('--tours', nargs='+', default=['atp', 'wta'])
    ap.add_argument('--tasks', nargs='+', default=[f'c1_{c}' for c in CUTOFFS] + ['c2', 'c3', 'c4'])
    ap.add_argument('--tag', default='all')
    ap.add_argument('--merge', action='store_true')
    args = ap.parse_args()
    if args.merge:
        merge()
        return
    os.makedirs(PART_DIR, exist_ok=True)
    for tour in args.tours:
        res = run_tour(tour, args.splits, args.validate_only, set(args.tasks))
        if res is not None:
            for nme, d in zip(NAMES, res):
                if len(d):
                    d.to_csv(os.path.join(PART_DIR, f'{nme}__{tour}__{args.tag}.csv'), index=False)
    log("VALIDATION ONLY: all checks passed" if args.validate_only else "part files written")


if __name__ == '__main__':
    main()
