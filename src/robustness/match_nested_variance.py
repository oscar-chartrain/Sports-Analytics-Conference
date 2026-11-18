"""
match_nested_variance.py -- the three-level (player / match within player / sampling)
variance model pre-registered in docs/combined/match_nested_preregistration.md
(written 2026-11-17, before this script was run).

Per-match clutch score d_pi = mu + u_p + w_pi + e_pi with u_p ~ N(0, tau_p^2),
w_pi ~ N(0, tau_m^2) and e_pi ~ N(0, v_pi) with known v_pi. Fitted by restricted maximum
likelihood (REML; see the pre-registration deviation) on each player's marginal match-vector likelihood. Validation by parametric simulation
first (a tour that fails the recovery rules gets no fits reported), then the fits, player-bootstrap intervals,
likelihood-ratio tests and the sensitivity to the minimum points per bucket.

Usage: python src/robustness/match_nested_variance.py [--boot N] [--sims N]
Writes results/applications/match_nested_*.csv
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse
import warnings

import numpy as np
import pandas as pd
from scipy import optimize, stats

import applications_analyses as aa
import all_shots_analyses as asa
import rally_extension as rx

SEED = 20261118
OUTS = ['S', 'Rt', 'R1']
MIN_BUCKET = 3
SENS = [1, 5]


# =============================================================================
# data: per-player match scores and their sampling variances
# =============================================================================

def build_design(arrs, players, k, min_bucket):
    """Per player: (y in pp, v in pp^2, matches kept, matches available)."""
    out = {}
    for p in players:
        s = rx.sums(arrs[p], np.ones(len(arrs[p]['lev']), dtype=bool), k)
        if s is None:
            continue
        g, Nt, Dt, Nb, Db, sign = s
        pt, pb = Nt.sum() / Dt.sum(), Nb.sum() / Db.sum()
        ok = (Dt >= min_bucket) & (Db >= min_bucket)
        if ok.sum() < 5:
            continue
        y = 100 * sign * (Nt[ok] / Dt[ok] - Nb[ok] / Db[ok])
        v = 1e4 * (pt * (1 - pt) / Dt[ok] + pb * (1 - pb) / Db[ok])
        out[p] = (y, v, int(ok.sum()), int(len(g)))
    return out


def stack(des, order):
    ys = [des[p][0] for p in order]
    vs = [des[p][1] for p in order]
    pid = np.concatenate([np.full(len(y), j) for j, y in enumerate(ys)])
    return np.concatenate(ys), np.concatenate(vs), pid, len(order)


# =============================================================================
# likelihood and fit
# =============================================================================

def nll(par, y, v, pid, P, free):
    """Restricted (REML) negative log-likelihood: the common mean is profiled out by
    generalised least squares and the usual log-determinant correction is added (the
    pre-registered ML was replaced by REML after the validation simulation showed a
    small-sample downward bias with 55 players; see the pre-registration deviation)."""
    tp2 = np.exp(par[0]) if 'p' in free else 0.0
    tm2 = np.exp(par[1]) if 'm' in free else 0.0
    s = tm2 + v
    w = 1.0 / s
    Sw = np.bincount(pid, w, minlength=P)
    Swy = np.bincount(pid, w * y, minlength=P)
    c = 1.0 / (1.0 + tp2 * Sw)                # per-player GLS weight factor
    mu = (Swy * c).sum() / (Sw * c).sum()
    r = y - mu
    Swr = np.bincount(pid, w * r, minlength=P)
    logdet = np.log(s).sum() + np.log1p(tp2 * Sw).sum()
    quad = (w * r * r).sum() - (tp2 * Swr ** 2 * c).sum()
    return 0.5 * (logdet + quad + np.log((Sw * c).sum()))


def fit(y, v, pid, P, free=('p', 'm'), starts=None):
    """Returns (mu, tp2, tm2, loglik-ish nll). tp2 or tm2 are 0 if not in free."""
    if starts is None:
        starts = [(1.0, 1.0), (4.0, 4.0), (0.25, 9.0), (9.0, 0.25)]
    best = None
    bounds = [(-12, 8), (-12, 8)]
    for tp, tm in starts:
        x0 = np.array([np.log(tp), np.log(tm)])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r = optimize.minimize(nll, x0, args=(y, v, pid, P, free), method='L-BFGS-B', bounds=bounds)
        if best is None or r.fun < best.fun:
            best = r
    tp2 = np.exp(best.x[0]) if 'p' in free else 0.0
    tm2 = np.exp(best.x[1]) if 'm' in free else 0.0
    return None, tp2, tm2, best.fun


def derived(tp2, tm2, y, v, pid, P, med_matches, retained_frac):
    s = tm2 + v
    inv_sum = np.bincount(pid, 1.0 / s, minlength=P)
    err = float(np.mean(1.0 / inv_sum))
    rel = tp2 / (tp2 + err)
    vbar = float(v.mean())
    need_ret = np.inf if tp2 < 1e-9 else (0.70 / 0.30) * (tm2 + vbar) / tp2
    return rel, need_ret, need_ret / retained_frac, vbar


# =============================================================================
# validation by simulation
# =============================================================================

def simulate(des, order, tp, tm, rng):
    ys = []
    for p in order:
        v = des[p][1]
        n = len(v)
        ys.append(rng.normal(0, tp) + rng.normal(0, tm, n) + rng.normal(0, np.sqrt(v)))
    return ys


def validate(designs, n_sims, rng):
    print("\nVALIDATION by simulation (true tau_p = 1.5, tau_m = 3.0 pp; then tau_m = 0)")
    for name, des in designs:
        order = list(des.keys())
        ests, ests0 = [], []
        for case, (tp, tm), store in (('a', (1.5, 3.0), ests), ('b', (1.5, 0.0), ests0)):
            for _ in range(n_sims):
                ys = simulate(des, order, tp, tm, rng)
                y = np.concatenate(ys)
                v = np.concatenate([des[p][1] for p in order])
                pid = np.concatenate([np.full(len(a), j) for j, a in enumerate(ys)])
                mu, a, b, _ = fit(y, v, pid, len(order))
                store.append((np.sqrt(a), np.sqrt(b)))
        e, e0 = np.array(ests), np.array(ests0)
        print(f"  {name}: case a mean tau_p {e[:, 0].mean():.2f} (true 1.5), mean tau_m {e[:, 1].mean():.2f} (true 3.0); "
              f"case b mean tau_p {e0[:, 0].mean():.2f}, mean tau_m {e0[:, 1].mean():.2f} (true 0)")
        ok = not (abs(e[:, 0].mean() - 1.5) > 0.15 * 1.5 or abs(e[:, 1].mean() - 3.0) > 0.15 * 3.0 or e0[:, 1].mean() >= 1.0)
        print("VALIDATION PASS" if ok else f"VALIDATION FAILED for {name}: no fits are reported for this tour")
        return ok, {'tau_p_mean_a': e[:, 0].mean(), 'tau_m_mean_a': e[:, 1].mean(),
                    'tau_p_mean_b': e0[:, 0].mean(), 'tau_m_mean_b': e0[:, 1].mean(), 'passed': ok}


# =============================================================================
# main analysis
# =============================================================================

def run_tour(tour, n_boot, n_sims):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    arrs = asa.player_arrays(tab, players, gm)
    rng = np.random.default_rng(SEED + (0 if tour == 'atp' else 1))

    primary = {k: build_design(arrs, players, k, MIN_BUCKET) for k in OUTS}
    ok, vrow = validate([(f'{tour.upper()} serve', primary['S'])], n_sims, rng)
    vrow['tour'] = tour
    if not ok:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame([vrow])

    rows, sens_rows = [], []
    for k in OUTS:
        des = primary[k]
        order = list(des.keys())
        y, v, pid, P = stack(des, order)
        kept = sum(des[p][2] for p in order)
        avail = sum(des[p][3] for p in order)
        frac = kept / avail
        mu, tp2, tm2, f_full = fit(y, v, pid, P)
        _, _, _, f_p0 = fit(y, v, pid, P, free=('m',))
        _, _, _, f_m0 = fit(y, v, pid, P, free=('p',))
        lr_p, lr_m = 2 * (f_p0 - f_full), 2 * (f_m0 - f_full)
        pv_p = 0.5 * stats.chi2.sf(max(lr_p, 0), 1) if lr_p > 0 else 1.0
        pv_m = 0.5 * stats.chi2.sf(max(lr_m, 0), 1) if lr_m > 0 else 1.0
        rel, need_ret, need_ch, vbar = derived(tp2, tm2, y, v, pid, P, rx.MEDIAN_MATCHES[tour], frac)
        # player-bootstrap intervals
        bs = np.zeros((n_boot, 5))
        for b in range(n_boot):
            idx = rng.integers(0, P, P)
            ordb = [order[i] for i in idx]
            yb, vb, pidb, Pb = stack(des, ordb)
            _, a, c, _ = fit(yb, vb, pidb, Pb, starts=[(max(tp2, 0.05), max(tm2, 0.05)), (1.0, 4.0)])
            r_, nr_, nc_, _ = derived(a, c, yb, vb, pidb, Pb, rx.MEDIAN_MATCHES[tour], frac)
            bs[b] = (np.sqrt(a), np.sqrt(c), r_, nr_, nc_)
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        rows.append({
            'tour': tour, 'outcome': k, 'n_players': P, 'matches_kept': kept, 'matches_available': avail,
            'share_kept': frac, 'tau_p_pp': np.sqrt(tp2), 'tau_p_lo': lo[0], 'tau_p_hi': hi[0],
            'tau_m_pp': np.sqrt(tm2), 'tau_m_lo': lo[1], 'tau_m_hi': hi[1],
            'mean_sampling_sd_per_match_pp': np.sqrt(vbar),
            'career_reliability': rel, 'career_rel_lo': lo[2], 'career_rel_hi': hi[2],
            'matches_needed_charted': need_ch, 'matches_needed_lo': lo[4], 'matches_needed_hi': hi[4],
            'median_charted_matches': rx.MEDIAN_MATCHES[tour],
            'lr_tau_p': lr_p, 'p_tau_p': pv_p, 'lr_tau_m': lr_m, 'p_tau_m': pv_m})
        print(f"[{k}] P={P}, matches kept {kept}/{avail} ({frac:.0%}): tau_p {np.sqrt(tp2):.2f} [{lo[0]:.2f}, {hi[0]:.2f}] pp, "
              f"tau_m {np.sqrt(tm2):.2f} [{lo[1]:.2f}, {hi[1]:.2f}] pp, sampling SD/match {np.sqrt(vbar):.2f}; "
              f"career reliability {rel:.2f} [{lo[2]:.2f}, {hi[2]:.2f}]; matches needed {need_ch:,.0f} "
              f"[{lo[4]:,.0f}, {hi[4]:,.0f}] (median charted {rx.MEDIAN_MATCHES[tour]}); "
              f"LR tau_p {lr_p:.1f} p={pv_p:.4f}; LR tau_m {lr_m:.1f} p={pv_m:.4f}")
        for mb in SENS:
            d2 = build_design(arrs, players, k, mb)
            o2 = list(d2.keys())
            y2, v2, pid2, P2 = stack(d2, o2)
            _, a2, c2, _ = fit(y2, v2, pid2, P2)
            kept2 = sum(d2[p][2] for p in o2)
            avail2 = sum(d2[p][3] for p in o2)
            r2, _, nc2, vb2 = derived(a2, c2, y2, v2, pid2, P2, rx.MEDIAN_MATCHES[tour], kept2 / avail2)
            sens_rows.append({'tour': tour, 'outcome': k, 'min_points_per_bucket': mb, 'n_players': P2,
                              'matches_kept': kept2, 'share_kept': kept2 / avail2,
                              'tau_p_pp': np.sqrt(a2), 'tau_m_pp': np.sqrt(c2),
                              'career_reliability': r2, 'matches_needed_charted': nc2})
            print(f"      min {mb} points per bucket: P={P2}, kept {kept2 / avail2:.0%}, tau_p {np.sqrt(a2):.2f}, "
                  f"tau_m {np.sqrt(c2):.2f}, career reliability {r2:.2f}, matches needed {nc2:,.0f}")
    return pd.DataFrame(rows), pd.DataFrame(sens_rows), pd.DataFrame([vrow])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boot', type=int, default=1000)
    ap.add_argument('--sims', type=int, default=200)
    args = ap.parse_args()
    main_rows, sens_rows, val_rows = [], [], []
    for tour in ('atp', 'wta'):
        m, s, v_ = run_tour(tour, args.boot, args.sims)
        main_rows.append(m)
        sens_rows.append(s)
        val_rows.append(v_)
    pd.concat(val_rows).to_csv(os.path.join(aa.OUT_DIR, 'match_nested_validation.csv'), index=False)
    pd.concat(main_rows).to_csv(os.path.join(aa.OUT_DIR, 'match_nested_variance.csv'), index=False)
    pd.concat(sens_rows).to_csv(os.path.join(aa.OUT_DIR, 'match_nested_sensitivity.csv'), index=False)
    print(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
