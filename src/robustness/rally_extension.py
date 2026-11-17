"""
rally_extension.py -- carries the practice-side analyses of Section 6 and the
robustness checks of Section 4.3 to rally points, as pre-registered in
docs/combined/rally_extension_preregistration.md (written 2026-11-16, before
this script was run).

Outcomes: R1 rally-phase point clutch, R2 unforced-error clutch (all shots),
R3 winner clutch (all shots); S and Rt (the paper's serve and return clutch)
run through the same code as calibration. For each outcome and tour:
  1. matches needed for reliability 0.70 (from allshots_reliability.csv);
  2. true spread (match-clustered two-stage estimator), noise SE, implied reliability;
  3. match-win translation (R1 only);
  4. match-level cluster bootstrap rank intervals (quartile thresholds held at
     full-sample values);
  5. empirical-Bayes shrinkage, original split and random splits;
  6. leverage-variant sensitivity (original split plus 200 random splits).

Validation first: original-split reliabilities of R1, R2, R3, S and Rt must
match allshots_reliability.csv / the paper to within 0.001, or the script aborts.

Usage: python src/robustness/rally_extension.py [--boot N] [--splits N] [--shrink-splits N]
Writes results/applications/rally_extension_*.csv
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
import formulas as f

SEED = 20261116
OUTS = ['R1', 'R2', 'R3', 'S', 'Rt']
NAMES = {'R1': 'Rally-phase point clutch', 'R2': 'Unforced-error clutch (all shots)',
         'R3': 'Winner clutch (all shots)', 'S': 'Serve clutch (paper)', 'Rt': 'Return clutch (paper)'}
ALLSHOT_KEY = {'R1': 'R1_rally_point', 'R2': 'R2_error_all', 'R3': 'R3_winner_all',
               'S': 'serve_clutch', 'Rt': 'return_clutch'}
VARIANTS = ['leverage_p60', 'leverage_p70', 'leverage_tiered', 'leverage_empirical']
MEDIAN_MATCHES = {'atp': 74, 'wta': 64}
MIN_PTS, MIN_SHOTS = asa.MIN_PTS, asa.MIN_SHOTS


# =============================================================================
# per-player, per-match bucket sums
# =============================================================================

def sums(d, m, k):
    """Top/bottom-quartile numerator and denominator sums per match for outcome k
    on the points selected by mask m. Returns None if the player lacks data.
    (g, Nt, Dt, Nb, Db, sign) with g the global match index of each row."""
    keep = m & ~np.isnan(d['lev'])
    v = {key: x[keep] for key, x in d.items()}
    if k in ('S', 'Rt'):
        r = v['is_serve'] == (k == 'S')
        v = {key: x[r] for key, x in v.items()}
    n = len(v['lev'])
    if n < 4 * MIN_PTS:
        return None
    q25, q75 = np.quantile(v['lev'], [0.25, 0.75])
    top, bot = v['lev'] >= q75, v['lev'] <= q25
    if k == 'R1':
        top, bot = top & v['rally'], bot & v['rally']
        num, den, sign, mn = v['won'], np.ones(n), 1.0, MIN_PTS
    elif k in ('S', 'Rt'):
        num, den, sign, mn = v['won'], np.ones(n), 1.0, MIN_PTS
    elif k == 'R2':
        num, den, sign, mn = v['ufe'], v['shots'], -1.0, MIN_SHOTS
    else:
        num, den, sign, mn = v['win'], v['shots'], 1.0, MIN_SHOTS
    if k in ('R1', 'S', 'Rt'):
        if top.sum() < mn or bot.sum() < mn:
            return None
    elif den[top].sum() < mn or den[bot].sum() < mn:
        return None
    g_u, inv = np.unique(v['gm'], return_inverse=True)
    nm = len(g_u)

    def bc(w):
        return np.bincount(inv, weights=w, minlength=nm)
    return (g_u, bc(num * top), bc(den * top), bc(num * bot), bc(den * bot), sign)


def diff_se(s):
    """Rate difference and its match-clustered (sandwich) SE from per-match sums."""
    g, Nt, Dt, Nb, Db, sign = s
    rt, rb = Nt.sum() / Dt.sum(), Nb.sum() / Db.sum()
    diff = sign * (rt - rb)
    e = sign * ((Nt - rt * Dt) / Dt.sum() - (Nb - rb * Db) / Db.sum())
    M = len(g)
    se = np.sqrt(M / (M - 1) * (e ** 2).sum()) if M > 1 else np.nan
    return diff, se


def tau_moment(diff, se):
    v = np.var(diff, ddof=1) - np.mean(se ** 2)
    return np.sqrt(max(v, 0.0)), max(v, 0.0)


def need(rho, tour, target=0.70):
    if rho <= 0:
        return np.nan
    return target * (1 - rho) / (rho * (1 - target)) * MEDIAN_MATCHES[tour]


def fmt_need(x):
    return 'unbounded' if np.isnan(x) else f'{x:,.0f}'


def half_stats(arrs, players, k, in_a_by_player):
    da = np.full(len(players), np.nan); sa = da.copy()
    db = da.copy(); sb = da.copy()
    for j, p in enumerate(players):
        a = sums(arrs[p], in_a_by_player[j], k)
        b = sums(arrs[p], ~in_a_by_player[j], k)
        if a is not None:
            da[j], sa[j] = diff_se(a)
        if b is not None:
            db[j], sb[j] = diff_se(b)
    return da, sa, db, sb


def rel_from(da, db):
    ok = ~np.isnan(da) & ~np.isnan(db)
    if ok.sum() < 10:
        return np.nan
    return f.spearman_brown(np.corrcoef(da[ok], db[ok])[0, 1])


def shrink(raw, se):
    tau2 = max(0.0, np.var(raw, ddof=1) - np.mean(se ** 2))
    b = tau2 / (tau2 + se ** 2) if tau2 > 0 else np.zeros_like(se)
    return raw.mean() + b * (raw - raw.mean())


def shrunk_rel(da, sa, db, sb):
    """Spearman-Brown reliability of the shrunk half scores. If a half has no
    estimated true variance, shrinkage collapses it to a constant (no signal): 0."""
    xa, xb = shrink(da, sa), shrink(db, sb)
    if np.std(xa) < 1e-12 or np.std(xb) < 1e-12:
        return 0.0
    r = max(np.corrcoef(xa, xb)[0, 1], -0.999)
    return f.spearman_brown(r)


def run_tour(tour, n_boot, n_splits, n_shrink):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    n_m = len(sorted_ids)
    orig_assign = np.array([half_map[m] == 'A' for m in sorted_ids])
    arrs = asa.player_arrays(tab, players, gm)
    allsh = pd.read_csv(os.path.join(aa.OUT_DIR, 'allshots_reliability.csv'))
    allsh = allsh[allsh['tour'] == tour].set_index('outcome')

    # ---- validation on the original split ----
    ia = [orig_assign[arrs[p]['gm']] for p in players]
    orig = {}
    for k in OUTS:
        da, sa, db, sb = half_stats(arrs, players, k, ia)
        orig[k] = (da, sa, db, sb)
        r = rel_from(da, db)
        ref = allsh.loc[ALLSHOT_KEY[k], 'original_split']
        print(f"VALIDATION {k}: new {r:+.4f} reference {ref:+.4f}")
        if abs(r - ref) > 0.001:
            raise SystemExit(f"{tour.upper()}: validation failed for {k}.")
    print("VALIDATION PASS")

    rng = np.random.default_rng(SEED)
    spread_rows, shrink_rows, rank_rows, rank_summ, variant_rows = [], [], [], [], []
    full_stats = {}
    for k in OUTS:
        # ---- 1-2: data needed and true spread ----
        ok, diffs, ses, names, parts = [], [], [], [], {}
        for j, p in enumerate(players):
            s = sums(arrs[p], np.ones(len(arrs[p]['lev']), dtype=bool), k)
            if s is None:
                continue
            d, se = diff_se(s)
            ok.append(j); diffs.append(d); ses.append(se); names.append(p); parts[p] = s
        diffs, ses = np.array(diffs), np.array(ses)
        n = len(diffs)
        tau, v = tau_moment(diffs, ses)
        ms2 = float(np.mean(ses ** 2))
        rel_impl = v / (v + ms2)
        bt, br = np.zeros(2000), np.zeros(2000)
        for b in range(2000):
            idx = rng.integers(0, n, n)
            t, vv = tau_moment(diffs[idx], ses[idx])
            bt[b] = t
            br[b] = vv / (vv + np.mean(ses[idx] ** 2))
        lo, hi = np.percentile(bt, [2.5, 97.5])
        rlo, rhi = np.percentile(br, [2.5, 97.5])
        a = allsh.loc[ALLSHOT_KEY[k]]
        spread_rows.append({
            'tour': tour, 'outcome': k, 'label': NAMES[k], 'n_players': n,
            'rel_median': a['median'], 'rel_p2_5': a['p2_5'], 'rel_p97_5': a['p97_5'],
            'matches_needed': need(a['median'], tour),
            'matches_needed_lo': need(a['p97_5'], tour), 'matches_needed_hi': need(a['p2_5'], tour),
            'true_sd_pp': 100 * tau, 'true_sd_lo': 100 * lo, 'true_sd_hi': 100 * hi,
            'noise_se_pp': 100 * np.sqrt(ms2), 'implied_reliability': rel_impl,
            'implied_rel_lo': rlo, 'implied_rel_hi': rhi})
        print(f"[{k}] n={n} reliability {a['median']:.2f}; matches needed {fmt_need(need(a['median'], tour))} "
              f"[{fmt_need(need(a['p97_5'], tour))}, {fmt_need(need(a['p2_5'], tour))}]; true SD {100 * tau:.2f} "
              f"[{100 * lo:.2f}, {100 * hi:.2f}] pp, noise SE {100 * np.sqrt(ms2):.2f}, implied rel {rel_impl:.2f} "
              f"[{rlo:.2f}, {rhi:.2f}]")
        full_stats[k] = (names, diffs, parts)

        # ---- 3: match-win translation (R1) ----
        if k == 'R1':
            top_m, bot_m = [], []
            for p in players:
                d = arrs[p]
                keep = ~np.isnan(d['lev'])
                lev, rally, g = d['lev'][keep], d['rally'][keep], d['gm'][keep]
                q25, q75 = np.quantile(lev, [0.25, 0.75])
                nm_p = len(np.unique(g))
                top_m.append(lev[(lev >= q75) & rally].sum() / nm_p)
                bot_m.append(lev[(lev <= q25) & rally].sum() / nm_p)
            tm, bm = float(np.median(top_m)), float(np.median(bot_m))
            spread_rows[-1].update(top_rally_leverage_per_match=tm, bottom_rally_leverage_per_match=bm,
                                   winprob_pp_low=100 * tau * bm, winprob_pp_high=100 * tau * tm)
            print(f"      R1 leverage mass per match: top {tm:.2f}, bottom {bm:.2f}; one true SD = "
                  f"{tau * bm * 100:.2f} to {tau * tm * 100:.2f} pp match-win probability")

        # ---- 4: cluster bootstrap rank intervals (fixed thresholds) ----
        gl = [parts[p][0] for p in names]
        counts = rng.multinomial(n_m, np.full(n_m, 1.0 / n_m), size=n_boot).astype(float)
        mat = np.full((n_boot, n), np.nan)
        for j, p in enumerate(names):
            g, Nt, Dt, Nb, Db, sign = parts[p]
            W = counts[:, g]
            nt, dt, nb, db = W @ Nt, W @ Dt, W @ Nb, W @ Db
            with np.errstate(divide='ignore', invalid='ignore'):
                val = sign * (nt / dt - nb / db)
            val[(dt <= 0) | (db <= 0)] = np.nan
            mat[:, j] = val
        pt = diffs
        lo_s, hi_s = np.nanpercentile(mat, [2.5, 97.5], axis=0)
        ranks = np.argsort(np.argsort(-np.nan_to_num(mat, nan=-np.inf), axis=1), axis=1) + 1
        rlo_r, rhi_r = np.percentile(ranks, [2.5, 97.5], axis=0)
        pt_rank = np.argsort(np.argsort(-pt)) + 1
        excl = int(((lo_s > pt.mean()) | (hi_s < pt.mean())).sum())
        order = np.argsort(pt_rank)[:10]
        width = float(np.median(rhi_r - rlo_r))
        rank_summ.append({'tour': tour, 'outcome': k, 'n_players': n, 'median_rank_width': width,
                          'n_excluding_pool_mean': excl, 'top10_within_top20': int((rhi_r[order] <= 20).sum())})
        print(f"      rank intervals: median width {width:.1f} of {n}; score intervals excluding pool mean {excl}/{n}")
        rank_rows.append(pd.DataFrame({'tour': tour, 'outcome': k, 'player': names, 'score': pt,
                                       'score_lo': lo_s, 'score_hi': hi_s, 'rank': pt_rank,
                                       'rank_lo': rlo_r, 'rank_hi': rhi_r}))

        # ---- 5: shrinkage on the original split ----
        da, sa, db, sb = orig[k]
        okk = ~np.isnan(da) & ~np.isnan(db)
        raw_rel = rel_from(da, db)
        sh_rel = shrunk_rel(da[okk], sa[okk], db[okk], sb[okk])
        raws, shs = [], []
        for s_ in range(n_shrink):
            order = rng.permutation(n_m)
            assign = np.zeros(n_m, dtype=int)
            assign[order[1::2]] = 1
            in_a = assign == 0
            da_, sa_, db_, sb_ = half_stats(arrs, players, k, [in_a[arrs[p]['gm']] for p in players])
            o_ = ~np.isnan(da_) & ~np.isnan(db_)
            if o_.sum() < 10:
                continue
            raws.append(rel_from(da_, db_))
            shs.append(shrunk_rel(da_[o_], sa_[o_], db_[o_], sb_[o_]))
        shs = np.array(shs); raws = np.array(raws)
        shrink_rows.append({'tour': tour, 'outcome': k, 'label': NAMES[k], 'raw_original_split': raw_rel,
                            'shrunk_original_split': sh_rel, 'raw_random_median': float(np.median(raws)),
                            'shrunk_random_median': float(np.median(shs)),
                            'shrunk_random_p2_5': float(np.percentile(shs, 2.5)),
                            'shrunk_random_p97_5': float(np.percentile(shs, 97.5)),
                            'shrunk_share_at_or_above_070': float((shs >= 0.70).mean())})
        print(f"      shrinkage: original split raw {raw_rel:.3f} -> shrunk {sh_rel:.3f}; random-split median raw "
              f"{np.median(raws):.3f} -> shrunk {np.median(shs):.3f}, share >= 0.70 {(shs >= 0.70).mean():.1%}")

    # ---- 6: leverage variants ----
    orig_lev = tab['leverage_p65'].copy()
    for var in VARIANTS:
        tab['leverage_p65'] = tab[var].values
        arr_v = asa.player_arrays(tab, players, gm)
        for k in OUTS:
            da, sa, db, sb = half_stats(arr_v, players, k, ia)
            r0 = rel_from(da, db)
            draws = []
            for s_ in range(n_splits):
                order = rng.permutation(n_m)
                assign = np.zeros(n_m, dtype=int)
                assign[order[1::2]] = 1
                in_a = assign == 0
                da, sa, db, sb = half_stats(arr_v, players, k, [in_a[arr_v[p]['gm']] for p in players])
                draws.append(rel_from(da, db))
            d = np.array([x for x in draws if not np.isnan(x)])
            variant_rows.append({'tour': tour, 'variant': var, 'outcome': k, 'original_split': r0,
                                 'median': np.median(d), 'p2_5': np.percentile(d, 2.5),
                                 'p97_5': np.percentile(d, 97.5), 'share_at_or_above_070': float((d >= 0.70).mean())})
            print(f"      {var:19s} {k:3s} orig {r0:+.3f} median {np.median(d):+.3f} share>=0.70 {(d >= 0.70).mean():.1%}")
    tab['leverage_p65'] = orig_lev.values
    return (pd.DataFrame(spread_rows), pd.DataFrame(shrink_rows), pd.concat(rank_rows),
            pd.DataFrame(rank_summ), pd.DataFrame(variant_rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--splits', type=int, default=200)
    ap.add_argument('--shrink-splits', type=int, default=1000)
    args = ap.parse_args()
    outs = [[], [], [], [], []]
    for tour in ('atp', 'wta'):
        for lst, df in zip(outs, run_tour(tour, args.boot, args.splits, args.shrink_splits)):
            lst.append(df)
    names = ['spread', 'shrinkage', 'rank_players', 'rank_summary', 'variants']
    for n_, lst in zip(names, outs):
        pd.concat(lst).to_csv(os.path.join(aa.OUT_DIR, f'rally_extension_{n_}.csv'), index=False)
    print(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
