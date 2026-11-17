"""
slope_chronological.py -- two analyses pre-registered in
docs/combined/slope_chronological_preregistration.md (written 2026-11-17, before
this script was run):

  1. a continuous per-player leverage-slope clutch score (OLS slope of point-win on
     leverage, scaled by the player's full-sample leverage SD for the role) against the
     paper's quartile score: split-half reliability (original split and 1,000 random
     balanced splits, same splits for both estimators), match-clustered true spread;
  2. a chronological split (each player's earlier half of matches against the later half)
     for the quartile score (S, Rt, R1, R2, R3) and the slope score (S, Rt, R1).

Validation first: the quartile original-split reliabilities of S, Rt and R1 from this code
must match allshots_reliability.csv within 0.001, or the script aborts.

Usage: python src/robustness/slope_chronological.py [--splits N] [--boot N]
Writes results/applications/slope_*.csv and chronological_*.csv
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse

import numpy as np
import pandas as pd

import applications_analyses as aa
import all_shots_analyses as asa
import rally_extension as rx
import formulas as f

SEED = 20261117
MIN_N = 4 * asa.MIN_PTS
SLOPE_OUTS = ['S', 'Rt', 'R1']
QUART_OUTS = ['S', 'Rt', 'R1', 'R2', 'R3']


# =============================================================================
# slope score
# =============================================================================

def select(d, k):
    """Rows of a player's arrays used for outcome k: (x leverage, y won, match index)."""
    keep = ~np.isnan(d['lev'])
    if k == 'S':
        keep &= d['is_serve']
    elif k == 'Rt':
        keep &= ~d['is_serve']
    else:
        keep &= d['rally']
    return d['lev'][keep], d['won'][keep].astype(float), d['gm'][keep]


def slope_score(x, y, g, sd, want_se=False):
    """OLS slope of y on x (times sd); optional match-clustered SE. None if too little data."""
    if len(x) < MIN_N:
        return None
    xc = x - x.mean()
    sxx = float((xc ** 2).sum())
    if sxx <= 1e-12:
        return None
    b = float((xc * (y - y.mean())).sum() / sxx)
    if not want_se:
        return b * sd, b
    resid = y - y.mean() - b * xc
    g_u, inv = np.unique(g, return_inverse=True)
    M = len(g_u)
    if M < 2:
        return None
    e = np.bincount(inv, weights=xc * resid, minlength=M) / sxx
    se = np.sqrt(M / (M - 1) * (e ** 2).sum())
    return b * sd, b, se * sd, se


def build_sel(arrs, players):
    sel = {}
    for p in players:
        for k in SLOPE_OUTS:
            x, y, g = select(arrs[p], k)
            sd = float(np.std(x)) if len(x) > 1 else np.nan
            sel[(p, k)] = (x, y, g, sd)
    return sel


def half_slopes(sel, players, k, ia_by_player, raw=False):
    da = np.full(len(players), np.nan)
    db = da.copy()
    for j, p in enumerate(players):
        x, y, g, sd = sel[(p, k)]
        m = ia_by_player[j](g)
        for out, mask in ((da, m), (db, ~m)):
            r = slope_score(x[mask], y[mask], g[mask], sd)
            if r is not None:
                out[j] = r[1] if raw else r[0]
    return da, db


def rel_pair(da, db):
    ok = ~np.isnan(da) & ~np.isnan(db)
    if ok.sum() < 10:
        return np.nan, np.nan, int(ok.sum())
    r = np.corrcoef(da[ok], db[ok])[0, 1]
    return r, f.spearman_brown(r), int(ok.sum())


def boot_r(da, db, rng, n_boot):
    ok = np.where(~np.isnan(da) & ~np.isnan(db))[0]
    rs, sbs = [], []
    for _ in range(n_boot):
        idx = rng.choice(ok, len(ok))
        if np.std(da[idx]) < 1e-12 or np.std(db[idx]) < 1e-12:
            continue
        r = np.corrcoef(da[idx], db[idx])[0, 1]
        rs.append(r)
        sbs.append(f.spearman_brown(r))
    return np.percentile(rs, [2.5, 97.5]), np.percentile(sbs, [2.5, 97.5])


def run_tour(tour, n_splits, n_boot):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    # match ids start with the date, so sorted order is chronological (ties by id)
    dates = [s[:8] for s in sorted_ids]
    assert dates == sorted(dates), 'match ids are not date-ordered'
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    n_m = len(sorted_ids)
    orig_assign = np.array([half_map[m] == 'A' for m in sorted_ids])
    arrs = asa.player_arrays(tab, players, gm)
    sel = build_sel(arrs, players)
    allsh = pd.read_csv(os.path.join(aa.OUT_DIR, 'allshots_reliability.csv'))
    allsh = allsh[allsh['tour'] == tour].set_index('outcome')
    rng = np.random.default_rng(SEED)

    # ---- validation ----
    ia_orig = [orig_assign[arrs[p]['gm']] for p in players]
    qorig = {}
    for k in QUART_OUTS:
        da, sa, db, sb = rx.half_stats(arrs, players, k, ia_orig)
        qorig[k] = (da, db)
        r = rx.rel_from(da, db)
        ref = allsh.loc[rx.ALLSHOT_KEY[k], 'original_split']
        print(f"VALIDATION {k}: new {r:+.4f} reference {ref:+.4f}")
        if abs(r - ref) > 0.001:
            raise SystemExit(f"{tour.upper()}: validation failed for {k}.")
    print("VALIDATION PASS")

    # ---- Analysis 1a: reliability, original split and random splits ----
    ia_fun_orig = [(lambda g, a=orig_assign: a[g]) for _ in players]
    rel_rows = []
    rand = {(k, e): [] for k in SLOPE_OUTS for e in ('slope', 'raw_slope', 'quartile')}
    for s_ in range(n_splits):
        order = rng.permutation(n_m)
        in_a = np.zeros(n_m, dtype=bool)
        in_a[order[0::2]] = True
        funs = [(lambda g, a=in_a: a[g]) for _ in players]
        ia_list = [in_a[arrs[p]['gm']] for p in players]
        for k in SLOPE_OUTS:
            da, db = half_slopes(sel, players, k, funs)
            rand[(k, 'slope')].append(rel_pair(da, db)[1])
            da, db = half_slopes(sel, players, k, funs, raw=True)
            rand[(k, 'raw_slope')].append(rel_pair(da, db)[1])
            qa, _, qb, _ = rx.half_stats(arrs, players, k, ia_list)
            rand[(k, 'quartile')].append(rx.rel_from(qa, qb))
    for k in SLOPE_OUTS:
        row = {'tour': tour, 'outcome': k}
        da, db = half_slopes(sel, players, k, ia_fun_orig)
        row['slope_original_split'] = rel_pair(da, db)[1]
        row['n_players_slope'] = rel_pair(da, db)[2]
        da, db = half_slopes(sel, players, k, ia_fun_orig, raw=True)
        row['raw_slope_original_split'] = rel_pair(da, db)[1]
        row['quartile_original_split'] = rx.rel_from(*qorig[k])
        for e in ('slope', 'raw_slope', 'quartile'):
            v = np.array([x for x in rand[(k, e)] if not np.isnan(x)])
            row[f'{e}_median'] = float(np.median(v))
            row[f'{e}_p2_5'], row[f'{e}_p97_5'] = [float(x) for x in np.percentile(v, [2.5, 97.5])]
            row[f'{e}_share_at_or_above_070'] = float((v >= 0.70).mean())
        rel_rows.append(row)
        print(f"[{k}] slope orig {row['slope_original_split']:+.3f} median {row['slope_median']:+.3f} "
              f"(share>=0.70 {row['slope_share_at_or_above_070']:.1%}); raw slope median {row['raw_slope_median']:+.3f}; "
              f"quartile orig {row['quartile_original_split']:+.3f} median {row['quartile_median']:+.3f}")

    # ---- Analysis 1b: full-sample score agreement and clustered true spread ----
    spread_rows = []
    for k in SLOPE_OUTS:
        sc, se, qd, names = [], [], [], []
        for j, p in enumerate(players):
            x, y, g, sd = sel[(p, k)]
            r = slope_score(x, y, g, sd, want_se=True)
            s = rx.sums(arrs[p], np.ones(len(arrs[p]['lev']), dtype=bool), k)
            if r is None or s is None:
                continue
            sc.append(r[0]); se.append(r[2]); qd.append(rx.diff_se(s)[0]); names.append(p)
        sc, se, qd = np.array(sc), np.array(se), np.array(qd)
        n = len(sc)
        tau, v = rx.tau_moment(sc, se)
        ms2 = float(np.mean(se ** 2))
        bt, br = np.zeros(2000), np.zeros(2000)
        for b in range(2000):
            idx = rng.integers(0, n, n)
            t, vv = rx.tau_moment(sc[idx], se[idx])
            bt[b] = t
            br[b] = vv / (vv + np.mean(se[idx] ** 2))
        lo, hi = np.percentile(bt, [2.5, 97.5])
        rlo, rhi = np.percentile(br, [2.5, 97.5])
        agree = float(np.corrcoef(sc, qd)[0, 1])
        spread_rows.append({'tour': tour, 'outcome': k, 'n_players': n, 'true_sd_pp': 100 * tau,
                            'true_sd_lo': 100 * lo, 'true_sd_hi': 100 * hi, 'noise_se_pp': 100 * np.sqrt(ms2),
                            'implied_reliability': v / (v + ms2), 'implied_rel_lo': rlo, 'implied_rel_hi': rhi,
                            'corr_with_quartile_score': agree})
        print(f"[{k}] slope score n={n}: true SD {100 * tau:.2f} [{100 * lo:.2f}, {100 * hi:.2f}] pp per 1 SD leverage, "
              f"noise SE {100 * np.sqrt(ms2):.2f}, implied rel {v / (v + ms2):.2f} [{rlo:.2f}, {rhi:.2f}]; "
              f"corr with quartile score {agree:.2f}")

    # ---- Analysis 2: chronological split ----
    chron_ia = []
    for p in players:
        uniq = np.unique(arrs[p]['gm'])
        first = uniq[:int(np.ceil(len(uniq) / 2))]
        chron_ia.append(np.isin(arrs[p]['gm'], first))
    chron_fun = []
    for p in players:
        uniq = np.unique(arrs[p]['gm'])
        first = set(uniq[:int(np.ceil(len(uniq) / 2))].tolist())
        chron_fun.append(lambda g, fs=first: np.isin(g, list(fs)))
    chron_rows = []
    for est, outs in (('quartile', QUART_OUTS), ('slope', SLOPE_OUTS)):
        for k in outs:
            if est == 'quartile':
                da, _, db, _ = rx.half_stats(arrs, players, k, chron_ia)
            else:
                da, db = half_slopes(sel, players, k, chron_fun)
            r, sb, n = rel_pair(da, db)
            (rlo, rhi), (slo, shi) = boot_r(da, db, rng, n_boot)
            row = {'tour': tour, 'estimator': est, 'outcome': k, 'n_players': n,
                   'early_late_r': r, 'r_lo': rlo, 'r_hi': rhi,
                   'chronological_spearman_brown': sb, 'sb_lo': slo, 'sb_hi': shi}
            if est == 'quartile':
                row['interleaved_original'] = allsh.loc[rx.ALLSHOT_KEY[k], 'original_split']
                row['interleaved_median'] = allsh.loc[rx.ALLSHOT_KEY[k], 'median']
            else:
                rr = [x for x in rel_rows if x['outcome'] == k][0]
                row['interleaved_original'] = rr['slope_original_split']
                row['interleaved_median'] = rr['slope_median']
            chron_rows.append(row)
            print(f"[chronological {est} {k}] n={n} early-late r {r:+.3f} [{rlo:+.2f}, {rhi:+.2f}], "
                  f"Spearman-Brown {sb:+.3f} [{slo:+.2f}, {shi:+.2f}]; interleaved original "
                  f"{row['interleaved_original']:+.3f}, median {row['interleaved_median']:+.3f}")
    return pd.DataFrame(rel_rows), pd.DataFrame(spread_rows), pd.DataFrame(chron_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=1000)
    ap.add_argument('--boot', type=int, default=2000)
    args = ap.parse_args()
    outs = [[], [], []]
    for tour in ('atp', 'wta'):
        for lst, df in zip(outs, run_tour(tour, args.splits, args.boot)):
            lst.append(df)
    for name, lst in zip(['slope_reliability', 'slope_spread', 'chronological_reliability'], outs):
        pd.concat(lst).to_csv(os.path.join(aa.OUT_DIR, f'{name}.csv'), index=False)
    print(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
