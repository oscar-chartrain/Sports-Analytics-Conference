"""Validity checks: do the stable parts of clutch scores mean anything, and how good is the forehand?

Plan: docs/combined/validity_checks_preregistration.md (written before this script was run).
  V-A  stability beyond ability (early score -> late score, partial on the early overall rate)
  V-B  convergence across indicators (cross-time correlations among 7 outcomes, 21 pairs)
  V-C  forehand and backhand errors: shrunk random-split reliability, true spread, matches needed

    python src/robustness/validity_checks.py [--tours atp wta] [--splits 1000] [--boot 2000] [--validate-only]
Writes results/applications/validity_{stability,convergence,shots}.csv and prints a log.
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats

import applications_analyses as aa
import all_shots_analyses as asa
import rally_extension as rx
import slope_chronological as sc
import formulas as f

SEED = 20261122
OUT_DIR = aa.OUT_DIR
SEVEN = ['serve_clutch', 'return_clutch', 'R1_rally_point', 'R2_error_all', 'R3_winner_all',
         'R4_error_forehand', 'R5_error_backhand']
SHORT = {'serve_clutch': 'S', 'return_clutch': 'Rt', 'R1_rally_point': 'R1', 'R2_error_all': 'R2',
         'R3_winner_all': 'R3', 'R4_error_forehand': 'R4', 'R5_error_backhand': 'R5'}
CHRON_KEY = {'S': 'serve_clutch'}      # committed chronological file uses S, Rt, R1, R2, R3
ALPHA_PAIR = 0.05 / 21
ALPHA_PARTIAL = 0.05 / 7
FAM = {'R4': 'forehand', 'R5': 'backhand'}


def log(*a):
    print(*a, flush=True)


def fail(msg):
    raise SystemExit(f"VALIDATION FAILED: {msg}")


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def sums_fam(d, m, fam):
    """Per-match top/bottom-quartile sums for forehand or backhand errors (sign -1), same layout
    and floors as rx.sums for R2/R3 (quartiles from all of the player's points on the mask)."""
    keep = m & ~np.isnan(d['lev'])
    v = {key: x[keep] for key, x in d.items()}
    n = len(v['lev'])
    if n < 4 * asa.MIN_PTS:
        return None
    q25, q75 = np.quantile(v['lev'], [0.25, 0.75])
    top, bot = v['lev'] >= q75, v['lev'] <= q25
    num, den = v[f'ufe_{fam}'], v[f'sh_{fam}']
    if den[top].sum() < asa.MIN_SHOTS or den[bot].sum() < asa.MIN_SHOTS:
        return None
    g_u, inv = np.unique(v['gm'], return_inverse=True)
    nm = len(g_u)

    def bc(w):
        return np.bincount(inv, weights=w, minlength=nm)
    return (g_u, bc(num * top), bc(den * top), bc(num * bot), bc(den * bot), -1.0)


def overall_rates(d, m):
    """Overall (not leverage-split) rate of each of the 7 outcomes' underlying event, on mask m."""
    keep = m & ~np.isnan(d['lev'])
    v = {k: x[keep] for k, x in d.items()}
    out = {}
    out['serve_clutch'] = v['won'][v['is_serve']].mean() if v['is_serve'].any() else np.nan
    out['return_clutch'] = v['won'][~v['is_serve']].mean() if (~v['is_serve']).any() else np.nan
    out['R1_rally_point'] = v['won'][v['rally']].mean() if v['rally'].any() else np.nan
    out['R2_error_all'] = v['ufe'].sum() / max(v['shots'].sum(), 1)
    out['R3_winner_all'] = v['win'].sum() / max(v['shots'].sum(), 1)
    out['R4_error_forehand'] = v['ufe_forehand'].sum() / max(v['sh_forehand'].sum(), 1)
    out['R5_error_backhand'] = v['ufe_backhand'].sum() / max(v['sh_backhand'].sum(), 1)
    out['_counts'] = (len(v['lev']), v['shots'].sum(), v['ufe'].sum(), v['won'].sum())
    return out


def corr(x, y):
    ok = ~np.isnan(x) & ~np.isnan(y)
    if ok.sum() < 10 or np.std(x[ok]) < 1e-12 or np.std(y[ok]) < 1e-12:
        return np.nan, int(ok.sum())
    return float(np.corrcoef(x[ok], y[ok])[0, 1]), int(ok.sum())


def fisher_p(r, n):
    if np.isnan(r) or n < 5:
        return np.nan
    z = np.arctanh(np.clip(r, -0.9999, 0.9999)) * np.sqrt(n - 3)
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def partial_r(x, y, z):
    """Correlation of x and y after removing the linear effect of z. Returns (r, p, n)."""
    ok = ~np.isnan(x) & ~np.isnan(y) & ~np.isnan(z)
    n = int(ok.sum())
    if n < 10:
        return np.nan, np.nan, n
    x, y, z = x[ok], y[ok], z[ok]
    rx_ = x - np.polyval(np.polyfit(z, x, 1), z)
    ry_ = y - np.polyval(np.polyfit(z, y, 1), z)
    r = float(np.corrcoef(rx_, ry_)[0, 1])
    t = r * np.sqrt((n - 3) / max(1 - r * r, 1e-12))
    p = float(2 * (1 - stats.t.cdf(abs(t), n - 3)))
    return r, p, n


# ----------------------------------------------------------------------------
# main per-tour
# ----------------------------------------------------------------------------

def run_tour(tour, n_splits, n_boot, validate_only):
    t0 = time.time()
    log(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    dates = [s[:8] for s in sorted_ids]
    assert dates == sorted(dates), 'match ids are not date-ordered'
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    n_m = len(sorted_ids)
    arrs = asa.player_arrays(tab, players, gm)
    rng = np.random.default_rng(SEED + (0 if tour == 'atp' else 1000))
    np_ = len(players)

    # chronological halves
    early = []
    for p in players:
        uniq = np.unique(arrs[p]['gm'])
        first = uniq[:int(np.ceil(len(uniq) / 2))]
        early.append(np.isin(arrs[p]['gm'], first))
    va, vb = asa.half_values(arrs, players, early)
    idx = {k: asa.OUTCOMES.index(k) for k in SEVEN}
    E = {k: va[:, idx[k]] for k in SEVEN}
    L = {k: vb[:, idx[k]] for k in SEVEN}

    # ---- V1: chronological reliability equals the committed values ----
    com = pd.read_csv(os.path.join(OUT_DIR, 'chronological_reliability.csv'))
    com = com[(com['tour'] == tour) & (com['estimator'] == 'quartile')].set_index('outcome')
    for k in SEVEN[:5]:
        r, n = corr(E[k], L[k])
        sb = f.spearman_brown(r)
        ref = com.loc[SHORT[k], 'chronological_spearman_brown']
        log(f"V1 {tour} {SHORT[k]}: chronological SB {sb:+.4f} vs committed {ref:+.4f}")
        if abs(sb - ref) > 0.001:
            fail(f"V1 {tour} {SHORT[k]}: {sb:.4f} vs {ref:.4f}")

    # ---- V2: shot-type sums routine ----
    full_mask = [np.ones(len(arrs[p]['lev']), dtype=bool) for p in players]
    for j, p in enumerate(players[:15]):
        for k, nm in (('R2', 'ufe'), ('R3', 'win')):
            a = rx.sums(arrs[p], full_mask[j], k)
            if a is None:
                continue
            d = arrs[p]
            # replicate via the generic routine with the all-shot columns
            keep = ~np.isnan(d['lev'])
            q25, q75 = np.quantile(d['lev'][keep], [0.25, 0.75])
            top, bot = d['lev'][keep] >= q75, d['lev'][keep] <= q25
            g_u, inv = np.unique(d['gm'][keep], return_inverse=True)
            nmat = len(g_u)
            num = (d['ufe'] if k == 'R2' else d['win'])[keep]
            den = d['shots'][keep]
            b = (np.bincount(inv, weights=num * top, minlength=nmat), np.bincount(inv, weights=den * top, minlength=nmat))
            if not (np.allclose(a[1], b[0], atol=1e-12) and np.allclose(a[2], b[1], atol=1e-12)):
                fail(f"V2 {tour}: per-match sums differ from rx.sums for {k}")
    for j, p in enumerate(players):
        for k in ('R4', 'R5'):
            s = sums_fam(arrs[p], full_mask[j], FAM[k])
            ref = asa.evaluate(arrs[p], full_mask[j])['R4_error_forehand' if k == 'R4' else 'R5_error_backhand']
            if s is None:
                if not np.isnan(ref):
                    fail(f"V2 {tour} {p} {k}: sums_fam returned None but evaluate has a value")
                continue
            val = rx.diff_se(s)[0]
            if abs(val - ref) > 1e-12:
                fail(f"V2 {tour} {p} {k}: {val} vs evaluate {ref}")
    log(f"V2 {tour}: shot-type sums reproduce rx.sums (R2, R3) and asa.evaluate (R4, R5) for every player")

    # ---- V3: overall rates and counts ----
    for j, p in enumerate(players):
        e_, l_, a_ = overall_rates(arrs[p], early[j]), overall_rates(arrs[p], ~early[j]), overall_rates(arrs[p], full_mask[j])
        for c in range(4):
            if abs((e_['_counts'][c] + l_['_counts'][c]) - a_['_counts'][c]) > 1e-9:
                fail(f"V3 {tour} {p}: early plus late counts differ from full-sample counts")
    log(f"V3 {tour}: early plus late counts equal full-sample counts for every player")

    # ---- V-A: stability and partial stability ----
    rate_e = {k: np.array([overall_rates(arrs[p], early[j])[k] for j, p in enumerate(players)]) for k in SEVEN}
    stab_rows = []
    stab = {}
    for k in SEVEN:
        r, n = corr(E[k], L[k])
        pr, pp, npart = partial_r(E[k], L[k], rate_e[k])
        (rlo, rhi), (slo, shi) = sc.boot_r(E[k], L[k], rng, 50 if validate_only else n_boot)
        stab[k] = r
        stab_rows.append(dict(tour=tour, outcome=k, n=n, early_late_r=r, r_lo=rlo, r_hi=rhi,
                              chronological_sb=f.spearman_brown(r), sb_lo=slo, sb_hi=shi,
                              partial_r=pr, partial_p=pp, partial_n=npart,
                              partial_keeps_half=bool(pr >= 0.5 * r and pp < ALPHA_PARTIAL) if not np.isnan(pr) else False))
        log(f"VA {tour} {SHORT[k]:>2s}: early-late r {r:+.3f} [{rlo:+.2f}, {rhi:+.2f}]; partial on overall rate {pr:+.3f} "
            f"(p {pp:.4f}, n {npart})")

    # ---- V-B: cross-time correlations ----
    conv_rows = []
    pairs = [(SEVEN[i], SEVEN[j]) for i in range(7) for j in range(i + 1, 7)]
    cross = {}
    for x, y in pairs:
        r1, n1 = corr(E[x], L[y])
        r2, n2 = corr(E[y], L[x])
        r = np.nanmean([r1, r2])
        n = min(n1, n2)
        p = fisher_p(r, n)
        att = np.sqrt(stab[x] * stab[y]) if stab[x] > 0 and stab[y] > 0 else np.nan
        cross[(x, y)] = r
        conv_rows.append(dict(tour=tour, outcome_x=x, outcome_y=y, early_x_late_y=r1, early_y_late_x=r2, cross_r=r, n=n,
                              p=p, below_bonferroni=bool(p < ALPHA_PAIR), disattenuated_r=(r / att if not np.isnan(att) else np.nan)))
        log(f"VB {tour} {SHORT[x]:>2s}-{SHORT[y]:<2s}: cross-time r {r:+.3f} (p {p:.4f}, n {n}); "
            f"stabilities {stab[x]:+.2f}, {stab[y]:+.2f}; disattenuated {conv_rows[-1]['disattenuated_r']:+.2f}")
    if len(conv_rows) != 21 or any(np.isnan(c['early_x_late_y']) or np.isnan(c['early_y_late_x']) for c in conv_rows):
        log("V4 NOTE: some pair lacks one direction")
    else:
        log("V4: every one of the 21 pairs uses both directions")
    # mean cross-time correlation with a player bootstrap
    def mean_cross(ix):
        vals = []
        for x, y in pairs:
            a, _ = corr(E[x][ix], L[y][ix])
            b, _ = corr(E[y][ix], L[x][ix])
            vals.append(np.nanmean([a, b]))
        return np.nanmean(vals)
    mc = mean_cross(np.arange(np_))
    nb = 40 if validate_only else n_boot
    bs = [mean_cross(rng.integers(0, np_, np_)) for _ in range(nb)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    same = np.nanmean(list(stab.values()))
    n_sig = int(sum(c['below_bonferroni'] for c in conv_rows))
    conv_rows.append(dict(tour=tour, outcome_x='MEAN of 21 pairs', outcome_y='', cross_r=mc, early_x_late_y=lo, early_y_late_x=hi,
                          n=np_, p=np.nan, below_bonferroni=n_sig, disattenuated_r=mc / same))
    log(f"VB {tour}: mean cross-time r {mc:+.3f} [{lo:+.3f}, {hi:+.3f}], mean same-outcome stability {same:+.3f}; "
        f"pairs below {ALPHA_PAIR:.4f}: {n_sig} of 21")

    # ---- V-C: forehand / backhand ----
    shot_rows = []
    ns = 40 if validate_only else n_splits
    committed = pd.read_csv(os.path.join(OUT_DIR, 'allshots_reliability.csv'))
    committed = committed[committed['tour'] == tour].set_index('outcome')['median']
    for k in ('R4', 'R5', 'R2', 'R3'):
        fam = FAM.get(k)

        def half_pair(ia_list):
            da = np.full(np_, np.nan); sa = da.copy(); db = da.copy(); sb_ = da.copy()
            for j, p in enumerate(players):
                if fam:
                    a = sums_fam(arrs[p], ia_list[j], fam); b = sums_fam(arrs[p], ~ia_list[j], fam)
                else:
                    a = rx.sums(arrs[p], ia_list[j], k); b = rx.sums(arrs[p], ~ia_list[j], k)
                if a is not None:
                    da[j], sa[j] = rx.diff_se(a)
                if b is not None:
                    db[j], sb_[j] = rx.diff_se(b)
            return da, sa, db, sb_
        raw, shr = [], []
        for _ in range(ns):
            order = rng.permutation(n_m)
            in_a = np.zeros(n_m, dtype=bool); in_a[order[0::2]] = True
            ia = [in_a[arrs[p]['gm']] for p in players]
            da, sa, db, sb_ = half_pair(ia)
            raw.append(rx.rel_from(da, db))
            ok = ~np.isnan(da) & ~np.isnan(db)
            shr.append(rx.shrunk_rel(da[ok], sa[ok], db[ok], sb_[ok]) if ok.sum() >= 10 else np.nan)
        raw, shr = np.array(raw), np.array(shr)
        # full-sample spread
        d_, s_ = [], []
        for j, p in enumerate(players):
            s = sums_fam(arrs[p], full_mask[j], fam) if fam else rx.sums(arrs[p], full_mask[j], k)
            if s is None:
                continue
            a, b = rx.diff_se(s)
            d_.append(a); s_.append(b)
        d_, s_ = np.array(d_), np.array(s_)
        n = len(d_)
        tau, v = rx.tau_moment(d_, s_)
        bt = [rx.tau_moment(d_[ii], s_[ii])[0] for ii in (rng.integers(0, n, n) for _ in range(50 if validate_only else n_boot))]
        lo_, hi_ = np.percentile(bt, [2.5, 97.5])
        med_raw, med_shr = float(np.nanmedian(raw)), float(np.nanmedian(shr))
        key = {'R2': 'R2_error_all', 'R3': 'R3_winner_all', 'R4': 'R4_error_forehand', 'R5': 'R5_error_backhand'}[k]
        if k in ('R2', 'R3') and not validate_only and abs(med_raw - committed[key]) > 0.02:
            fail(f"V5 {tour} {k}: raw median {med_raw:.3f} vs committed {committed[key]:.3f}")
        kk = SEVEN[3 + ('R2', 'R3', 'R4', 'R5').index(k)]
        chron = [r for r in stab_rows if r['outcome'] == kk][0]
        row = dict(tour=tour, outcome=key, n_players=n, raw_median=med_raw, raw_p2_5=float(np.nanpercentile(raw, 2.5)),
                   raw_p97_5=float(np.nanpercentile(raw, 97.5)), raw_share_ge_070=float(np.nanmean(raw >= 0.70)),
                   shrunk_median=med_shr, shrunk_p2_5=float(np.nanpercentile(shr, 2.5)), shrunk_p97_5=float(np.nanpercentile(shr, 97.5)),
                   shrunk_share_ge_070=float(np.nanmean(shr >= 0.70)), true_sd_per_shot_pp=100 * tau, true_sd_lo=100 * lo_,
                   true_sd_hi=100 * hi_, noise_se_pp=100 * np.sqrt(np.mean(s_ ** 2)),
                   matches_needed=rx.need(med_raw, tour), chron_sb=chron['chronological_sb'], chron_sb_lo=chron['sb_lo'],
                   chron_sb_hi=chron['sb_hi'])
        shot_rows.append(row)
        log(f"VC {tour} {key}: raw median {med_raw:+.3f} (share>=0.70 {row['raw_share_ge_070']:.1%}); shrunk {med_shr:+.3f} "
            f"[{row['shrunk_p2_5']:+.3f}, {row['shrunk_p97_5']:+.3f}] share>=0.70 {row['shrunk_share_ge_070']:.1%}; "
            f"true SD {100 * tau:.2f} [{100 * lo_:.2f}, {100 * hi_:.2f}] pp per shot, noise SE {row['noise_se_pp']:.2f}; "
            f"matches needed {row['matches_needed']:.0f}; chronological SB {row['chron_sb']:+.3f} [{row['chron_sb_lo']:+.2f}, {row['chron_sb_hi']:+.2f}]")
    log(f"{tour.upper()} done in {time.time() - t0:.0f}s")
    return pd.DataFrame(stab_rows), pd.DataFrame(conv_rows), pd.DataFrame(shot_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tours', nargs='+', default=['atp', 'wta'])
    ap.add_argument('--splits', type=int, default=1000)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--validate-only', action='store_true')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    for tour in args.tours:
        s, c, h = run_tour(tour, args.splits, args.boot, args.validate_only)
        if not args.validate_only:
            for name, d in (('stability', s), ('convergence', c), ('shots', h)):
                d.to_csv(os.path.join(OUT_DIR, f'validity_{name}_{tour}{args.tag}.csv'), index=False)
    log("=== RUN END")


if __name__ == '__main__':
    main()
