"""
confound_adjusted_clutch.py -- the confounder adjustment pre-registered in
docs/combined/confound_adjustment_preregistration.md (written 2026-11-18, before this script was
run).

Two adjusted versions of the paper's quartile clutch score (outcomes S serve-point win, Rt
return-point win, R1 rally-decided point win), compared with the raw score from the same code:

  A  covariate adjustment. z = won - x'b with b estimated by pooled least squares after removing
     each player's cell means (cells = player x leverage bucket: top quartile, middle, bottom
     quartile), so b comes from within-player, within-bucket variation and cannot absorb the
     leverage effect. The score is the paper's quartile difference computed on z.
     Covariates: surface (Clay, Grass), Best-of-5, match date, opponent strength (leave-pair-out,
     shrunk, weight K = 200); sensitivity: + late round + Grand Slam, and K = 50 / 1000.
  B  within-match estimator: each match's top-minus-bottom difference (>= 3 points in each
     bucket), weighted by 1/(1/n_top + 1/n_bottom); removes everything constant within a match.

Reported: split-half reliability (original split, 1,000 random balanced splits, chronological
split), between-player spread (match-clustered two-stage estimator), covariate coefficients,
and the headline entropy-clutch correlations with adjusted scores. Validation first (the script
aborts if any check fails): see the pre-registration, V1 to V6.

Usage: python src/robustness/confound_adjusted_clutch.py [--splits N] [--boot N] [--sim-reps N]
Writes results/applications/confound_adjusted_*.csv and run_log_confound_adjusted.txt (via tee).
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
import slope_chronological as sc
import formulas as f

SEED = 20261119
K_MAIN = 200
TILT, TILT_MULT = 2.0, 3.0      # V6(iii): induced leverage-opponent confound
NMIN_WM = 3                      # points per bucket for a match to enter the within-match estimator
MIN_PTS = asa.MIN_PTS            # 30
MIN_N = 4 * MIN_PTS
OUTS = ['S', 'Rt', 'R1']
COLS = ['clay', 'grass', 'bo5', 'year', 'late', 'slam', 'opp50', 'opp200', 'opp1000']
VARIANTS = {
    'A_core': [0, 1, 2, 3, 7],
    'A_ext': [0, 1, 2, 3, 4, 5, 7],
    'A_K50': [0, 1, 2, 3, 6],
    'A_K1000': [0, 1, 2, 3, 8],
}
VAR_ORDER = list(VARIANTS)
EST_ORDER = ['raw'] + VAR_ORDER + ['B']
SLAMS = {'australian open', 'roland garros', 'wimbledon', 'us open'}
LATE = {'QF', 'SF', 'F'}
REF_FILES = {'atp': 'step3_clutch_features_reconstructed.csv', 'wta': 'wta_clutch_features.csv'}
FROZEN_FILES = {'atp': 'step3_clutch_features.csv', 'wta': 'wta_clutch_features.csv'}
FEATURE_FILES = {'atp': 'step2_full_pool_features.csv', 'wta': 'wta_full_pool_features.csv'}
# the paper's frozen-table entropy-clutch correlations (confound_check_era_surface.py)
PAPER_R = {('atp', 'S'): -0.0413, ('atp', 'Rt'): 0.0164, ('wta', 'S'): -0.259, ('wta', 'Rt'): 0.196}


def log(*a):
    print(*a, flush=True)


def fail(msg):
    raise SystemExit(f"VALIDATION FAILED: {msg}")


# =============================================================================
# context
# =============================================================================

def match_covariates(matches, sorted_ids):
    """Per-match arrays (indexed like sorted_ids): clay, grass, bo5, year (decades, centred), late, slam."""
    meta = matches.drop_duplicates('match_id').set_index('match_id').reindex(sorted_ids)
    if meta['Player 1'].isna().any():
        raise SystemExit("some relevant matches are missing from the match file")
    surf = meta['Surface'].astype(str).str.strip()
    clay = (surf == 'Clay').values.astype(float)
    grass = (surf == 'Grass').values.astype(float)
    n_other = int((~surf.isin(['Hard', 'Clay', 'Grass'])).sum())
    bo5 = (pd.to_numeric(meta['Best of'], errors='coerce') == 5).values.astype(float)
    ids = np.asarray(sorted_ids)
    yr = np.array([int(s[:4]) + (int(s[4:6]) - 1) / 12.0 for s in ids])
    year = (yr - yr.mean()) / 10.0
    late = meta['Round'].astype(str).str.strip().isin(LATE).values.astype(float)
    slam = meta['Tournament'].astype(str).str.strip().str.lower().isin(SLAMS).values.astype(float)
    return np.column_stack([clay, grass, bo5, year, late, slam]), n_other


def opponent_strength(tab, K):
    """Row-level opponent strength for the server's view (the returner's return-win rate) and the
    returner's view (the server's serve-win rate), leave-pair-out and shrunk to the tour mean."""
    sw = tab['server_won_point'].values.astype(float)
    srv, ret = tab['server'].values, tab['returner'].values
    mu_s = sw.mean()
    mu_r = 1 - mu_s
    df = pd.DataFrame({'s': srv, 'r': ret, 'sw': sw})
    s_win, s_n = df.groupby('s')['sw'].sum(), df.groupby('s')['sw'].count()
    r_win, r_n = (1 - df['sw']).groupby(df['r']).sum(), df.groupby('r')['sw'].count()
    pair = df.groupby(['s', 'r'])['sw'].agg(['sum', 'count'])
    key = pd.MultiIndex.from_arrays([srv, ret])
    psum = pair['sum'].reindex(key).values
    pn = pair['count'].reindex(key).values
    rw = r_win.reindex(ret).values - (pn - psum)
    rn = r_n.reindex(ret).values - pn
    sw_ = s_win.reindex(srv).values - psum
    sn = s_n.reindex(srv).values - pn
    opp_for_server = (rw + K * mu_r) / (rn + K) - mu_r      # returner's return strength
    opp_for_returner = (sw_ + K * mu_s) / (sn + K) - mu_s   # server's serve strength
    return opp_for_server, opp_for_returner, (rw, rn, sw_, sn)


def check_opponent_strength(tab, K, opp_s, opp_r, rng, n=200):
    """V4: brute-force recomputation on random rows."""
    sw = tab['server_won_point'].values.astype(float)
    srv, ret = tab['server'].values, tab['returner'].values
    mu_s = sw.mean()
    mu_r = 1 - mu_s
    worst = 0.0
    for i in rng.integers(0, len(tab), n):
        a, b = srv[i], ret[i]
        m_r = (ret == b) & ~(srv == a)         # b's return points, excluding those against a
        v1 = ((1 - sw[m_r]).sum() + K * mu_r) / (m_r.sum() + K) - mu_r
        m_s = (srv == a) & ~(ret == b)         # a's serve points, excluding those against b
        v2 = (sw[m_s].sum() + K * mu_s) / (m_s.sum() + K) - mu_s
        worst = max(worst, abs(v1 - opp_s[i]), abs(v2 - opp_r[i]))
    if worst > 1e-9:
        fail(f"leave-pair-out opponent strength differs from brute force by {worst:.2e}")
    return worst


def player_context(tab, players, common, opps):
    """Per-player context matrix in exactly the row order of asa.player_arrays
    (server rows, then returner rows)."""
    by_s = tab.groupby('server').indices
    by_r = tab.groupby('returner').indices
    empty = np.array([], dtype=int)
    out = {}
    for p in players:
        i_s, i_r = by_s.get(p, empty), by_r.get(p, empty)
        c_s = np.column_stack([common[i_s]] + [opps[K][0][i_s] for K in (50, 200, 1000)])
        c_r = np.column_stack([common[i_r]] + [opps[K][1][i_r] for K in (50, 200, 1000)])
        out[p] = {'C': np.vstack([c_s, c_r]),
                  'won': np.concatenate([tab['server_won_point'].values[i_s],
                                         1 - tab['server_won_point'].values[i_r]])}
    return out


# =============================================================================
# selections, design, estimation of the covariate coefficients
# =============================================================================

def build_P(arrs, ctx, players):
    P = {}
    for p in players:
        d, C = arrs[p], ctx[p]['C']
        base = ~np.isnan(d['lev'])
        for k in OUTS:
            sel = base & d['is_serve'] if k == 'S' else (base & ~d['is_serve'] if k == 'Rt' else base)
            s = {'lev': d['lev'][sel], 'won': d['won'][sel].astype(float), 'gm': d['gm'][sel],
                 'is_serve': d['is_serve'][sel], 'rally': d['rally'][sel], 'C': C[sel], 'idx': np.where(sel)[0]}
            u, inv = np.unique(s['gm'], return_inverse=True)
            s['inv'], s['nm'] = inv, len(u)
            P[(p, k)] = s
    return P


def xmat(C, is_serve, k, cidx):
    Cc = C[:, cidx]
    if k != 'R1':
        return Cc
    sv = is_serve.astype(float)[:, None]
    return np.hstack([sv, Cc * sv, Cc * (1 - sv)])


def xnames(k, cidx):
    nm = [COLS[i] for i in cidx]
    if k != 'R1':
        return nm
    return ['serving'] + [f'{n}:serve_pt' for n in nm] + [f'{n}:return_pt' for n in nm]


def cell_labels(lev, q25, q75):
    return np.where(lev >= q75, 2, np.where(lev <= q25, 0, 1))


def fit_beta(P, players, k, cidx, masks=None, n_m=None, want_se=False):
    """Pooled within-(player x bucket) least squares of won on the context columns.
    masks: optional per-player boolean arrays over the selection rows (e.g. one half)."""
    q = xmat(P[(players[0], k)]['C'][:2], P[(players[0], k)]['is_serve'][:2], k, cidx).shape[1]
    if q == 0:
        return np.zeros(0), None, []
    XtX, Xty = np.zeros((q, q)), np.zeros(q)

    def cells(j, p):
        s = P[(p, k)]
        m = masks[j] if masks is not None else np.ones(len(s['lev']), dtype=bool)
        if m.sum() < MIN_N:
            return None
        q25, q75 = np.quantile(s['lev'][m], [0.25, 0.75])
        est = m & s['rally'] if k == 'R1' else m
        X = xmat(s['C'][est], s['is_serve'][est], k, cidx)
        y = s['won'][est]
        lab = cell_labels(s['lev'][est], q25, q75)
        Xd, yd = np.zeros_like(X), np.zeros_like(y)
        for c in (0, 1, 2):
            r = lab == c
            if r.any():
                Xd[r] = X[r] - X[r].mean(0)
                yd[r] = y[r] - y[r].mean()
        return Xd, yd, s['gm'][est]

    for j, p in enumerate(players):
        r = cells(j, p)
        if r is None:
            continue
        XtX += r[0].T @ r[0]
        Xty += r[0].T @ r[1]
    keep = np.diag(XtX) > 1e-9 * max(np.diag(XtX).max(), 1e-300)
    beta = np.zeros(q)
    beta[keep] = np.linalg.solve(XtX[np.ix_(keep, keep)], Xty[keep])
    names = xnames(k, cidx)
    if not want_se:
        return beta, None, names
    meat_acc = np.zeros((n_m, q))
    for j, p in enumerate(players):
        r = cells(j, p)
        if r is None:
            continue
        Xd, yd, g = r
        sc_ = Xd * (yd - Xd @ beta)[:, None]
        for t in range(q):
            meat_acc[:, t] += np.bincount(g, weights=sc_[:, t], minlength=n_m)
    used = (np.abs(meat_acc).sum(1) > 0).sum()
    meat = meat_acc.T @ meat_acc * used / max(used - 1, 1)
    se = np.full(q, np.nan)
    inv = np.linalg.inv(XtX[np.ix_(keep, keep)])
    cov = inv @ meat[np.ix_(keep, keep)] @ inv
    se[keep] = np.sqrt(np.diag(cov))
    return beta, se, names


def zvalues(s, k, cidx, beta):
    if len(beta) == 0:
        return s['won'].copy()
    return s['won'] - xmat(s['C'], s['is_serve'], k, cidx) @ beta


# =============================================================================
# fast evaluation of one half
# =============================================================================

def lean(s, k, m, zlist):
    """Quartile scores on the rows selected by boolean m: raw, one per z array, and the
    within-match estimator. Mirrors rally_extension.sums + diff_se (checked in V2).
    Returns (raw, [a...], b) with NaN where undefined, or None."""
    if m.sum() < MIN_N:
        return None
    lev = s['lev']
    q25, q75 = np.quantile(lev[m], [0.25, 0.75])
    top, bot = m & (lev >= q75), m & (lev <= q25)
    if k == 'R1':
        top, bot = top & s['rally'], bot & s['rally']
    if top.sum() < MIN_PTS or bot.sum() < MIN_PTS:
        return None
    w = s['won']
    raw = w[top].mean() - w[bot].mean()
    adj = [z[top].mean() - z[bot].mean() for z in zlist]
    inv, nm = s['inv'], s['nm']
    it, ib = inv[top], inv[bot]
    Dt, Db = np.bincount(it, minlength=nm), np.bincount(ib, minlength=nm)
    ok = (Dt >= NMIN_WM) & (Db >= NMIN_WM)
    b = np.nan
    if ok.sum() >= 2 and Dt[ok].sum() >= MIN_PTS and Db[ok].sum() >= MIN_PTS:
        Nt = np.bincount(it, weights=w[top], minlength=nm)
        Nb = np.bincount(ib, weights=w[bot], minlength=nm)
        d = Nt[ok] / Dt[ok] - Nb[ok] / Db[ok]
        wt = 1.0 / (1.0 / Dt[ok] + 1.0 / Db[ok])
        b = float((wt * d).sum() / wt.sum())
    return raw, adj, b


def wm_from_sums(t):
    """Within-match score and match-clustered SE from rally_extension.sums output."""
    g, Nt, Dt, Nb, Db, sign = t
    ok = (Dt >= NMIN_WM) & (Db >= NMIN_WM)
    if ok.sum() < 2 or Dt[ok].sum() < MIN_PTS or Db[ok].sum() < MIN_PTS:
        return np.nan, np.nan
    d = Nt[ok] / Dt[ok] - Nb[ok] / Db[ok]
    wt = 1.0 / (1.0 / Dt[ok] + 1.0 / Db[ok])
    score = (wt * d).sum() / wt.sum()
    e = wt * (d - score) / wt.sum()
    M = ok.sum()
    return float(score), float(np.sqrt(M / (M - 1) * (e ** 2).sum()))


# =============================================================================
# validation
# =============================================================================

def validate_v1(tour, players, arrs, orig_assign, allsh):
    ia = [orig_assign[arrs[p]['gm']] for p in players]
    for k in OUTS:
        da, _, db, _ = rx.half_stats(arrs, players, k, ia)
        r = rx.rel_from(da, db)
        ref = allsh.loc[rx.ALLSHOT_KEY[k], 'original_split']
        log(f"V1 {k}: raw original-split {r:+.4f} reference {ref:+.4f}")
        if abs(r - ref) > 0.001:
            fail(f"{tour.upper()} V1 original-split reliability of {k}")
    ref = pd.read_csv(os.path.join(asa.REPO_ROOT, 'results', tour, REF_FILES[tour])).set_index('player')
    worst = 0.0
    for p in players:
        full = np.ones(len(arrs[p]['lev']), dtype=bool)
        for k, col in (('S', 'serve_clutch_p65'), ('Rt', 'return_clutch_p65')):
            d, _ = rx.diff_se(rx.sums(arrs[p], full, k))
            worst = max(worst, abs(d - ref.loc[p, col]))
    log(f"V1 full-sample serve/return clutch vs committed table: max abs diff {worst:.2e}")
    if worst > 1e-9:
        fail(f"{tour.upper()} V1 full-sample clutch differs from {REF_FILES[tour]}")


def validate_v2(P, arrs, ctx, players, betas, n_m, rng, n_checks=60):
    worst = 0.0
    for _ in range(n_checks):
        p = players[rng.integers(len(players))]
        k = OUTS[rng.integers(3)]
        s, d = P[(p, k)], arrs[p]
        cidx = VARIANTS['A_core']
        z = zvalues(s, k, cidx, betas[(k, 'A_core')])
        zfull = d['won'].astype(float) - xmat(ctx[p]['C'], d['is_serve'], k, cidx) @ betas[(k, 'A_core')]
        ad = dict(d)
        ad['won'] = zfull
        in_a = np.zeros(n_m, dtype=bool)
        in_a[rng.permutation(n_m)[0::2]] = True
        for half in (True, False):
            mrows = in_a[d['gm']] if half else ~in_a[d['gm']]
            r = lean(s, k, in_a[s['gm']] if half else ~in_a[s['gm']], [z])
            t_raw, t_adj = rx.sums(d, mrows, k), rx.sums(ad, mrows, k)
            if r is None or t_raw is None:
                if (r is None) != (t_raw is None):
                    fail("V2 availability differs between lean and rally_extension.sums")
                continue
            worst = max(worst, abs(r[0] - rx.diff_se(t_raw)[0]), abs(r[1][0] - rx.diff_se(t_adj)[0]))
            b_ref = wm_from_sums(t_raw)[0]
            if np.isnan(r[2]) != np.isnan(b_ref):
                fail("V2 within-match availability differs")
            if not np.isnan(b_ref):
                worst = max(worst, abs(r[2] - b_ref))
    log(f"V2 lean routine vs rally_extension.sums (raw, adjusted, within-match): max abs diff {worst:.2e}")
    if worst > 1e-9:
        fail("V2 lean routine does not reproduce rally_extension.sums")


def validate_v3(arrs, ctx, players):
    for p in players:
        if len(arrs[p]['won']) != len(ctx[p]['won']) or not np.array_equal(arrs[p]['won'], ctx[p]['won']):
            fail(f"V3 context rows are not aligned with the player arrays ({p})")
    log("V3 context rows align with the player arrays for every player")


def validate_v5(P, players):
    worst = 0.0
    for p in players[:20]:
        for k in OUTS:
            s = P[(p, k)]
            m = np.ones(len(s['lev']), dtype=bool)
            r = lean(s, k, m, [zvalues(s, k, [], np.zeros(0))])
            if r is not None:
                worst = max(worst, abs(r[0] - r[1][0]))
    log(f"V5 adjusted score with no covariates equals raw: max abs diff {worst:.2e}")
    if worst > 1e-12:
        fail("V5 adjusted score with no covariates differs from raw")


def full_scores(P, players, k, cidx, beta):
    """Full-sample raw / adjusted / within-match scores on every player (lean, all rows)."""
    out = np.full((3, len(players)), np.nan)
    for j, p in enumerate(players):
        s = P[(p, k)]
        r = lean(s, k, np.ones(len(s['lev']), dtype=bool), [zvalues(s, k, cidx, beta)])
        if r is not None:
            out[:, j] = [r[0], r[1][0], r[2]]
    return out


def simulate_checks(tour, P, players, betas_real, rng, n_reps, n_m):
    """V6: simulation with known truth on the real design (S, Rt and R1).

    Scenarios (i)-(iii) are paired: the same uniform draws generate outcomes WITH the covariate
    effects and WITHOUT them (the oracle, true clutch 0). Each estimator is applied to both and the
    per-player difference isolates its bias from sampling noise. An unbiased adjustment must give a
    mean difference within 3 SE of zero; the raw score's difference is the confound it fails to remove."""
    rows = []
    cidx = VARIANTS['A_core']
    names = ['raw', 'A_core', 'B']
    scenarios = [('covariate effect x1', 1.0, 0.0), ('covariate effect x3', 3.0, 0.0),
                 (f'leverage tilted toward strong opponents (effect x{TILT_MULT:g}, tilt {TILT:g})', TILT_MULT, TILT)]
    for label, mult, tilt in scenarios:
        for k in OUTS:
            sc_c, sc_0, _ = full_scores_sim(P, players, k, cidx, betas_real[k], rng, mult, 0.0, tilt, True)
            stats_ = {}
            for e, name in enumerate(names):
                ok = ~np.isnan(sc_c[e]) & ~np.isnan(sc_0[e])
                d = sc_c[e][ok] - sc_0[e][ok]
                m, se = d.mean(), d.std(ddof=1) / np.sqrt(len(d))
                stats_[name] = (m, se)
                rows.append({'tour': tour, 'check': label, 'outcome': k, 'estimator': name,
                             'mean_pp': 100 * m, 'se_mean_pp': 100 * se, 'slope': np.nan,
                             'pass': (abs(m) <= 3 * se) if name != 'raw' else None})
                log(f"V6 {tour.upper()} {label} {k} {name}: bias vs oracle {100 * m:+.3f} pp (SE {100 * se:.3f})")
                if name != 'raw' and abs(m) > 3 * se:
                    fail(f"V6 {tour.upper()} {k} {name}: bias {100 * m:+.3f} pp is not within 3 SE of zero ({label})")
            if tilt > 0 and abs(stats_['raw'][0]) <= 3 * stats_['raw'][1]:
                fail(f"V6 {tour.upper()} {k}: the induced confound did not bias the raw score, so the test is uninformative")
    for k in OUTS:
        sl = {n: [] for n in names}
        for _ in range(n_reps):
            sc_c, _, delta = full_scores_sim(P, players, k, cidx, betas_real[k], rng, 1.0, 0.04, 0.0, False)
            for e, name in enumerate(names):
                ok = ~np.isnan(sc_c[e])
                sl[name].append(np.polyfit(delta[ok], sc_c[e][ok], 1)[0])
        for name in sl:
            m = float(np.mean(sl[name]))
            rows.append({'tour': tour, 'check': 'planted clutch N(0, 4 pp)', 'outcome': k, 'estimator': name,
                         'mean_pp': np.nan, 'se_mean_pp': np.nan, 'slope': m,
                         'pass': (0.85 <= m <= 1.15) if name != 'raw' else None})
            log(f"V6 {tour.upper()} planted clutch {k} {name}: mean slope on truth {m:.3f}")
            if name != 'raw' and not (0.85 <= m <= 1.15):
                fail(f"V6 {tour.upper()} {k} {name}: slope {m:.3f} outside [0.85, 1.15]")
    return pd.DataFrame(rows)


def full_scores_sim(P, players, k, cidx, beta_real, rng, mult, planted_sd, tilt=0.0, oracle=False):
    """Redraw outcomes, refit the coefficients on the simulated data, score every player.
    tilt > 0 re-defines leverage as z(leverage) + tilt * z(opponent strength) within each player,
    so top-leverage points come disproportionately from strong opponents (a built-in, match-level confound).
    oracle=True also returns the scores for outcomes drawn from the same uniforms with the
    covariate effects removed. Returns (scores, oracle scores or None, planted effects)."""
    Pc, P0 = {}, {}
    delta = np.zeros(len(players))
    for j, p in enumerate(players):
        s = P[(p, k)]
        xb = xmat(s['C'], s['is_serve'], k, cidx) @ beta_real * mult
        d = rng.normal(0, planted_sd) if planted_sd > 0 else 0.0
        s2 = dict(s)
        if tilt > 0:
            # opponent strength averaged within each match, so the induced confound is a
            # match-level one (the kind both adjustments are meant to handle)
            opp = s['C'][:, COLS.index('opp200')]
            opp = (np.bincount(s['inv'], weights=opp) / np.bincount(s['inv']))[s['inv']]
            zl = (s['lev'] - s['lev'].mean()) / s['lev'].std()
            s2['lev'] = zl + tilt * (opp - opp.mean()) / opp.std()
        top = s2['lev'] >= np.quantile(s2['lev'], 0.75)
        if k == 'R1':
            top = top & s['rally']
        a = s['won'].mean()
        u = rng.random(len(xb))
        s3 = dict(s2)
        s2['won'] = (u < np.clip(a + (xb - xb.mean()) + d * top, 0.02, 0.98)).astype(float)
        s3['won'] = (u < np.clip(a + d * top, 0.02, 0.98)).astype(float)
        Pc[(p, k)], P0[(p, k)] = s2, s3
        delta[j] = d
    out = []
    for Pset in (Pc, P0) if oracle else (Pc,):
        beta, _, _ = fit_beta(Pset, players, k, cidx)
        out.append(full_scores(Pset, players, k, cidx, beta))
    return out[0], (out[1] if oracle else None), delta


# =============================================================================
# main per-tour analysis
# =============================================================================

def run_tour(tour, n_splits, n_boot, n_sim):
    t0 = time.time()
    log(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
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
    rng = np.random.default_rng(SEED)

    mc, n_other = match_covariates(matches, sorted_ids)
    log(f"matches {n_m}; with an unrecognised surface {n_other}; Best-of-5 {int(mc[:, 2].sum())}; "
        f"Grand Slam {int(mc[:, 5].sum())}; late round {int(mc[:, 4].sum())}")
    common = mc[gm]
    opps = {}
    for K in (50, 200, 1000):
        o_s, o_r, _ = opponent_strength(tab, K)
        opps[K] = (o_s, o_r)
    w = check_opponent_strength(tab, 200, opps[200][0], opps[200][1], rng)
    log(f"V4 leave-pair-out opponent strength vs brute force (200 rows): max abs diff {w:.2e}")
    ctx = player_context(tab, players, common, opps)
    validate_v3(arrs, ctx, players)
    validate_v1(tour, players, arrs, orig_assign, allsh)
    P = build_P(arrs, ctx, players)
    validate_v5(P, players)

    # ---- coefficients (full sample, with match-clustered SEs) ----
    betas, coef_rows = {}, []
    for vname, cidx in VARIANTS.items():
        for k in OUTS:
            want = vname in ('A_core', 'A_ext')
            b, se, names = fit_beta(P, players, k, cidx, n_m=n_m, want_se=want)
            betas[(k, vname)] = b
            if want:
                for i, nme in enumerate(names):
                    coef_rows.append({'tour': tour, 'variant': vname, 'outcome': k, 'covariate': nme,
                                      'coef_pp': 100 * b[i], 'se_pp': 100 * se[i] if se is not None else np.nan,
                                      't': b[i] / se[i] if (se is not None and se[i] > 0) else np.nan})
    for r in coef_rows:
        if r['variant'] == 'A_core' and r['outcome'] in ('S', 'Rt'):
            log(f"coef {r['outcome']:>2s} {r['covariate']:<8s} {r['coef_pp']:+8.2f} pp (SE {r['se_pp']:.2f}, t {r['t']:+.1f})")
    rngv = np.random.default_rng(SEED + 1)
    validate_v2(P, arrs, ctx, players, betas, n_m, rngv)

    # ---- V6 simulation ----
    sim_df = simulate_checks(tour, P, players, {k: betas[(k, 'A_core')] for k in OUTS}, np.random.default_rng(SEED + 2),
                             n_sim, n_m)

    # ---- z arrays for every variant ----
    Z = {}
    for j, p in enumerate(players):
        for k in OUTS:
            s = P[(p, k)]
            Z[(j, k)] = [zvalues(s, k, VARIANTS[v], betas[(k, v)]) for v in VAR_ORDER]

    def eval_split(row_mask_fun, with_halfbeta=None):
        """Per-estimator half values {k: array(n_est, n_players) for halves a and b}."""
        out = {}
        for k in OUTS:
            da = np.full((len(EST_ORDER), len(players)), np.nan)
            db = da.copy()
            for j, p in enumerate(players):
                s = P[(p, k)]
                m = row_mask_fun(j, p, s)
                for arr, mm in ((da, m), (db, ~m)):
                    r = lean(s, k, mm, Z[(j, k)])
                    if r is not None:
                        arr[0, j] = r[0]
                        arr[1:1 + len(VAR_ORDER), j] = r[1]
                        arr[-1, j] = r[2]
            out[k] = (da, db)
        return out

    # ---- original split (and the half-specific-coefficient leakage check) ----
    o = eval_split(lambda j, p, s: orig_assign[s['gm']])
    rel_rows = []
    rand = {(k, e): [] for k in OUTS for e in EST_ORDER}
    hb = {}
    for k in OUTS:
        ma = [orig_assign[P[(p, k)]['gm']] for p in players]
        ba, _, _ = fit_beta(P, players, k, VARIANTS['A_core'], masks=ma)
        bb, _, _ = fit_beta(P, players, k, VARIANTS['A_core'], masks=[~m for m in ma])
        zs = []
        for j, p in enumerate(players):
            s = P[(p, k)]
            X = xmat(s['C'], s['is_serve'], k, VARIANTS['A_core'])
            zs.append(s['won'] - np.where(ma[j], X @ ba, X @ bb))
        da = np.full(len(players), np.nan)
        db = da.copy()
        for j, p in enumerate(players):
            s = P[(p, k)]
            ra, rb = lean(s, k, ma[j], [zs[j]]), lean(s, k, ~ma[j], [zs[j]])
            if ra is not None:
                da[j] = ra[1][0]
            if rb is not None:
                db[j] = rb[1][0]
        hb[k] = rx.rel_from(da, db)

    # ---- 1,000 random balanced splits, identical for every estimator ----
    log(f"\n{n_splits} random splits ...")
    for s_ in range(n_splits):
        order = rng.permutation(n_m)
        in_a = np.zeros(n_m, dtype=bool)
        in_a[order[0::2]] = True
        res = eval_split(lambda j, p, s, a=in_a: a[s['gm']])
        for k in OUTS:
            da, db = res[k]
            for e, name in enumerate(EST_ORDER):
                rand[(k, name)].append(rx.rel_from(da[e], db[e]))
        if (s_ + 1) % 100 == 0:
            log(f"  {s_ + 1} splits ({time.time() - t0:.0f}s)")
    for k in OUTS:
        da, db = o[k]
        for e, name in enumerate(EST_ORDER):
            v = np.array([x for x in rand[(k, name)] if not np.isnan(x)])
            row = {'tour': tour, 'outcome': k, 'estimator': name, 'original_split': rx.rel_from(da[e], db[e]),
                   'n_players': int((~np.isnan(da[e]) & ~np.isnan(db[e])).sum()), 'median': float(np.median(v)),
                   'p2_5': float(np.percentile(v, 2.5)), 'p97_5': float(np.percentile(v, 97.5)),
                   'share_at_or_above_070': float((v >= 0.70).mean()),
                   'orig_split_halfspecific_coef': hb[k] if name == 'A_core' else np.nan}
            rel_rows.append(row)
            log(f"[{k:>2s} {name:<8s}] orig {row['original_split']:+.3f} median {row['median']:+.3f} "
                f"[{row['p2_5']:+.2f}, {row['p97_5']:+.2f}] share>=0.70 {row['share_at_or_above_070']:.1%} n={row['n_players']}"
                + (f" (half-specific coef {hb[k]:+.3f})" if name == 'A_core' else ''))

    # ---- chronological split ----
    chron_rows = []
    first = {}
    for p in players:
        u = np.unique(arrs[p]['gm'])
        first[p] = set(u[:int(np.ceil(len(u) / 2))].tolist())
    res = eval_split(lambda j, p, s: np.isin(s['gm'], list(first[p])))
    for k in OUTS:
        da, db = res[k]
        for e, name in enumerate(EST_ORDER):
            r, sb, n = sc.rel_pair(da[e], db[e])
            (rlo, rhi), (slo, shi) = sc.boot_r(da[e], db[e], rng, n_boot)
            chron_rows.append({'tour': tour, 'outcome': k, 'estimator': name, 'n_players': n, 'early_late_r': r,
                               'r_lo': rlo, 'r_hi': rhi, 'chronological_spearman_brown': sb, 'sb_lo': slo, 'sb_hi': shi})
            log(f"[chronological {k:>2s} {name:<8s}] n={n} r {r:+.3f} [{rlo:+.2f}, {rhi:+.2f}]  SB {sb:+.3f} [{slo:+.2f}, {shi:+.2f}]")

    # ---- spread: full sample, match-clustered two-stage estimator ----
    spread_rows = []
    ones = {p: np.ones(len(arrs[p]['lev']), dtype=bool) for p in players}
    full = {}
    for k in OUTS:
        sc_ = {e: np.full(len(players), np.nan) for e in EST_ORDER}
        se_ = {e: np.full(len(players), np.nan) for e in EST_ORDER}
        for j, p in enumerate(players):
            t = rx.sums(arrs[p], ones[p], k)
            if t is None:
                continue
            sc_['raw'][j], se_['raw'][j] = rx.diff_se(t)
            sc_['B'][j], se_['B'][j] = wm_from_sums(t)
            for v in VAR_ORDER:
                d = P[(p, k)]
                ad = dict(arrs[p])
                ad['won'] = arrs[p]['won'].astype(float) - xmat(ctx[p]['C'], arrs[p]['is_serve'], k, VARIANTS[v]) @ betas[(k, v)] \
                    if len(betas[(k, v)]) else arrs[p]['won'].astype(float)
                sc_[v][j], se_[v][j] = rx.diff_se(rx.sums(ad, ones[p], k))
        full[k] = sc_
        ok = np.all([~np.isnan(sc_[e]) & ~np.isnan(se_[e]) for e in EST_ORDER], axis=0)
        n = int(ok.sum())
        for e in EST_ORDER:
            s_e, se_e = sc_[e][ok], se_[e][ok]
            tau, v = rx.tau_moment(s_e, se_e)
            ms2 = float(np.mean(se_e ** 2))
            bt, br = np.zeros(n_boot), np.zeros(n_boot)
            for b in range(n_boot):
                idx = rng.integers(0, n, n)
                t_, vv = rx.tau_moment(s_e[idx], se_e[idx])
                bt[b], br[b] = t_, vv / (vv + np.mean(se_e[idx] ** 2))
            lo, hi = np.percentile(bt, [2.5, 97.5])
            rlo, rhi = np.percentile(br, [2.5, 97.5])
            spread_rows.append({'tour': tour, 'outcome': k, 'estimator': e, 'n_players': n,
                                'sd_of_scores_pp': 100 * np.std(s_e, ddof=1), 'true_sd_pp': 100 * tau,
                                'true_sd_lo': 100 * lo, 'true_sd_hi': 100 * hi, 'noise_se_pp': 100 * np.sqrt(ms2),
                                'implied_reliability': v / (v + ms2), 'implied_rel_lo': rlo, 'implied_rel_hi': rhi,
                                'corr_with_raw': float(np.corrcoef(s_e, sc_['raw'][ok])[0, 1]),
                                'mean_shift_vs_raw_pp': 100 * float(np.mean(s_e - sc_['raw'][ok]))})
            log(f"[spread {k:>2s} {e:<8s}] n={n} SD {100 * np.std(s_e, ddof=1):.2f} pp, true SD {100 * tau:.2f} "
                f"[{100 * lo:.2f}, {100 * hi:.2f}], noise SE {100 * np.sqrt(ms2):.2f}, implied rel {v / (v + ms2):.2f}; "
                f"corr with raw {spread_rows[-1]['corr_with_raw']:.2f}, mean shift {spread_rows[-1]['mean_shift_vs_raw_pp']:+.2f} pp")

    # ---- entropy-clutch correlations ----
    ent_rows = []
    feats = pd.read_csv(os.path.join(asa.REPO_ROOT, 'results', tour, FEATURE_FILES[tour])).set_index('player')
    refc = pd.read_csv(os.path.join(asa.REPO_ROOT, 'results', tour, REF_FILES[tour])).set_index('player')
    frozen = pd.read_csv(os.path.join(asa.REPO_ROOT, 'results', tour, FROZEN_FILES[tour])).set_index('player')
    for k, col, flag in (('S', 'serve_clutch_p65', 'serve_clutch_p65_sufficient'),
                         ('Rt', 'return_clutch_p65', 'return_clutch_p65_sufficient')):
        suff = np.array([bool(feats.loc[p, 'transition_entropy_sufficient']) and bool(refc.loc[p, flag])
                         for p in players])
        ent = np.array([feats.loc[p, 'conditional_normalized_entropy'] for p in players])
        fz = np.array([frozen.loc[p, col] for p in players])
        fr_r = stats.pearsonr(ent[suff], fz[suff])
        if abs(fr_r[0] - PAPER_R[(tour, k)]) > 0.0006:
            log(f"WARNING: frozen-table r {fr_r[0]:+.4f} differs from the paper's {PAPER_R[(tour, k)]:+.4f}")
        for e in ['raw', 'A_core', 'A_ext', 'B']:
            x = full[k][e]
            ok = suff & ~np.isnan(x)
            r, pv = stats.pearsonr(ent[ok], x[ok])
            ent_rows.append({'tour': tour, 'outcome': k, 'estimator': e, 'n': int(ok.sum()), 'r': r, 'p': pv,
                             'frozen_table_r': fr_r[0], 'frozen_table_p': fr_r[1]})
            log(f"[entropy {k:>2s} {e:<7s}] n={int(ok.sum())} r {r:+.4f} p {pv:.4f}   (frozen table r {fr_r[0]:+.4f} p {fr_r[1]:.4f})")
    log(f"{tour.upper()} done in {time.time() - t0:.0f}s")
    return (pd.DataFrame(rel_rows), pd.DataFrame(spread_rows), pd.DataFrame(chron_rows),
            pd.DataFrame(ent_rows), pd.DataFrame(coef_rows), sim_df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=1000)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--sim-reps', type=int, default=5)
    ap.add_argument('--tours', default='atp,wta')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    names = ['reliability', 'spread', 'chronological', 'entropy', 'coefficients', 'simulation']
    outs = [[] for _ in names]
    for tour in args.tours.split(','):
        for lst, df in zip(outs, run_tour(tour, args.splits, args.boot, args.sim_reps)):
            lst.append(df)
    for name, lst in zip(names, outs):
        pd.concat(lst).to_csv(os.path.join(aa.OUT_DIR, f'confound_adjusted_{name}{args.tag}.csv'), index=False)
    log(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
