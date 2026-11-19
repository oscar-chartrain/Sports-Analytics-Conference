"""External criterion: does clutch predict winning when it matters?

Plan: docs/combined/decider_validity_preregistration.md (written before this script was run).
Predictors: the paper's full-sample clutch scores (charted matches). Criteria: deciding-set matches (C1) and
tiebreak sets (C2) in tour-level matches that are NOT charted, against an Elo strength expectation built
from sets that are neither deciding sets nor tiebreak sets.

    python src/robustness/fetch_tour_results.py          # once
    python src/robustness/decider_validity.py [--tours atp wta] [--validate-only] [--sims 1000] [--boot 2000]
"""
import os
import re
import sys
import argparse
import time
import unicodedata
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats, optimize

import applications_analyses as aa
import all_shots_analyses as asa
import formulas as f
import split_half_reliability as shr

SEED = 20261123
K_MAIN = 20.0
K_SENS = (10.0, 30.0)
FLOOR = 30
ALPHA_PRIMARY = 0.05 / 4
ALPHA_SECONDARY = 0.05 / 28
SEVEN = ['serve_clutch', 'return_clutch', 'R1_rally_point', 'R2_error_all', 'R3_winner_all',
         'R4_error_forehand', 'R5_error_backhand']
SD_TRUE_S = {'atp': 2.107, 'wta': 1.845}      # true SD of serve clutch, pp (Table S6 / Table 2 style estimate)
OUT_DIR = aa.OUT_DIR
TOUR_DIR = os.path.join(aa.REPO_ROOT, 'results', 'tour_results')
SCALE = np.log(10) / 400.0


def log(*a):
    print(*a, flush=True)


def fail(msg):
    raise SystemExit(f"VALIDATION FAILED: {msg}")


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().replace('-', ' ')
    return ' '.join(re.sub(r'[^a-z ]', '', s).split())


BAD = ('RET', 'W/O', 'DEF', 'WO', 'ABD', 'UNK', 'NOSHOW', 'UNFINISHED')
TOK = re.compile(r'^(\d+)-(\d+)(?:\((\d+)\))?$')


def parse_score(score):
    """List of (winner games, loser games, has_tiebreak_marker) or None if not a complete, parseable score."""
    if not isinstance(score, str):
        return None
    s = score.strip()
    if any(k in s.upper() for k in BAD) or not s:
        return None
    out = []
    for tok in s.split():
        m = TOK.match(tok)
        if not m:
            return None
        out.append((int(m.group(1)), int(m.group(2)), m.group(3) is not None))
    return out


def valid_set(wg, lg):
    hi, lo = max(wg, lg), min(wg, lg)
    return (hi == 6 and lo <= 4) or (hi == 7 and lo in (5, 6)) or (hi >= 8 and hi - lo == 2)


def load_results(tour):
    fs = sorted(x for x in os.listdir(TOUR_DIR) if x.startswith(f'{tour}_matches_') and x.endswith('.csv'))
    df = pd.concat([pd.read_csv(os.path.join(TOUR_DIR, x), low_memory=False) for x in fs], ignore_index=True)
    df = df.dropna(subset=['winner_id', 'loser_id', 'tourney_date']).copy()
    df['match_num'] = pd.to_numeric(df['match_num'], errors='coerce').fillna(0)
    df = df.sort_values(['tourney_date', 'match_num'], kind='mergesort').reset_index(drop=True)
    df['wn'] = df['winner_name'].map(norm)
    df['ln'] = df['loser_name'].map(norm)
    df['date'] = pd.to_datetime(df['tourney_date'].astype(int).astype(str), format='%Y%m%d')
    return df


def process_matches(df):
    """Per-match set lists and flags: complete, decider, tiebreak sets."""
    sets_col, complete, decider, anomalies = [], [], [], 0
    for sc_, bo in zip(df['score'].values, df['best_of'].values):
        s = parse_score(sc_)
        ok = s is not None and len(s) >= 2 and bo in (3, 5)
        if ok:
            ok = all(valid_set(w, l) for w, l, _ in s)
            if not ok:
                anomalies += 1
        sets_col.append(s if ok else None)
        complete.append(ok)
        decider.append(ok and len(s) == bo)
    return sets_col, np.array(complete), np.array(decider), anomalies


def elo_run(df, sets_col, decider, K):
    """Pre-match ratings for winner and loser, from sets that are neither deciding sets nor tiebreak sets."""
    R = {}
    n = len(df)
    rw, rl = np.full(n, 1500.0), np.full(n, 1500.0)
    used_dec, used_tb = 0, 0
    wid, lid = df['winner_id'].values, df['loser_id'].values
    for i in range(n):
        a, b = wid[i], lid[i]
        ra, rb = R.get(a, 1500.0), R.get(b, 1500.0)
        rw[i], rl[i] = ra, rb
        s = sets_col[i]
        if s is None:
            continue
        for j, (wg, lg, tbm) in enumerate(s):
            is_tb = tbm or (wg, lg) in ((7, 6), (6, 7))
            is_last_dec = decider[i] and j == len(s) - 1
            if is_tb or is_last_dec:
                continue
            e_a = 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))
            if wg > lg:
                da = K * (1 - e_a)
            else:
                da = -K * e_a
            ra += da
            rb -= da
        R[a], R[b] = ra, rb
    return rw, rl, R


# ----------------------------------------------------------------------------
# criteria
# ----------------------------------------------------------------------------

def fit_b(d):
    """MLE of b in P = sigma(b d) over oriented differences d (winner minus loser)."""
    def nll(b):
        return np.sum(np.logaddexp(0, -b * d))
    r = optimize.minimize_scalar(nll, bounds=(0.01, 5), method='bounded')
    return float(r.x)


def sigma(x):
    return 1.0 / (1.0 + np.exp(-x))


def build_events(df, sets_col, decider, rw, rl):
    """Event tables. C1: one row per deciding-set match (winner perspective). C2: one row per tiebreak set."""
    idx = np.where(decider)[0]
    c1 = pd.DataFrame({'i': idx, 'wid': df['winner_id'].values[idx], 'lid': df['loser_id'].values[idx],
                       'd': (rw[idx] - rl[idx]) * SCALE, 'bo': df['best_of'].values[idx], 'date': df['date'].values[idx]})
    rows = []
    for i, s in enumerate(sets_col):
        if s is None:
            continue
        for wg, lg, tbm in s:
            if tbm or (wg, lg) in ((7, 6), (6, 7)):
                rows.append((i, wg > lg))
    t = pd.DataFrame(rows, columns=['i', 'w_won_set'])
    wid, lid = df['winner_id'].values, df['loser_id'].values
    ii = t['i'].values
    wws = t['w_won_set'].values
    t['sw'] = np.where(wws, wid[ii], lid[ii])
    t['sl'] = np.where(wws, lid[ii], wid[ii])
    t['d'] = np.where(wws, rw[ii] - rl[ii], rl[ii] - rw[ii]) * SCALE
    t['date'] = df['date'].values[ii]
    return c1, t


def crit_arrays(ev, wcol, lcol, bvals, pid):
    """(y - expected) and strength advantage d for the events involving player pid (winner or loser column)."""
    m_w = ev[wcol].values == pid
    m_l = ev[lcol].values == pid
    d = np.concatenate([ev['d'].values[m_w], -ev['d'].values[m_l]])
    b = np.concatenate([bvals[m_w], bvals[m_l]])
    y = np.concatenate([np.ones(m_w.sum()), np.zeros(m_l.sum())])
    return y - sigma(b * d), d, sigma(b * d)


# ----------------------------------------------------------------------------
# estimation
# ----------------------------------------------------------------------------

def wls_hc3(y, X, w):
    W = np.diag(w)
    XtWX = X.T @ W @ X
    inv = np.linalg.inv(XtWX)
    beta = inv @ X.T @ (w * y)
    e = y - X @ beta
    h = w * np.einsum('ij,jk,ik->i', X, inv, X)
    meat = X.T @ np.diag(w * w * e * e / (1 - h) ** 2) @ X
    V = inv @ meat @ inv
    return beta, np.sqrt(np.diag(V)), e


def test_predictor(z, excess, n, abar, rng, n_boot, want_boot=True):
    ok = ~np.isnan(z) & ~np.isnan(excess)
    z, ex, nn, ab = z[ok], excess[ok], n[ok].astype(float), abar[ok]
    X = np.column_stack([np.ones(len(z)), z, ab])
    beta, se, _ = wls_hc3(ex, X, nn)
    t = beta[1] / se[1]
    p = 2 * (1 - stats.t.cdf(abs(t), len(z) - 3))
    rho, prho = stats.spearmanr(z, ex)
    lo = hi = np.nan
    if want_boot:
        bs = []
        for _ in range(n_boot):
            ii = rng.integers(0, len(z), len(z))
            try:
                b_, _, _ = wls_hc3(ex[ii], X[ii], nn[ii])
                bs.append(b_[1])
            except np.linalg.LinAlgError:
                continue
        lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(n_players=int(len(z)), slope_pp=100 * beta[1], se_pp=100 * se[1], p=float(p), boot_lo_pp=100 * lo,
                boot_hi_pp=100 * hi, spearman=float(rho), spearman_p=float(prho), strength_coef=beta[2])


def criterion_reliability(res_list, rng, n_splits=1000):
    """Split-half reliability of player excess: res_list is a list of arrays of (y - expected) per player."""
    vals = []
    for _ in range(n_splits):
        a, b = [], []
        for r in res_list:
            perm = rng.permutation(len(r))
            h = len(r) // 2
            a.append(r[perm[:h]].mean())
            b.append(r[perm[h:2 * h]].mean())
        a, b = np.array(a), np.array(b)
        if np.std(a) < 1e-12 or np.std(b) < 1e-12:
            continue
        vals.append(f.spearman_brown(np.corrcoef(a, b)[0, 1]))
    v = np.array(vals)
    return float(np.median(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


# ----------------------------------------------------------------------------
# benchmark: asymmetric set model
# ----------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _hold(p):
    q = 1 - p
    return p ** 4 * (1 + 4 * q + 10 * q * q) + 20 * p ** 3 * q ** 3 * p * p / (p * p + q * q)


def _tiebreak(pa, pb, a_serves_first):
    """P(A wins a 7-point tiebreak); pa = A's win prob on own serve, pb = B's on own serve."""
    @lru_cache(maxsize=None)
    def go(x, y):
        if x >= 7 and x - y >= 2:
            return 1.0
        if y >= 7 and y - x >= 2:
            return 0.0
        m = x + y
        # server of point m (0-indexed): 0 -> first server; then pairs
        pair = (m + 1) // 2
        first = a_serves_first
        a_serves = first if pair % 2 == 0 else (not first)
        pw = pa if a_serves else 1 - pb
        if x == y and x >= 6:
            # one point each served in the next two: closed form
            pa_ = pa
            pbr = 1 - pb
            win2 = pa_ * pbr
            lose2 = (1 - pa_) * pb
            return win2 / (win2 + lose2)
        return pw * go(x + 1, y) + (1 - pw) * go(x, y + 1)
    return go(0, 0)


def set_win_prob(pa, pb):
    """P(A wins a set with a tiebreak at 6-6); A and B serve with win probabilities pa, pb; starting server averaged."""
    out = []
    for a_first in (True, False):
        ha, hb = _hold(pa), _hold(pb)
        tb = _tiebreak(pa, pb, a_first)

        @lru_cache(maxsize=None)
        def go(x, y, a_serves):
            if x >= 6 and x - y >= 2:
                return 1.0
            if y >= 6 and y - x >= 2:
                return 0.0
            if x == 6 and y == 6:
                return tb
            pw = ha if a_serves else 1 - hb
            return pw * go(x + 1, y, not a_serves) + (1 - pw) * go(x, y + 1, not a_serves)
        out.append(go(0, 0, a_first))
    return float(np.mean(out))


def sensitivity_k(p0=0.65, h=0.005):
    up = set_win_prob(p0 + h, p0 - h)
    dn = set_win_prob(p0 - h, p0 + h)
    return (up - dn) / (2 * h)          # change in P(win set) per unit change in point-win prob (both roles)


# ----------------------------------------------------------------------------
# predictors from charted matches
# ----------------------------------------------------------------------------

def get_predictors(tour):
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    arrs = asa.player_arrays(tab, players, gm)
    full = {k: np.full(len(players), np.nan) for k in SEVEN}
    for j, p in enumerate(players):
        res = asa.evaluate(arrs[p], np.ones(len(arrs[p]['lev']), dtype=bool))
        for k in SEVEN:
            full[k][j] = res[k]
    early = []
    for p in players:
        uniq = np.unique(arrs[p]['gm'])
        first = uniq[:int(np.ceil(len(uniq) / 2))]
        early.append(np.isin(arrs[p]['gm'], first))
    va, vb = asa.half_values(arrs, players, early)
    idx = {k: asa.OUTCOMES.index(k) for k in SEVEN}
    rel = {}
    for k in SEVEN:
        a, b = va[:, idx[k]], vb[:, idx[k]]
        ok = ~np.isnan(a) & ~np.isnan(b)
        rel[k] = f.spearman_brown(np.corrcoef(a[ok], b[ok])[0, 1])
    zs = lambda x: (x - np.nanmean(x)) / np.nanstd(x, ddof=1)
    Z = {k: zs(full[k]) for k in SEVEN}

    def composite(Zd):
        M = np.column_stack([Zd[k] for k in SEVEN])
        cnt = (~np.isnan(M)).sum(1)
        c = np.nanmean(np.where(cnt[:, None] >= 5, M, np.nan), axis=1)
        return zs(c)
    Z['composite'] = composite(Z)
    # composite reliability: early-late correlation of the composite built from half-sample z-scores
    ZE = {k: zs(va[:, idx[k]]) for k in SEVEN}
    ZL = {k: zs(vb[:, idx[k]]) for k in SEVEN}
    ce, cl = composite(ZE), composite(ZL)
    ok = ~np.isnan(ce) & ~np.isnan(cl)
    rel['composite'] = f.spearman_brown(np.corrcoef(ce[ok], cl[ok])[0, 1])
    return players, matches, pts, Z, rel


# ----------------------------------------------------------------------------
# main per tour
# ----------------------------------------------------------------------------

def run_tour(tour, validate_only, n_sims, n_boot):
    t0 = time.time()
    log(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    rng = np.random.default_rng(SEED + (0 if tour == 'atp' else 1000))
    df = load_results(tour)
    sets_col, complete, decider, anomalies = process_matches(df)
    log(f"tour matches {len(df):,}; complete {complete.sum():,} ({complete.mean():.1%}); deciding-set matches {decider.sum():,}; "
        f"score anomalies dropped {anomalies}")
    players, matches, pts, Z, rel = (None,) * 5
    # pool and names (from the charted data; no predictor needed for validation)
    pool_players, charted, _, _, charted_pts = aa.load_tour(tour)
    pool_players = list(pool_players)
    # ---- V1: names ----
    name_ids = {}
    allnames = pd.concat([df[['wn', 'winner_id']].rename(columns={'wn': 'n', 'winner_id': 'id'}),
                          df[['ln', 'loser_id']].rename(columns={'ln': 'n', 'loser_id': 'id'})])
    cnt = allnames.groupby(['n', 'id']).size().reset_index(name='c')
    pid = {}
    for p in pool_players:
        c = cnt[cnt['n'] == norm(p)]
        if len(c) == 0:
            fail(f"V1 {tour}: pool player {p} not found in the tour results")
        pid[p] = c.sort_values('c', ascending=False).iloc[0]['id']
        if len(c) > 1:
            log(f"V1 note: {p} has {len(c)} ids with that name; using the one with most matches")
    log(f"V1 {tour}: all {len(pool_players)} pool players found in the tour results")

    # ---- charted matches located in the tour file (to exclude from the criterion) ----
    cm = charted.drop_duplicates('match_id').copy()
    cm['cdate'] = pd.to_datetime(cm['match_id'].str[:8], format='%Y%m%d', errors='coerce')
    cm['a'] = cm['Player 1'].map(norm)
    cm['b'] = cm['Player 2'].map(norm)
    cm = cm.dropna(subset=['cdate'])
    pair_key = lambda a, b: a + '|' + b if a < b else b + '|' + a
    df['pair'] = [pair_key(a, b) for a, b in zip(df['wn'], df['ln'])]
    by_pair = df.groupby('pair').indices
    excluded = np.zeros(len(df), dtype=bool)
    located, winner_agree, winner_den, consistent = 0, 0, 0, 0
    n_complete_loc = 0
    dvals = df['date'].values
    # last charted point winner per match (V2)
    _m, _raw = shr.load_raw(tour)
    last = _raw.groupby('match_id').tail(1).set_index('match_id')
    for r in cm.itertuples():
        ix = by_pair.get(pair_key(r.a, r.b), [])
        cd = np.datetime64(r.cdate)
        hit = [i for i in ix if dvals[i] <= cd <= dvals[i] + np.timedelta64(21, 'D')]
        if len(hit) == 1:
            located += 1
            i = hit[0]
            excluded[i] = True
            if complete[i] and r.match_id in last.index:
                n_complete_loc += 1
                row = last.loc[r.match_id]
                s_ = sets_col[i]
                bo = int(df['best_of'].values[i])
                need = (bo + 1) // 2
                wg, lg, _tbm = s_[-1]
                gw, gl = (6, 6) if (wg, lg) == (7, 6) else (wg - 1, lg)
                if r.a == df['wn'].values[i]:
                    sw_, sl_, gw_c, gl_c, side = row['Set1'], row['Set2'], row['Gm1'], row['Gm2'], 1
                elif r.b == df['wn'].values[i]:
                    sw_, sl_, gw_c, gl_c, side = row['Set2'], row['Set1'], row['Gm2'], row['Gm1'], 2
                else:
                    continue
                # the chart reaches match point if the state before its last point is the state before the tour score's last point
                if (sw_, sl_, gw_c, gl_c) == (need - 1, len(s_) - need, gw, gl):
                    consistent += 1
                    winner_den += 1
                    winner_agree += int(int(row['PtWinner']) == side)
        elif len(hit) > 1:
            for i in hit:
                excluded[i] = True
    share = located / len(cm)
    agree = winner_agree / max(winner_den, 1)
    cons_share = consistent / max(n_complete_loc, 1)
    log(f"charted matches {len(cm):,}; located uniquely in the tour results {located:,} ({share:.1%}); tour matches excluded "
        f"{int(excluded.sum()):,}")
    log(f"V2 {tour}: of {n_complete_loc:,} located complete matches, {consistent:,} ({cons_share:.1%}) have a chart that reaches match point "
        f"(its last-point state equals the tour score's); in those the charted last-point winner is the tour-file winner in {agree:.2%}")
    if agree < 0.99 or cons_share < 0.85:
        fail(f"V2 {tour}: winner agreement {agree:.4f} (need 0.99) or chart-complete share {cons_share:.3f} (need 0.85)")

    # ---- V3: parsing sanity ----
    comp_idx = np.where(complete)[0]
    bad = 0
    for i in comp_idx[:: max(1, len(comp_idx) // 20000)]:
        s = sets_col[i]
        w_sets = sum(1 for wg, lg, _ in s if wg > lg)
        l_sets = len(s) - w_sets
        bo = df['best_of'].values[i]
        if not (w_sets == (bo + 1) // 2 and l_sets < (bo + 1) // 2):
            bad += 1
    log(f"V3 {tour}: {bad} of {len(comp_idx[:: max(1, len(comp_idx) // 20000)]):,} sampled complete matches have a winner without the "
        f"required set majority (the match winner wins sets_to_win sets)")
    if bad > 0.01 * len(comp_idx[:: max(1, len(comp_idx) // 20000)]):
        fail(f"V3 {tour}: too many inconsistent set counts")

    # ---- V4: Elo ----
    toy = pd.DataFrame({'winner_id': ['A', 'A'], 'loser_id': ['B', 'B']})
    toy_sets = [[(6, 4, False), (6, 4, False)], [(6, 4, False), (4, 6, False), (7, 6, True)]]
    toy_dec = np.array([False, True])
    rw0, rl0, R0 = elo_run(toy, toy_sets, toy_dec, 20.0)
    # match 1: two sets A wins: A 1500 -> 1510 -> after second set; hand calc
    e1 = 0.5
    a1 = 1500 + 20 * (1 - e1)
    e2 = 1 / (1 + 10 ** (-(a1 - (3000 - a1)) / 400))
    a2 = a1 + 20 * (1 - e2)
    if abs(rw0[1] - a2) > 1e-9:
        fail("V4: Elo hand calculation not reproduced (after match 1)")
    # match 2: deciding set and tiebreak set must not update; sets 1 (A wins) and 2 (A loses) do
    e3 = 1 / (1 + 10 ** (-(a2 - (3000 - a2)) / 400))
    a3 = a2 + 20 * (1 - e3)
    e4 = 1 / (1 + 10 ** (-(a3 - (3000 - a3)) / 400))
    a4 = a3 - 20 * e4
    if abs(R0['A'] - a4) > 1e-9 or abs(R0['A'] + R0['B'] - 3000) > 1e-9:
        fail("V4: Elo hand calculation not reproduced (deciding-set and tiebreak sets must not update; zero-sum)")
    log("V4: Elo reproduces the hand calculation (deciding sets and tiebreak sets do not update ratings; zero-sum)")

    # ---- Elo, events, calibration ----
    rw, rl, Rfinal = elo_run(df, sets_col, decider, K_MAIN)
    c1, tb = build_events(df, sets_col, decider, rw, rl)
    c1['excl'] = excluded[c1['i'].values]
    tb['excl'] = excluded[tb['i'].values]
    b3 = fit_b(c1.loc[c1.bo == 3, 'd'].values)
    b5 = fit_b(c1.loc[c1.bo == 5, 'd'].values) if (c1.bo == 5).sum() > 100 else b3
    btb = fit_b(tb['d'].values)
    log(f"calibration {tour}: b(best-of-3 decider) {b3:.3f} (n {int((c1.bo == 3).sum()):,}), b(best-of-5 decider) {b5:.3f} "
        f"(n {int((c1.bo == 5).sum()):,}), b(tiebreak) {btb:.3f} (n {len(tb):,})")
    if min(b3, b5, btb) <= 0:
        fail("V5: non-positive calibration slope")
    c1['b'] = np.where(c1['bo'] == 5, b5, b3)
    c1['exp'] = sigma(c1['b'] * c1['d'])           # expected win prob of the match winner
    tb['exp'] = sigma(btb * tb['d'])
    for name, ev in (('C1', c1), ('C2', tb)):
        sym = pd.concat([pd.DataFrame({'p': ev['exp'], 'y': 1.0}), pd.DataFrame({'p': 1 - ev['exp'], 'y': 0.0})])
        qq = pd.qcut(sym['p'], 10, duplicates='drop')
        gg = sym.groupby(qq, observed=True).agg(p=('p', 'mean'), y=('y', 'mean'))
        dev = float(np.max(np.abs(gg['p'] - gg['y'])))
        log(f"V5 {tour} {name}: largest decile gap between expected and observed win rate {100 * dev:.2f} pp "
            f"(league-wide, both orientations)")
        if dev > 0.02:
            fail(f"V5 {tour} {name}: calibration decile gap {dev:.3f} above 0.02")
    # V6 antisymmetry
    log(f"V6 {tour}: the two players' expected probabilities sum to 1 by construction (antisymmetric model); league-wide mean excess = 0")

    # ---- criterion arrays for pool players ----
    k_sens = sensitivity_k()
    log(f"benchmark: change in set-win probability per unit change in point-win probability (serve and return, 65% serve) k = {k_sens:.2f}")
    keep1 = c1[~c1['excl']]
    keep2 = tb[~tb['excl']]
    res1, res2, abar1, n1, n2, ex1, ex2, exp1 = {}, {}, {}, {}, {}, {}, {}, {}
    b1 = keep1['b'].values
    b2 = np.full(len(keep2), btb)
    for p in pool_players:
        i = pid[p]
        r, dd, e1 = crit_arrays(keep1, 'wid', 'lid', b1, i)
        res1[p], abar1[p], n1[p], exp1[p] = r, (dd.mean() if len(dd) else np.nan), len(r), e1
        ex1[p] = r.mean() if len(r) else np.nan
        r2, d2, _ = crit_arrays(keep2, 'sw', 'sl', b2, i)
        res2[p], n2[p] = r2, len(r2)
        ex2[p] = r2.mean() if len(r2) else np.nan
    n1a = np.array([n1[p] for p in pool_players]); n2a = np.array([n2[p] for p in pool_players])
    ok1 = n1a >= FLOOR
    ok2 = n2a >= FLOOR
    log(f"V1 {tour}: pool players with at least {FLOOR} deciding-set matches {int(ok1.sum())} of {len(pool_players)}; "
        f"tiebreak sets {int(ok2.sum())}; median deciding-set matches {np.median(n1a):.0f}, median tiebreak sets {np.median(n2a):.0f}")
    if ok1.mean() < 0.90 or ok2.mean() < 0.90:
        fail(f"V1 {tour}: fewer than 90% of pool players have {FLOOR} criterion events")

    # ---- positive control simulation (also in validate-only) ----
    sim_rows = []
    sim_pool = [p for p, o in zip(pool_players, ok1) if o]
    abar_sim = np.array([abar1[p] for p in sim_pool])
    n_sim = np.array([len(exp1[p]) for p in sim_pool], dtype=float)
    # extra between-player spread in the criterion beyond binomial noise (model error and any real decider skill), so the
    # simulated power is not optimistic: tau^2 = observed variance of player excess minus its mean binomial variance
    ex_obs = np.array([ex1[p] for p in sim_pool])
    bin_var = np.array([np.sum(exp1[p] * (1 - exp1[p])) / len(exp1[p]) ** 2 for p in sim_pool])
    tau2 = max(0.0, float(np.var(ex_obs, ddof=1) - bin_var.mean()))
    log(f"criterion spread {tour}: SD of player excess {100 * np.sqrt(np.var(ex_obs, ddof=1)):.2f} pp; binomial noise "
        f"{100 * np.sqrt(bin_var.mean()):.2f} pp; excess true SD (model error or real skill) {100 * np.sqrt(tau2):.2f} pp")
    # predictor reliabilities come from the charted data; in validate-only use S's committed chronological value
    com = pd.read_csv(os.path.join(OUT_DIR, 'chronological_reliability.csv'))
    rel_s = float(com[(com.tour == tour) & (com.estimator == 'quartile') & (com.outcome == 'S')]['chronological_spearman_brown'].iloc[0])
    thetas = [0.0, 0.01, 0.02, 0.04, 0.08]
    ns_sim = 200 if validate_only else n_sims
    for th in thetas:
        slopes, pvals = [], []
        E = np.concatenate([exp1[p] for p in sim_pool])
        starts = np.concatenate([[0], np.cumsum([len(exp1[p]) for p in sim_pool])[:-1]])
        for _ in range(ns_sim):
            t_i = rng.normal(0, 1, len(sim_pool))
            z = np.sqrt(rel_s) * t_i + np.sqrt(1 - rel_s) * rng.normal(0, 1, len(sim_pool))
            z = (z - z.mean()) / z.std(ddof=1)
            u_i = rng.normal(0, np.sqrt(tau2), len(sim_pool))
            pr = np.clip(E + np.repeat(th * t_i + u_i, n_sim.astype(int)), 0.001, 0.999)
            y = (rng.random(len(E)) < pr).astype(float)
            ex = np.add.reduceat(y - E, starts) / n_sim
            X = np.column_stack([np.ones(len(z)), z, abar_sim])
            beta, se, _ = wls_hc3(ex, X, n_sim)
            slopes.append(beta[1])
            pvals.append(2 * (1 - stats.t.cdf(abs(beta[1] / se[1]), len(z) - 3)))
        slopes, pvals = np.array(slopes), np.array(pvals)
        sim_rows.append(dict(tour=tour, predictor='S (simulated, reliability %.2f)' % rel_s, theta_pp=100 * th,
                             expected_slope_pp=100 * th * np.sqrt(rel_s), mean_slope_pp=100 * slopes.mean(),
                             power_0125=float((pvals < ALPHA_PRIMARY).mean()), reject_05=float((pvals < 0.05).mean())))
        log(f"V7 {tour} theta {100 * th:.0f} pp per true SD: expected slope {100 * th * np.sqrt(rel_s):.2f} pp, "
            f"mean {100 * slopes.mean():.2f} pp (SE {100 * slopes.std(ddof=1) / np.sqrt(len(slopes)):.2f}); "
            f"power at {ALPHA_PRIMARY:.4f}: {(pvals < ALPHA_PRIMARY).mean():.1%}; rejection at 0.05: {(pvals < 0.05).mean():.1%}")
        if th == 0.0:
            se_ = slopes.std(ddof=1) / np.sqrt(len(slopes))
            if abs(slopes.mean()) > 3 * se_ or not (0.02 <= (pvals < 0.05).mean() <= 0.08):
                fail(f"V7 {tour}: null simulation bias or size outside tolerance")
        if th == 0.04 and abs(slopes.mean() - th * np.sqrt(rel_s)) > 0.15 * th * np.sqrt(rel_s):
            fail(f"V7 {tour}: simulated slope not within 15% of theta * sqrt(rel)")
    if validate_only:
        log(f"validation complete for {tour.upper()} in {time.time() - t0:.0f}s")
        return None

    # ---- predictors ----
    players, matches, pts, Z, rel = get_predictors(tour)
    if list(players) != pool_players:
        fail("predictor player order differs from the pool order")
    pred_names = SEVEN + ['composite']
    rows, play_rows = [], []
    ex1a = np.array([ex1[p] for p in pool_players]); ex2a = np.array([ex2[p] for p in pool_players])
    abar_all = np.array([abar1[p] for p in pool_players])
    # abar for the tiebreak criterion
    abar2 = []
    for p in pool_players:
        i = pid[p]
        _r, d2, _e = crit_arrays(keep2, 'sw', 'sl', b2, i)
        abar2.append(d2.mean() if len(d2) else np.nan)
    abar2 = np.array(abar2)
    # ---- criterion reliability ----
    rel_c1 = criterion_reliability([res1[p] for p, o in zip(pool_players, ok1) if o], rng)
    rel_c2 = criterion_reliability([res2[p] for p, o in zip(pool_players, ok2) if o], rng)
    log(f"criterion reliability {tour}: C1 median {rel_c1[0]:+.3f} [{rel_c1[1]:+.3f}, {rel_c1[2]:+.3f}]; "
        f"C2 median {rel_c2[0]:+.3f} [{rel_c2[1]:+.3f}, {rel_c2[2]:+.3f}]")
    rel_rows = [dict(tour=tour, criterion='C1 deciding-set matches', median=rel_c1[0], p2_5=rel_c1[1], p97_5=rel_c1[2],
                     players=int(ok1.sum()), median_events=float(np.median(n1a[ok1]))),
                dict(tour=tour, criterion='C2 tiebreak sets', median=rel_c2[0], p2_5=rel_c2[1], p97_5=rel_c2[2],
                     players=int(ok2.sum()), median_events=float(np.median(n2a[ok2])))]
    # ---- tests ----
    for crit, exa, nn, ab, ok in (('C1', ex1a, n1a, abar_all, ok1), ('C2', ex2a, n2a, abar2, ok2)):
        for k in pred_names:
            z = np.where(ok, Z[k], np.nan)
            e = np.where(ok, exa, np.nan)
            r = test_predictor(z, e, nn, ab, rng, 50 if validate_only else n_boot)
            primary = (crit == 'C1' and k in ('serve_clutch', 'composite'))
            thr = ALPHA_PRIMARY if primary else ALPHA_SECONDARY
            rows.append(dict(tour=tour, K=K_MAIN, criterion=crit, predictor=k, primary=primary, predictor_reliability=rel[k],
                             below_threshold=bool(r['p'] < thr), threshold=thr, **r))
            log(f"TEST {tour} {crit} {k:<18s}: slope {r['slope_pp']:+.2f} pp per SD [{r['boot_lo_pp']:+.2f}, {r['boot_hi_pp']:+.2f}] "
                f"(SE {r['se_pp']:.2f}, p {r['p']:.4f}; Spearman {r['spearman']:+.3f}) n {r['n_players']}"
                + ("  PRIMARY" if primary else ""))
    # ---- sensitivity: excluding pool-vs-pool matches and K = 10, 30, for the primary tests ----
    pool_ids = set(pid.values())
    sens_rows = []
    keep1_np = keep1[~(keep1['wid'].isin(pool_ids) & keep1['lid'].isin(pool_ids))]
    ex_np, n_np, ab_np = [], [], []
    for p in pool_players:
        i = pid[p]
        r, dd, _e = crit_arrays(keep1_np, 'wid', 'lid', keep1_np['b'].values, i)
        ex_np.append(r.mean() if len(r) else np.nan); n_np.append(len(r)); ab_np.append(dd.mean() if len(dd) else np.nan)
    ex_np, n_np, ab_np = np.array(ex_np), np.array(n_np), np.array(ab_np)
    ok_np = n_np >= FLOOR
    for k in ('serve_clutch', 'composite'):
        r = test_predictor(np.where(ok_np, Z[k], np.nan), np.where(ok_np, ex_np, np.nan), n_np, ab_np, rng, n_boot)
        sens_rows.append(dict(tour=tour, variant='C1 without pool-vs-pool matches', predictor=k, **r))
        log(f"SENS {tour} C1 without pool-vs-pool {k}: slope {r['slope_pp']:+.2f} pp [{r['boot_lo_pp']:+.2f}, {r['boot_hi_pp']:+.2f}] p {r['p']:.4f} n {r['n_players']}")
    for Ks in K_SENS:
        rw_s, rl_s, _ = elo_run(df, sets_col, decider, Ks)
        c1s, _tbs = build_events(df, sets_col, decider, rw_s, rl_s)
        c1s['excl'] = excluded[c1s['i'].values]
        b3s = fit_b(c1s.loc[c1s.bo == 3, 'd'].values)
        b5s = fit_b(c1s.loc[c1s.bo == 5, 'd'].values) if (c1s.bo == 5).sum() > 100 else b3s
        c1s['b'] = np.where(c1s['bo'] == 5, b5s, b3s)
        k1 = c1s[~c1s['excl']]
        exs, ns_, abs_ = [], [], []
        for p in pool_players:
            i = pid[p]
            r, dd, _e = crit_arrays(k1, 'wid', 'lid', k1['b'].values, i)
            exs.append(r.mean() if len(r) else np.nan); ns_.append(len(r)); abs_.append(dd.mean() if len(dd) else np.nan)
        exs, ns_, abs_ = np.array(exs), np.array(ns_), np.array(abs_)
        oks = ns_ >= FLOOR
        for k in ('serve_clutch', 'composite'):
            r = test_predictor(np.where(oks, Z[k], np.nan), np.where(oks, exs, np.nan), ns_, abs_, rng, n_boot)
            sens_rows.append(dict(tour=tour, variant=f'C1 Elo K={Ks:g}', predictor=k, **r))
            log(f"SENS {tour} C1 K={Ks:g} {k}: slope {r['slope_pp']:+.2f} pp [{r['boot_lo_pp']:+.2f}, {r['boot_hi_pp']:+.2f}] p {r['p']:.4f}")
    # ---- benchmark ----
    sd = SD_TRUE_S[tour]
    bench_lo = 100 * k_sens * 0.5 * sd / 100.0     # pp of win probability per true SD (sd is in pp of point-win prob)
    bench_hi = 100 * k_sens * sd / 100.0
    s_rel = rel['serve_clutch']
    log(f"benchmark {tour}: one true SD of serve clutch ({sd:.2f} pp) implies a change in deciding-set win probability of "
        f"{bench_lo:.1f} to {bench_hi:.1f} pp per true SD, or {bench_lo * np.sqrt(s_rel):.1f} to {bench_hi * np.sqrt(s_rel):.1f} pp per SD of the observed score")
    bench = pd.DataFrame([dict(tour=tour, k=k_sens, sd_true_pp=sd, per_true_sd_low=bench_lo, per_true_sd_high=bench_hi,
                               score_reliability=s_rel, per_obs_sd_low=bench_lo * np.sqrt(s_rel),
                               per_obs_sd_high=bench_hi * np.sqrt(s_rel), b_bo3=b3, b_bo5=b5, b_tiebreak=btb,
                               charted_located_share=share, winner_agreement=agree,
                               excluded_tour_matches=int(excluded.sum()))])
    players_df = pd.DataFrame({'tour': tour, 'player': pool_players, 'deciders': n1a, 'excess_c1_pp': 100 * ex1a, 'tiebreaks': n2a,
                               'excess_c2_pp': 100 * ex2a, 'mean_strength_advantage_c1': abar_all,
                               **{f'z_{k}': Z[k] for k in pred_names}})
    log(f"{tour.upper()} done in {time.time() - t0:.0f}s")
    return (pd.DataFrame(rows), pd.DataFrame(sens_rows), pd.DataFrame(rel_rows), pd.DataFrame(sim_rows), bench, players_df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tours', nargs='+', default=['atp', 'wta'])
    ap.add_argument('--sims', type=int, default=1000)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--validate-only', action='store_true')
    args = ap.parse_args()
    for tour in args.tours:
        out = run_tour(tour, args.validate_only, args.sims, args.boot)
        if out is None:
            continue
        names = ['tests', 'sensitivity', 'criterion_reliability', 'power', 'benchmark', 'players']
        for n, d in zip(names, out):
            d.to_csv(os.path.join(OUT_DIR, f'decider_validity_{n}_{tour}.csv'), index=False)
    log("=== RUN END")


if __name__ == '__main__':
    main()
