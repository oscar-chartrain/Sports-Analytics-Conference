"""
applications_analyses.py -- the three analyses pre-registered in
docs/combined/applications_preregistration.md, run in that order:

  1. Split-half reliability of Tennis Abstract's Balanced Leverage Ratio
     (faithful definition: mean of serve-LR and return-LR), plus the pooled
     LR this repo has called `blr_combined`, plus LR_serve / LR_return.
  2. Data-requirement projections (Spearman-Brown prophecy, primary;
     per-player shrinkage reliability, secondary).
  3. Player-cluster bootstrap intervals on clutch scores and ranks.

Leverage depends only on a point's score state, so it is computed ONCE per
tour on every relevant point (the same point set split_half_reliability.py
uses) and cached. The A/B halves and every bootstrap replicate are then
subsets / resamples of that one table, which is exactly what
split_half_reliability.py's per-half rebuild computes for the p65 variant
(p65 leverage does not depend on which other points are in the sample).

Usage:
  python3 applications_analyses.py              # all three, both tours
  python3 applications_analyses.py --skip-entropy  # skip the slow entropy
                                                   # sanity re-run
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from scipy import stats

import features as feat
import formulas as f
import split_half_reliability as shr

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(REPO_ROOT, 'results', 'applications')
MIN_OBS = feat.MIN_OBS
LEV = 'leverage_p65'

# Documented values the same-run sanity check must reproduce (+-0.005).
DOCUMENTED = {
    'atp': {'serve': 0.572, 'return': 0.231, 'entropy': 0.925},
    'wta': {'serve': 0.578, 'return': 0.055, 'entropy': None},
}
DOCUMENTED_SHRINKAGE = {
    'atp': {'serve': 0.594, 'return': 0.371},
    'wta': {'serve': 0.624, 'return': 0.132},
}
TARGETS = (0.70, 0.80)
B_BOOT = 2000
SEED = 20261103
NAMED = ['Jannik Sinner', 'Carlos Alcaraz', 'Novak Djokovic', 'Roger Federer']


# =============================================================================
# Point table (cached)
# =============================================================================

def build_point_table(tour):
    cache = os.path.join(OUT_DIR, f'cache_{tour}_points_p65.pkl')
    if os.path.exists(cache):
        with open(cache, 'rb') as fh:
            return pickle.load(fh)
    players = shr.load_pool(tour)
    matches, points = shr.load_raw(tour)
    half_map, relevant_matches = shr.split_matches(matches, players)
    relevant_points = points[points['match_id'].isin(set(half_map.keys()))]
    t0 = time.time()
    summary, pts = feat.build_clutch_features(relevant_matches, relevant_points, players,
                                              return_points=True)
    print(f"  leverage for {len(pts):,} points in {time.time() - t0:.0f}s")
    pts = pts[['match_id', 'server', 'returner', 'server_won_point', LEV]].copy()
    pts['half'] = pts['match_id'].map(half_map)
    obj = {'players': players, 'pts': pts, 'summary': summary,
           'relevant_matches': relevant_matches, 'half_map': half_map}
    with open(cache, 'wb') as fh:
        pickle.dump(obj, fh)
    return obj


def role_points(pts, player, role):
    """One player's points in one role, with 'won' from that player's side."""
    if role == 'serve':
        sub = pts[pts['server'] == player][['match_id', LEV, 'server_won_point']]
        won = sub['server_won_point'].values
    else:
        sub = pts[pts['returner'] == player][['match_id', LEV, 'server_won_point']]
        won = 1.0 - sub['server_won_point'].values
    return sub['match_id'].values, sub[LEV].values.astype(float), won.astype(float)


# =============================================================================
# Measures on arrays (shared by halves and bootstrap)
# =============================================================================

def quartile_clutch_arr(lev, won):
    """Array version of features.quartile_clutch (same thresholds, same
    tie handling via <= / >= on pandas-quantile cut points)."""
    ok = ~np.isnan(lev) & ~np.isnan(won)
    lev, won = lev[ok], won[ok]
    if len(lev) < MIN_OBS * 4:
        return np.nan
    q_low = np.quantile(lev, 0.25)   # numpy 'linear' == pandas default
    q_high = np.quantile(lev, 0.75)
    low = won[lev <= q_low]
    high = won[lev >= q_high]
    if len(low) < MIN_OBS or len(high) < MIN_OBS:
        return np.nan
    return high.mean() - low.mean()


def lr_arr(lev, won):
    """Leverage ratio: mean leverage of points won / of points lost."""
    ok = ~np.isnan(lev)
    lev, won = lev[ok], won[ok]
    w = won == 1
    if w.sum() < MIN_OBS or (~w).sum() < MIN_OBS:
        return np.nan
    lost_mean = lev[~w].mean()
    if lost_mean == 0:
        return np.nan
    return lev[w].mean() / lost_mean


def pooled_lr_arr(lev_s, won_s, lev_r, won_r):
    """This repo's existing `blr_combined`: all points pooled. Mirrors
    features.build_clutch_features exactly (no MIN_OBS gate there)."""
    lev = np.concatenate([lev_s, lev_r])
    won = np.concatenate([won_s, won_r])
    ok = ~np.isnan(lev)
    lev, won = lev[ok], won[ok]
    lost_mean = lev[won == 0].mean()
    if not lost_mean:
        return np.nan
    return lev[won == 1].mean() / lost_mean


def all_measures(lev_s, won_s, lev_r, won_r):
    lr_s = lr_arr(lev_s, won_s)
    lr_r = lr_arr(lev_r, won_r)
    return {
        'serve_clutch': quartile_clutch_arr(lev_s, won_s),
        'return_clutch': quartile_clutch_arr(lev_r, won_r),
        'lr_serve': lr_s,
        'lr_return': lr_r,
        'blr': (lr_s + lr_r) / 2 if not (np.isnan(lr_s) or np.isnan(lr_r)) else np.nan,
        'pooled_lr': pooled_lr_arr(lev_s, won_s, lev_r, won_r),
    }


def player_arrays(pts, players):
    out = {}
    for p in players:
        out[p] = {'serve': role_points(pts, p, 'serve'), 'return': role_points(pts, p, 'return')}
    return out


def measures_for(arrs, mask_fn=None):
    rows = {}
    for p, d in arrs.items():
        ms, ls, ws = d['serve']
        mr, lr_, wr = d['return']
        if mask_fn is not None:
            ks, kr = mask_fn(ms), mask_fn(mr)
            ls, ws, lr_, wr = ls[ks], ws[ks], lr_[kr], wr[kr]
        rows[p] = all_measures(ls, ws, lr_, wr)
    return pd.DataFrame(rows).T


# =============================================================================
# Analysis 1
# =============================================================================

def reliability(a, b):
    both = a.dropna().index.intersection(b.dropna().index)
    n = len(both)
    if n < 4:
        return {'n': n, 'r_half': np.nan, 'p': np.nan, 'r_full': np.nan,
                'ci_lo': np.nan, 'ci_hi': np.nan}
    r, p = stats.pearsonr(a[both].astype(float), b[both].astype(float))
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return {'n': n, 'r_half': r, 'p': p, 'r_full': f.spearman_brown(r),
            'ci_lo': f.spearman_brown(lo), 'ci_hi': f.spearman_brown(hi)}


def analysis1(tour, obj, arrs, skip_entropy):
    print(f"\n--- Analysis 1: BLR split-half reliability ({tour.upper()}) ---")
    pts = obj['pts']
    half_of = obj['half_map']
    ma = measures_for(arrs, lambda m: np.array([half_of.get(x) == 'A' for x in m], dtype=bool))
    mb = measures_for(arrs, lambda m: np.array([half_of.get(x) == 'B' for x in m], dtype=bool))
    full = measures_for(arrs)

    results = {}
    for col in ['serve_clutch', 'return_clutch', 'blr', 'pooled_lr', 'lr_serve', 'lr_return']:
        results[col] = reliability(ma[col], mb[col])
        r = results[col]
        print(f"  {col:14s} n={r['n']:3d}  r_half={r['r_half']:+.4f}  "
              f"rel(SB)={r['r_full']:.3f}  95% CI [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]")

    # Sanity 1: clutch reliabilities reproduce documented values.
    checks = {}
    for role in ['serve', 'return']:
        got = results[f'{role}_clutch']['r_full']
        want = DOCUMENTED[tour][role]
        checks[f'{role}_clutch_reproduces_doc'] = bool(abs(got - want) <= 0.005)
        print(f"  SANITY {role} clutch: {got:.4f} vs documented {want:.3f} -> "
              f"{'PASS' if checks[f'{role}_clutch_reproduces_doc'] else 'FAIL'}")

    # Sanity 2: full-sample pooled LR == pipeline's blr_combined.
    summ = obj['summary'].set_index('player')
    diff = (full['pooled_lr'].astype(float) - summ['blr_combined'].reindex(full.index)).abs().max()
    checks['pooled_lr_matches_blr_combined'] = bool(diff < 1e-12)
    print(f"  SANITY pooled LR vs pipeline blr_combined: max |diff| = {diff:.2e} -> "
          f"{'PASS' if checks['pooled_lr_matches_blr_combined'] else 'FAIL'}")

    # Sanity 3 (entropy reproduces), the slow part.
    if not skip_entropy:
        matches, points = shr.load_raw(tour)
        rel_pts = points[points['match_id'].isin(set(half_of.keys()))]
        ea = shr.build_entropy_half(obj['relevant_matches'], rel_pts, obj['players'], half_of, 'A')
        eb = shr.build_entropy_half(obj['relevant_matches'], rel_pts, obj['players'], half_of, 'B')
        er = reliability(pd.Series(ea), pd.Series(eb))
        results['entropy'] = er
        want = DOCUMENTED[tour]['entropy']
        if want is not None:
            checks['entropy_reproduces_doc'] = bool(abs(er['r_full'] - want) <= 0.005)
        print(f"  entropy rel(SB)={er['r_full']:.4f}" +
              (f" vs documented {want:.3f} -> {'PASS' if checks['entropy_reproduces_doc'] else 'FAIL'}"
               if want is not None else " (no single documented WTA figure to check against)"))

    # Convergent-validity bookkeeping.
    combined_clutch = full[['serve_clutch', 'return_clutch']].astype(float).mean(axis=1)
    cv = {
        'blr_vs_pooled_lr': stats.pearsonr(full['blr'].astype(float), full['pooled_lr'].astype(float))[0],
        'pooled_lr_vs_combined_clutch': stats.pearsonr(full['pooled_lr'].astype(float), combined_clutch)[0],
        'blr_vs_combined_clutch': stats.pearsonr(full['blr'].astype(float), combined_clutch)[0],
    }
    for k, v in cv.items():
        print(f"  full-sample r({k}) = {v:.3f}")

    ma.add_suffix('_a').join(mb.add_suffix('_b')).join(full.add_suffix('_full')) \
        .to_csv(os.path.join(OUT_DIR, f'{tour}_blr_halves.csv'), index_label='player')
    return results, checks, cv, full


# =============================================================================
# Analysis 2
# =============================================================================

def prophecy_k(rho, target):
    if rho is None or np.isnan(rho) or rho <= 0:
        return np.nan
    return target * (1 - rho) / (rho * (1 - target))


def analysis2(tour, obj, rel1):
    print(f"\n--- Analysis 2: data requirement ({tour.upper()}) ---")
    rm = obj['relevant_matches']
    counts = pd.concat([rm['Player 1'], rm['Player 2']]).value_counts()
    med_matches = float(counts.reindex(obj['players']).median())
    print(f"  median charted matches in pool: {med_matches:.0f}")

    inputs = {
        'serve_clutch (quartile)': DOCUMENTED[tour]['serve'],
        'return_clutch (quartile)': DOCUMENTED[tour]['return'],
        'serve_clutch (shrinkage)': DOCUMENTED_SHRINKAGE[tour]['serve'],
        'return_clutch (shrinkage)': DOCUMENTED_SHRINKAGE[tour]['return'],
        'BLR (faithful)': rel1['blr']['r_full'],
        'pooled LR': rel1['pooled_lr']['r_full'],
    }
    primary = []
    for name, rho in inputs.items():
        row = {'measure': name, 'reliability': rho}
        for t in TARGETS:
            k = prophecy_k(rho, t)
            row[f'k_{t:.2f}'] = k
            row[f'matches_{t:.2f}'] = k * med_matches if not np.isnan(k) else np.nan
        primary.append(row)
        if rho >= TARGETS[0]:
            note = '(already at/above 0.70)'
        elif np.isnan(row['k_0.70']):
            note = 'NOT ATTAINABLE by adding data'
        else:
            note = f"x{row['k_0.70']:.1f} data  ~{row['matches_0.70']:.0f} matches"
        print(f"  {name:26s} rel={rho:.3f}  to 0.70: {note}")
    primary = pd.DataFrame(primary)

    # Secondary: per-player shrinkage reliability on the full sample.
    summ = obj['summary'].set_index('player')
    pts = obj['pts']
    secondary = []
    for role in ['serve', 'return']:
        raw = summ[f'{role}_clutch_p65'].astype(float)
        nh = summ[f'n_{role}_high_leverage'].astype(float)
        nl = summ[f'n_{role}_low_leverage'].astype(float)
        ok = raw.notna() & (nh > 0) & (nl > 0)
        raw, nh, nl = raw[ok], nh[ok], nl[ok]
        var_i = 0.25 * (1 / nh + 1 / nl)
        tau2 = max(0.0, raw.var(ddof=1) - var_i.mean())
        rel_i = tau2 / (tau2 + var_i) if tau2 > 0 else var_i * 0
        side = 'server' if role == 'serve' else 'returner'
        # median high-leverage points per charted match, for this role
        per_match = (nh / counts.reindex(nh.index)).median()
        if tau2 > 0:
            n_star = 0.5 * TARGETS[0] / ((1 - TARGETS[0]) * tau2)
            matches_star = n_star / per_match
        else:
            n_star = matches_star = np.nan
        secondary.append({'role': role, 'tau2': tau2,
                          'share_rel_ge_070': float((rel_i >= 0.70).mean()),
                          'median_rel_i': float(rel_i.median()),
                          'n_star_high_lev_points': n_star,
                          'median_high_lev_pts_per_match': per_match,
                          'matches_star': matches_star})
        print(f"  [shrinkage] {role}: tau2={tau2:.6f}  median rel_i={rel_i.median():.3f}  "
              f"share >=0.70: {(rel_i >= 0.70).mean():.1%}  "
              f"matches for 0.70 ~ {matches_star:.0f}")
    secondary = pd.DataFrame(secondary)

    # Pre-registered consistency check (factor of 3).
    cons = {}
    for role in ['serve', 'return']:
        a = primary.loc[primary['measure'] == f'{role}_clutch (quartile)', 'matches_0.70'].iloc[0]
        b = secondary.loc[secondary['role'] == role, 'matches_star'].iloc[0]
        ratio = (max(a, b) / min(a, b)) if (a > 0 and b > 0) else np.nan
        cons[role] = {'prophecy_matches': a, 'shrinkage_matches': b, 'ratio': ratio,
                      'within_factor_3': bool(ratio <= 3) if not np.isnan(ratio) else None}
        print(f"  CONSISTENCY {role}: prophecy ~{a:.0f} vs shrinkage ~{b:.0f} matches "
              f"(ratio {ratio:.2f}) -> {'within 3x' if cons[role]['within_factor_3'] else 'DIFFER >3x'}")

    primary.to_csv(os.path.join(OUT_DIR, f'{tour}_data_requirement.csv'), index=False)
    secondary.to_csv(os.path.join(OUT_DIR, f'{tour}_data_requirement_shrinkage.csv'), index=False)
    return primary, secondary, cons, med_matches


# =============================================================================
# Analysis 3
# =============================================================================

def analysis3(tour, obj, arrs, full):
    print(f"\n--- Analysis 3: bootstrap ({tour.upper()}, B={B_BOOT}) ---")
    rng = np.random.default_rng(SEED)
    players = list(arrs.keys())
    measures = ['serve_clutch', 'return_clutch', 'blr']

    # Pre-index each player's points by match for fast resampling.
    idx = {}
    for p in players:
        idx[p] = {}
        for role in ('serve', 'return'):
            m, lev, won = arrs[p][role]
            order = np.argsort(m, kind='stable')
            m_s, lev_s, won_s = m[order], lev[order], won[order]
            uniq, starts = np.unique(m_s, return_index=True)
            ends = np.append(starts[1:], len(m_s))
            idx[p][role] = (uniq, starts, ends, lev_s, won_s)
        # a player's matches = union across roles
        idx[p]['matches'] = np.union1d(idx[p]['serve'][0], idx[p]['return'][0])

    def gather(p, role, chosen):
        uniq, starts, ends, lev_s, won_s = idx[p][role]
        pos = np.searchsorted(uniq, chosen)
        hit = (pos < len(uniq)) & (uniq[np.minimum(pos, len(uniq) - 1)] == chosen)
        segs = [np.arange(starts[i], ends[i]) for i in pos[hit]]
        if not segs:
            return np.array([]), np.array([])
        sel = np.concatenate(segs)
        return lev_s[sel], won_s[sel]

    # Identity replicate must reproduce point estimates.
    ident = {}
    for p in players:
        ls, ws = gather(p, 'serve', idx[p]['matches'])
        lr_, wr = gather(p, 'return', idx[p]['matches'])
        ident[p] = all_measures(ls, ws, lr_, wr)
    ident = pd.DataFrame(ident).T
    max_id_diff = max((ident[m].astype(float) - full[m].astype(float)).abs().max() for m in measures)
    identity_ok = bool(max_id_diff < 1e-12)
    print(f"  SANITY identity replicate reproduces point estimates: max |diff|={max_id_diff:.1e} -> "
          f"{'PASS' if identity_ok else 'FAIL'}")

    boot = {m: np.full((B_BOOT, len(players)), np.nan) for m in measures}
    t0 = time.time()
    for b in range(B_BOOT):
        for j, p in enumerate(players):
            ms = idx[p]['matches']
            chosen = rng.choice(ms, size=len(ms), replace=True)
            ls, ws = gather(p, 'serve', chosen)
            lr_, wr = gather(p, 'return', chosen)
            res = all_measures(ls, ws, lr_, wr)
            for m in measures:
                boot[m][b, j] = res[m]
        if b == 9:
            print(f"  ~{(time.time() - t0) / 10 * B_BOOT / 60:.0f} min estimated for {B_BOOT} replicates")
    print(f"  bootstrap done in {(time.time() - t0) / 60:.1f} min")

    summary_rows = []
    pool_stats = {}
    for m in measures:
        est = full[m].astype(float).reindex(players).values
        draws = boot[m]
        # rank 1 = most clutch (highest value); NaN ranked last
        ranks = (-np.nan_to_num(draws, nan=-np.inf)).argsort(axis=1).argsort(axis=1) + 1
        est_rank = pd.Series(est, index=players).rank(ascending=False, method='first')
        lo_s, hi_s = np.nanpercentile(draws, [2.5, 97.5], axis=0)
        lo_r, hi_r = np.percentile(ranks, [2.5, 97.5], axis=0)
        mean_s = np.nanmean(draws, axis=0)
        pool_mean = np.nanmean(est)
        for j, p in enumerate(players):
            summary_rows.append({'measure': m, 'player': p, 'estimate': est[j],
                                 'boot_mean': mean_s[j], 'score_lo': lo_s[j], 'score_hi': hi_s[j],
                                 'rank_est': int(est_rank[p]), 'rank_lo': lo_r[j], 'rank_hi': hi_r[j],
                                 'excludes_pool_mean': bool(lo_s[j] > pool_mean or hi_s[j] < pool_mean)})
        width = hi_r - lo_r
        top10 = est_rank.sort_values().index[:10]
        top10_in20 = sum(1 for p in top10 if hi_r[players.index(p)] <= 20)
        bias = np.nanmax(np.abs(mean_s - est))
        pool_stats[m] = {'median_rank_width': float(np.median(width)),
                         'n_excluding_pool_mean': int(sum(r['excludes_pool_mean'] for r in summary_rows
                                                          if r['measure'] == m)),
                         'n_players': len(players),
                         'top10_with_interval_within_top20': int(top10_in20),
                         'max_abs_bias': float(bias)}
        print(f"  {m:14s} median 95% rank-interval width = {np.median(width):.0f} ranks; "
              f"{pool_stats[m]['n_excluding_pool_mean']}/{len(players)} exclude pool mean; "
              f"top-10 within top-20: {top10_in20}/10; max |boot mean - est| = {bias:.4f}")

    summ = pd.DataFrame(summary_rows)
    summ.to_csv(os.path.join(OUT_DIR, f'{tour}_bootstrap_intervals.csv'), index=False)
    np.savez_compressed(os.path.join(OUT_DIR, f'{tour}_bootstrap_draws.npz'),
                        players=np.array(players), **boot)
    named = summ[summ['player'].isin(NAMED)]
    for _, r in named.iterrows():
        print(f"    {r['player']:16s} {r['measure']:13s} est={r['estimate']:+.4f} "
              f"[{r['score_lo']:+.4f}, {r['score_hi']:+.4f}]  rank {r['rank_est']} "
              f"[{r['rank_lo']:.0f}-{r['rank_hi']:.0f}]")
    return pool_stats, identity_ok


# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-entropy', action='store_true')
    ap.add_argument('--tours', default='atp,wta')
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    report = {}
    for tour in args.tours.split(','):
        print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
        obj = build_point_table(tour)
        arrs = player_arrays(obj['pts'], obj['players'])
        rel1, checks1, cv, full = analysis1(tour, obj, arrs, args.skip_entropy)
        prim, sec, cons, med = analysis2(tour, obj, rel1)
        pool_stats, identity_ok = analysis3(tour, obj, arrs, full)
        report[tour] = {
            'analysis1_reliability': rel1, 'analysis1_sanity': checks1,
            'convergent_validity': cv,
            'analysis2_median_matches': med,
            'analysis2_primary': prim.to_dict(orient='records'),
            'analysis2_secondary': sec.to_dict(orient='records'),
            'analysis2_consistency': cons,
            'analysis3_pool': pool_stats, 'analysis3_identity_ok': identity_ok,
        }
    with open(os.path.join(OUT_DIR, 'applications_results.json'), 'w') as fh:
        json.dump(report, fh, indent=2, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else float(o) if isinstance(o, (np.floating,)) else str(o))
    print(f"\nWrote {OUT_DIR}/applications_results.json")


if __name__ == '__main__':
    main()
