"""
all_shots_analyses.py -- the all-shot (serve, return and rally) clutch
analyses pre-registered in docs/combined/all_shots_preregistration.md
(written 2026-11-16, before this script existed).

Classifies every point by where it ended (serve, return or rally), builds
shot-level outcomes under leverage (unforced errors, winners, aces, double
faults, by shot family), and for each one reports
  A. split-half reliability on the paper's original split and 1,000 random
     balanced splits;
  B. the entropy correlation, TOST equivalence bound and reliability-corrected
     bound (same machinery as Section 5.2 of the paper);
  C. the share of points decided in each phase in the top and bottom
     leverage quartiles.

Validation first: the same code must reproduce the paper's serve and return
quartile-clutch reliabilities on the original split to within 0.001, and
hitter attribution must pass the standing parity check, or the script aborts
before writing anything.

Needs the raw MCP files in results/{tour}/ (see the README) and, through
applications_analyses.load_tour, the cached leverage point table.
Usage: python src/robustness/all_shots_analyses.py [--splits N]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse

import numpy as np
import pandas as pd
from scipy import stats

import applications_analyses as aa
import disattenuated_equivalence_bounds as deb
import formulas as f
import parsing as par
import split_half_reliability as shr

REPO_ROOT = aa.REPO_ROOT
OUT_DIR = aa.OUT_DIR
SEED = 20261116
N_SPLITS = 1000
MIN_PTS = 30          # points per bucket (point-win outcomes)
MIN_SHOTS = 100       # shots (or serve points) per bucket (shot-level outcomes)
FAULT_CHARS = set('ndwxg!')
FAMILIES = {'forehand': set('f'), 'backhand': set('b'), 'slice': set('rs'),
            'net': set('vzopjkhi')}
FAM_NAMES = list(FAMILIES)
PHASE = {'serve': 0, 'return': 1, 'rally': 2, 'other': 3}

OUTCOMES = ['serve_clutch', 'return_clutch',                       # validation, paper's definitions
            'R1_rally_point', 'R2_error_all', 'R3_winner_all',
            'R4_error_forehand', 'R5_error_backhand', 'R6_error_slice', 'R7_error_net',
            'R8_double_fault', 'R9_ace']
LABELS = {
    'serve_clutch': 'Serve quartile clutch (paper)', 'return_clutch': 'Return quartile clutch (paper)',
    'R1_rally_point': 'R1 Rally-phase point clutch', 'R2_error_all': 'R2 Unforced-error clutch, all shots',
    'R3_winner_all': 'R3 Winner clutch, all shots', 'R4_error_forehand': 'R4 Error clutch, forehand',
    'R5_error_backhand': 'R5 Error clutch, backhand', 'R6_error_slice': 'R6 Error clutch, slice',
    'R7_error_net': 'R7 Error clutch, net game', 'R8_double_fault': 'R8 Double-fault clutch (serve)',
    'R9_ace': 'R9 Ace clutch (serve)'}


# =============================================================================
# POINT PARSING
# =============================================================================

def parse_point(s):
    """Returns a tuple describing one point, or None if there is no string.
    (phase, server_shots, returner_shots, last_hitter_is_server, term,
     last_family, ace, double_fault, fam_counts_server[4], fam_counts_returner[4])"""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    toks = par.extract_shot_dir_pairs(s)
    n = len(toks)
    last = s[-1]
    if last in '*#@':
        term = last
    elif n == 0 and last in FAULT_CHARS:
        term = 'F'
    else:
        term = '?'
    fam_s = [0, 0, 0, 0]
    fam_r = [0, 0, 0, 0]
    ns = nr = 0
    for i, (ch, _) in enumerate(toks):
        k = next((j for j, name in enumerate(FAM_NAMES) if ch in FAMILIES[name]), -1)
        if i % 2 == 0:            # returner hits even tokens (hitter-parity fix)
            nr += 1
            if k >= 0:
                fam_r[k] += 1
        else:
            ns += 1
            if k >= 0:
                fam_s[k] += 1
    ace = int(n == 0 and term == '*')
    dbl = int(n == 0 and term == 'F')
    if n == 0 and term in ('*', 'F'):
        phase = PHASE['serve']
    elif n == 1 or (n == 0 and term == '#'):
        phase = PHASE['return']
    elif n >= 2:
        phase = PHASE['rally']
    else:
        phase = PHASE['other']
    if n >= 1:
        last_server = int((n - 1) % 2 == 1)
        last_fam = next((j for j, name in enumerate(FAM_NAMES) if toks[-1][0] in FAMILIES[name]), -1)
    else:
        last_server = int(term in ('*', 'F'))   # ace / double fault: server; '#': returner
        last_fam = -1
    return (phase, ns, nr, last_server, term, last_fam, ace, dbl, fam_s, fam_r)


def build_point_table(tour, matches, half_map, pts):
    """Aligns the raw notation with the cached leverage table and returns the
    leverage table with all-shot columns added. Aborts if rows do not align."""
    _, points = shr.load_raw(tour)
    rel = points[points['match_id'].isin(set(half_map.keys()))].reset_index(drop=True)
    if len(rel) != len(pts) or not (rel['match_id'].values == pts['match_id'].values).all():
        raise SystemExit(f"{tour.upper()}: raw points do not align with the cached leverage table.")
    s = rel['2nd'].where(rel['2nd'].notna(), rel['1st'])
    parsed = [parse_point(x) for x in s.tolist()]
    n = len(parsed)
    cols = {k: np.zeros(n, dtype=np.int16) for k in
            ('phase', 'ns', 'nr', 'last_server', 'last_fam', 'ace', 'dbl', 'ok')}
    term = np.array(['?'] * n, dtype='<U1')
    fam_s = np.zeros((n, 4), dtype=np.int16)
    fam_r = np.zeros((n, 4), dtype=np.int16)
    for i, p in enumerate(parsed):
        if p is None:
            cols['phase'][i] = PHASE['other']
            continue
        cols['ok'][i] = 1
        (cols['phase'][i], cols['ns'][i], cols['nr'][i], cols['last_server'][i], term[i],
         cols['last_fam'][i], cols['ace'][i], cols['dbl'][i], fs, fr) = p
        fam_s[i], fam_r[i] = fs, fr
    out = pts.reset_index(drop=True).copy()
    for k, v in cols.items():
        out[k] = v
    out['term'] = term
    for j, name in enumerate(FAM_NAMES):
        out[f'fam_s_{name}'] = fam_s[:, j]
        out[f'fam_r_{name}'] = fam_r[:, j]
    return out


def parity_check(tab, min_rate=0.85):
    """For points ending in a winner after at least one shot token, the last
    hitter must be the point winner (same logic as parsing.verify_hitter_parity)."""
    sel = tab[(tab['term'] == '*') & (tab['phase'] >= PHASE['return']) & (tab['ok'] == 1)]
    hitter_is_server = sel['last_server'] == 1
    server_won = sel['server_won_point'] == 1
    rate = float((hitter_is_server == server_won).mean())
    print(f"  hitter parity on {len(sel):,} winner points: {rate:.3f} (floor {min_rate})")
    if rate < min_rate:
        raise SystemExit("Hitter-attribution parity check failed; aborting.")
    return rate


# =============================================================================
# PER-PLAYER ARRAYS
# =============================================================================

def player_arrays(tab, players, gm):
    """For each player, arrays over the points they played (server or returner)."""
    out = {}
    by_s = tab.groupby('server').indices
    by_r = tab.groupby('returner').indices
    for p in players:
        parts = []
        for role, idx in (('s', by_s.get(p, np.array([], dtype=int))), ('r', by_r.get(p, np.array([], dtype=int)))):
            d = tab.iloc[idx]
            is_s = role == 's'
            own = d['last_server'].values == (1 if is_s else 0)
            term = d['term'].values
            nfin = d['phase'].values
            fam_cols = [f"fam_{'s' if is_s else 'r'}_{n}" for n in FAM_NAMES]
            shots = d['ns'].values if is_s else d['nr'].values
            has_shot = d['phase'].values >= PHASE['return']
            ufe_pt = (term == '@') & own & has_shot
            win_pt = (term == '*') & own & has_shot
            lf = d['last_fam'].values
            rec = {
                'lev': d['leverage_p65'].values,
                'won': (d['server_won_point'].values if is_s else 1 - d['server_won_point'].values),
                'is_serve': np.full(len(d), is_s),
                'gm': gm[idx],
                'rally': d['phase'].values == PHASE['rally'],
                'shots': shots.astype(float),
                'ufe': ufe_pt.astype(float),
                'win': win_pt.astype(float),
                'ace': (d['ace'].values if is_s else np.zeros(len(d))).astype(float),
                'dbl': (d['dbl'].values if is_s else np.zeros(len(d))).astype(float),
            }
            for j, name in enumerate(FAM_NAMES):
                rec[f'sh_{name}'] = d[fam_cols[j]].values.astype(float)
                rec[f'ufe_{name}'] = (ufe_pt & (lf == j)).astype(float)
            parts.append(rec)
        out[p] = {k: np.concatenate([parts[0][k], parts[1][k]]) for k in parts[0]}
    return out


def _buckets(lev):
    q25, q75 = np.quantile(lev, [0.25, 0.75])
    return lev >= q75, lev <= q25


def _rate_diff(num, den, top, bot, sign, min_den):
    """sign * (rate_top - rate_bot) with a denominator sufficiency floor."""
    dt, db = den[top].sum(), den[bot].sum()
    if dt < min_den or db < min_den:
        return np.nan
    return sign * (num[top].sum() / dt - num[bot].sum() / db)


def evaluate(d, m):
    """All outcomes for one player on the points selected by boolean mask m."""
    v = {k: x[m] for k, x in d.items()}
    keep = ~np.isnan(v['lev'])          # the paper's quartile_clutch drops missing leverage first
    v = {k: x[keep] for k, x in v.items()}
    n = len(v['lev'])
    res = dict.fromkeys(OUTCOMES, np.nan)
    if n < 4 * MIN_PTS:
        return res
    # paper's role-specific point-win quartile clutch (validation)
    for role, key in ((True, 'serve_clutch'), (False, 'return_clutch')):
        r = v['is_serve'] == role
        if r.sum() >= 4 * MIN_PTS:
            top, bot = _buckets(v['lev'][r])
            if top.sum() >= MIN_PTS and bot.sum() >= MIN_PTS:
                w = v['won'][r]
                res[key] = w[top].mean() - w[bot].mean()
    top, bot = _buckets(v['lev'])
    # R1: rally-decided points, thresholds from all the player's points
    rt, rb = top & v['rally'], bot & v['rally']
    if rt.sum() >= MIN_PTS and rb.sum() >= MIN_PTS:
        res['R1_rally_point'] = v['won'][rt].mean() - v['won'][rb].mean()
    res['R2_error_all'] = _rate_diff(v['ufe'], v['shots'], top, bot, -1.0, MIN_SHOTS)
    res['R3_winner_all'] = _rate_diff(v['win'], v['shots'], top, bot, +1.0, MIN_SHOTS)
    for j, name in enumerate(FAM_NAMES):
        res[f'R{4 + j}_error_{name}'] = _rate_diff(v[f'ufe_{name}'], v[f'sh_{name}'], top, bot, -1.0, MIN_SHOTS)
    # serve-only outcomes: thresholds from serve points
    sv = v['is_serve']
    if sv.sum() >= 4 * MIN_PTS:
        stop, sbot = _buckets(v['lev'][sv])
        ones = np.ones(sv.sum())
        res['R8_double_fault'] = _rate_diff(v['dbl'][sv], ones, stop, sbot, -1.0, MIN_SHOTS)
        res['R9_ace'] = _rate_diff(v['ace'][sv], ones, stop, sbot, +1.0, MIN_SHOTS)
    return res


def split_rel(va, vb):
    """Spearman-Brown reliability per outcome from (n_players, n_outcomes) arrays,
    using players with both halves defined."""
    out = []
    for k in range(va.shape[1]):
        ok = ~np.isnan(va[:, k]) & ~np.isnan(vb[:, k])
        if ok.sum() < 10:
            out.append(np.nan)
            continue
        r = np.corrcoef(va[ok, k], vb[ok, k])[0, 1]
        out.append(f.spearman_brown(r))
    return np.array(out)


def half_values(arrs, players, assign_by_player):
    va = np.full((len(players), len(OUTCOMES)), np.nan)
    vb = np.full((len(players), len(OUTCOMES)), np.nan)
    for j, p in enumerate(players):
        in_a = assign_by_player[j]
        ra, rb = evaluate(arrs[p], in_a), evaluate(arrs[p], ~in_a)
        va[j] = [ra[k] for k in OUTCOMES]
        vb[j] = [rb[k] for k in OUTCOMES]
    return va, vb


# =============================================================================
# MAIN ANALYSES
# =============================================================================

def run_tour(tour, n_splits):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = build_point_table(tour, matches, half_map, pts)
    parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    arrs = player_arrays(tab, players, gm)
    orig_assign = np.array([half_map[m] == 'A' for m in sorted_ids])

    # ---- original split + validation ----
    va, vb = half_values(arrs, players, [orig_assign[arrs[p]['gm']] for p in players])
    orig = split_rel(va, vb)
    doc = {'serve_clutch': aa.DOC_RELIABILITY[(tour, 'serve')], 'return_clutch': aa.DOC_RELIABILITY[(tour, 'return')]}
    for k, ref in doc.items():
        d = abs(orig[OUTCOMES.index(k)] - ref)
        print(f"VALIDATION {k}: new {orig[OUTCOMES.index(k)]:+.4f} reported {ref:+.4f} diff {d:.5f}")
        if d > 0.001:
            raise SystemExit(f"{tour.upper()}: validation failed for {k}; stop and investigate.")
    print("VALIDATION PASS")

    # ---- random splits ----
    rng = np.random.default_rng(SEED)
    n_m = len(sorted_ids)
    draws = np.zeros((n_splits, len(OUTCOMES)))
    for s in range(n_splits):
        order = rng.permutation(n_m)
        assign = np.zeros(n_m, dtype=int)
        assign[order[1::2]] = 1
        in_a_all = assign == 0
        va, vb = half_values(arrs, players, [in_a_all[arrs[p]['gm']] for p in players])
        draws[s] = split_rel(va, vb)
        if (s + 1) % 100 == 0:
            print(f"  ...{s + 1}/{n_splits} splits")
    rel_rows = []
    for k, name in enumerate(OUTCOMES):
        d = draws[:, k]
        d = d[~np.isnan(d)]
        row = {'tour': tour, 'outcome': name, 'label': LABELS[name], 'original_split': orig[k],
               'median': np.median(d) if len(d) else np.nan,
               'p2_5': np.percentile(d, 2.5) if len(d) else np.nan,
               'p97_5': np.percentile(d, 97.5) if len(d) else np.nan,
               'share_below_070': float((d < 0.70).mean()) if len(d) else np.nan,
               'share_at_or_above_070': float((d >= 0.70).mean()) if len(d) else np.nan,
               'n_valid_splits': len(d)}
        rel_rows.append(row)
        print(f"{LABELS[name]:38s} orig {orig[k]:+.3f}  median {row['median']:+.3f}  "
              f"[{row['p2_5']:+.3f}, {row['p97_5']:+.3f}]  share>=0.70 {row['share_at_or_above_070']:.1%}")
    rel = pd.DataFrame(rel_rows)

    # ---- full-sample values, entropy test, corrected bounds ----
    feat_path = 'step2_full_pool_features.csv' if tour == 'atp' else 'wta_full_pool_features.csv'
    ent = pd.read_csv(os.path.join(REPO_ROOT, 'results', tour, feat_path))
    ent = ent[ent['transition_entropy_sufficient']].set_index('player')['conditional_normalized_entropy']
    full = {p: evaluate(arrs[p], np.ones(len(arrs[p]['lev']), dtype=bool)) for p in players}
    full_df = pd.DataFrame.from_dict(full, orient='index')
    ent_rel = aa.DOC_RELIABILITY[(tour, 'entropy')]
    test_rows = []
    for name in ('R1_rally_point', 'R2_error_all', 'R3_winner_all'):
        both = pd.concat([ent, full_df[name]], axis=1, keys=['x', 'y']).dropna()
        r, p = stats.pearsonr(both['x'], both['y'])
        tb = deb.tightest_tost_bound(both['x'].values, both['y'].values)
        b_obs = tb[0] if tb else np.nan
        med = rel.loc[rel['outcome'] == name, 'median'].iloc[0]
        att = np.sqrt(ent_rel * med) if med > 0 else np.nan
        test_rows.append({'tour': tour, 'outcome': name, 'n': len(both), 'r': r, 'p': p,
                          'bonferroni_threshold': 0.05 / 6, 'tost_bound_observed': b_obs,
                          'outcome_reliability_median': med,
                          'tost_bound_corrected': (b_obs / att) if att and not np.isnan(att) else np.nan})
        print(f"ENTROPY vs {name}: r={r:+.3f} p={p:.3f} n={len(both)}  bound obs {b_obs:.3f} corrected "
              f"{test_rows[-1]['tost_bound_corrected']:.3f}")

    # ---- phase shares by leverage quartile ----
    tab['lev_bucket'] = 'middle'
    q25, q75 = tab['leverage_p65'].quantile([0.25, 0.75])
    tab.loc[tab['leverage_p65'] >= q75, 'lev_bucket'] = 'top'
    tab.loc[tab['leverage_p65'] <= q25, 'lev_bucket'] = 'bottom'
    phase_names = {v: k for k, v in PHASE.items()}
    shares = (tab.groupby('lev_bucket')['phase'].value_counts(normalize=True).rename('share').reset_index())
    shares['phase'] = shares['phase'].map(phase_names)
    shares.insert(0, 'tour', tour)
    print(shares.pivot(index='lev_bucket', columns='phase', values='share').round(3))
    return rel, pd.DataFrame(test_rows), shares


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=N_SPLITS)
    args = ap.parse_args()
    rels, tests, shares = [], [], []
    for tour in ('atp', 'wta'):
        r, t, s = run_tour(tour, args.splits)
        rels.append(r); tests.append(t); shares.append(s)
    pd.concat(rels).to_csv(os.path.join(OUT_DIR, 'allshots_reliability.csv'), index=False)
    pd.concat(tests).to_csv(os.path.join(OUT_DIR, 'allshots_entropy_tests.csv'), index=False)
    pd.concat(shares).to_csv(os.path.join(OUT_DIR, 'allshots_phase_shares.csv'), index=False)
    print(f"\nWrote outputs to {OUT_DIR}")


if __name__ == '__main__':
    main()
