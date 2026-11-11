"""
applications_extensions.py -- the three robustness extensions pre-registered in
docs/combined/applications_extensions_preregistration.md (written 2026-11-11,
before this script existed):

  A. Reliability of the clutch measures across 1,000 random half-splits, not
     just the one interleaved split used everywhere else.
  B. Reliability of break-point conversion / save rates, raw and as a
     differential against each player's non-break-point baseline.
  C. The true between-player spread of clutch (variance decomposition plus an
     independent covariance estimate), with player-bootstrap intervals.

Reuses applications_analyses.py unchanged (cached point table, RolePoints
weighted-quartile engine, split-half helpers). Needs that script's cache
(results/{tour}/cache_applications_{tour}.pkl) and the raw MCP files.

Analysis A's validation step aborts the script (nothing written) if the
original alternating assignment, pushed through the new vectorised code, does
not reproduce results/applications/a1_blr_reliability.csv within 0.001.

Usage: python3 applications_extensions.py [--splits N]
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse
import pickle

import numpy as np
import pandas as pd
from scipy import stats

import applications_analyses as aa
import formulas as f
import parsing as pr
import split_half_reliability as shr

SEED = 20261111
N_SPLITS = 1000
N_BOOT = 2000
OUT_DIR = aa.OUT_DIR
MEASURES = ['serve_clutch', 'return_clutch', 'lr_serve', 'lr_return', 'blr', 'pooled_lr']
LABELS = {'serve_clutch': 'Serve quartile clutch', 'return_clutch': 'Return quartile clutch',
          'lr_serve': 'LR serve', 'lr_return': 'LR return',
          'blr': 'BLR (faithful, primary)', 'pooled_lr': 'Pooled LR'}


# =============================================================================
# ANALYSIS A: RANDOM SPLITS
# =============================================================================

def lr_parts(rp, w):
    wf = w[rp.mi].astype(float)
    n_won = wf @ rp.won
    n_lost = wf.sum() - n_won
    return wf @ rp.lev_won, n_won, wf @ rp.lev_lost, n_lost


def half_vectors(role_points, w):
    """Six measures for one player on the match subset given by weight vector w."""
    sp, rp = role_points
    s_score, lr_s = sp.stats(w)
    r_score, lr_r = rp.stats(w)
    a = lr_parts(sp, w)
    b = lr_parts(rp, w)
    pooled = ((a[0] + b[0]) / (a[1] + b[1])) / ((a[2] + b[2]) / (a[3] + b[3]))
    return [s_score, r_score, lr_s, lr_r, (lr_s + lr_r) / 2, pooled]


def split_reliability(vals_a, vals_b):
    """vals_*: (n_players, n_measures). Returns SB reliability per measure."""
    out = []
    for k in range(vals_a.shape[1]):
        r = np.corrcoef(vals_a[:, k], vals_b[:, k])[0, 1]
        out.append(f.spearman_brown(r))
    return np.array(out)


def analysis_a(tour, players, frames, half_map, n_splits):
    print(f"\n{'=' * 70}\nANALYSIS A -- {tour.upper()}: reliability across {n_splits} random splits\n{'=' * 70}")
    sorted_ids = sorted(half_map.keys())
    gindex = {m: i for i, m in enumerate(sorted_ids)}
    n_matches = len(sorted_ids)

    rps, gidx = [], []
    for p in players:
        ids, midx = aa.player_matches(frames[p])
        rps.append((aa.RolePoints(frames[p]['serve'], midx), aa.RolePoints(frames[p]['return'], midx)))
        gidx.append(np.array([gindex[m] for m in ids]))

    def reliabilities(assign):
        va = np.zeros((len(players), len(MEASURES)))
        vb = np.zeros((len(players), len(MEASURES)))
        for j in range(len(players)):
            in_a = (assign[gidx[j]] == 0).astype(float)
            va[j] = half_vectors(rps[j], in_a)
            vb[j] = half_vectors(rps[j], 1.0 - in_a)
        return split_reliability(va, vb)

    # ---- validation: original assignment through the new code -------------
    orig_assign = np.array([0 if half_map[m] == 'A' else 1 for m in sorted_ids])
    orig = reliabilities(orig_assign)
    ref = pd.read_csv(os.path.join(OUT_DIR, 'a1_blr_reliability.csv'))
    ref = ref[ref['tour'] == tour].set_index('measure')['r_full']
    worst = 0.0
    for k, m in enumerate(MEASURES):
        d = abs(orig[k] - ref[LABELS[m]])
        worst = max(worst, d)
        print(f"VALIDATION {LABELS[m]:26s} new code {orig[k]:+.4f}  reported {ref[LABELS[m]]:+.4f}  diff {d:.5f}")
    if worst > 0.001:
        raise SystemExit(f"{tour.upper()}: Analysis A validation failed (max diff {worst:.4f}); stop and investigate.")
    print("VALIDATION PASS: original assignment reproduces every reported reliability within 0.001")

    rng = np.random.default_rng(SEED)
    draws = np.zeros((n_splits, len(MEASURES)))
    for s in range(n_splits):
        order = rng.permutation(n_matches)
        assign = np.zeros(n_matches, dtype=int)
        assign[order[1::2]] = 1  # alternate positions of the shuffled list
        draws[s] = reliabilities(assign)
        if (s + 1) % 200 == 0:
            print(f"  ...{s + 1}/{n_splits} splits")

    rows = []
    for k, m in enumerate(MEASURES):
        d = draws[:, k]
        lo, hi = np.percentile(d, [2.5, 97.5])
        row = {'tour': tour, 'measure': LABELS[m], 'original_split': orig[k], 'median': np.median(d),
               'p2_5': lo, 'p97_5': hi, 'share_below_070': float((d < 0.70).mean()),
               'original_in_range': bool(lo <= orig[k] <= hi), 'n_splits': n_splits}
        rows.append(row)
        print(f"{LABELS[m]:26s} original {orig[k]:+.3f}  median {row['median']:+.3f}  "
              f"95% range [{lo:+.3f}, {hi:+.3f}]  share<0.70: {row['share_below_070']:.1%}  "
              f"original typical: {'yes' if row['original_in_range'] else 'NO'}")
    return pd.DataFrame(rows)


# =============================================================================
# ANALYSIS B: BREAK-POINT RATES
# =============================================================================

STANDARD_SITS = {'normal', 'approaching_break_point', 'deuce', 'game_point_server'}


def load_categories(tour, pts):
    """Per-point category: 'bp', 'base' or 'other' (tiebreak / unparsed),
    aligned positionally with the cached point table."""
    cache_path = os.path.join(aa.REPO_ROOT, 'results', tour, f'cache_bp_{tour}.pkl')
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as fh:
            return pickle.load(fh)
    players = shr.load_pool(tour)
    matches, points = shr.load_raw(tour)
    half_map, _ = shr.split_matches(matches, players)
    rel = points[points['match_id'].isin(set(half_map.keys()))].reset_index(drop=True)
    if len(rel) != len(pts) or not (rel['match_id'].values == pts['match_id'].values).all():
        raise SystemExit(f"{tour.upper()}: raw points do not align with the cached point table")
    print(f"{tour.upper()}: classifying {len(rel):,} points for break-point status (slow)...")
    cats = []
    for pts_str, svr in zip(rel['Pts'].tolist(), rel['Svr'].tolist()):
        sit = pr.get_game_situation(pts_str, svr)
        if sit == 'break_point':
            cats.append('bp')
        elif sit in STANDARD_SITS:
            cats.append('base')
        else:
            cats.append('other')
    cats = np.array(cats)
    with open(cache_path, 'wb') as fh:
        pickle.dump(cats, fh)
    return cats


def bp_table(pts, players, half_label=None):
    """Per player and role: BP rate, baseline rate, differential, n_bp."""
    d = pts if half_label is None else pts[pts['half'] == half_label]
    out = {}
    for role in ('serve', 'return'):
        if role == 'serve':
            player, won = d['server'], d['server_won_point']
        else:
            player, won = d['returner'], 1 - d['server_won_point']
        t = pd.DataFrame({'player': player, 'cat': d['cat'], 'won': won})
        t = t[t['player'].isin(players) & t['cat'].isin(['bp', 'base'])]
        g = t.groupby(['player', 'cat'])['won'].agg(['mean', 'size']).unstack('cat')
        res = pd.DataFrame(index=g.index)
        res['bp_rate'] = g[('mean', 'bp')]
        res['base_rate'] = g[('mean', 'base')]
        res['n_bp'] = g[('size', 'bp')]
        res['diff'] = res['bp_rate'] - res['base_rate']
        out[role] = res
    return out


def analysis_b(tour, players, pts):
    print(f"\n{'=' * 70}\nANALYSIS B -- {tour.upper()}: break-point conversion and save rates\n{'=' * 70}")
    ta, tb, tf = bp_table(pts, players, 'A'), bp_table(pts, players, 'B'), bp_table(pts, players)
    rows, extra = [], []
    for role in ('serve', 'return'):
        name = 'BP save (serve)' if role == 'serve' else 'BP conversion (return)'
        a, b = ta[role], tb[role]
        ok = (a['n_bp'] >= aa.MIN_OBS) & (b['n_bp'] >= aa.MIN_OBS)
        ok = ok.reindex(players).fillna(False)
        n_excl = int((~ok).sum())
        keep = [p for p in players if ok[p]]
        print(f"{name}: players excluded by the 30-break-point floor: {n_excl}; "
              f"median break points per half {int(min(a.loc[keep, 'n_bp'].median(), b.loc[keep, 'n_bp'].median()))}")
        for label, col in ((f'{name}, raw rate', 'bp_rate'), (f'{name}, differential vs baseline', 'diff')):
            r = aa.split_half_with_ci(a.loc[keep, col], b.loc[keep, col])
            print(f"  {label:48s} n={r['n']:3d}  r_half={r['r_half']:+.4f}  SB={r['r_full']:.4f}  "
                  f"95% CI [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]")
            rows.append({'tour': tour, 'measure': label, 'excluded': n_excl, **r})
        full = tf[role].reindex(keep)
        r_rb = stats.pearsonr(full['bp_rate'], full['base_rate'])[0]
        print(f"  full-sample r between raw BP rate and non-BP baseline rate across players: {r_rb:+.3f}")
        extra.append({'tour': tour, 'role': role, 'r_raw_vs_baseline': r_rb,
                      'mean_bp_rate': full['bp_rate'].mean(), 'mean_base_rate': full['base_rate'].mean()})
    return pd.DataFrame(rows), pd.DataFrame(extra)


# =============================================================================
# ANALYSIS C: TRUE SPREAD
# =============================================================================

def spread_stats(raw, var_i, cov_ab):
    tau2 = max(0.0, raw.var(ddof=1) - var_i.mean())
    return tau2, cov_ab


def analysis_c(tour, players, summary):
    print(f"\n{'=' * 70}\nANALYSIS C -- {tour.upper()}: true spread of clutch\n{'=' * 70}")
    rng = np.random.default_rng(SEED)
    s = summary.set_index('player').reindex(players)
    half = pd.read_csv(os.path.join(aa.FIG_DIR, f'split_half_raw_{tour}.csv')).set_index('player').reindex(players)
    rows = []
    for role in ('serve', 'return'):
        ok = s[f'{role}_clutch_p65_sufficient'].astype(bool) & half[f'{role}_clutch_a'].notna() & half[f'{role}_clutch_b'].notna()
        raw = s.loc[ok, f'{role}_clutch_p65'].to_numpy()
        var_i = (0.25 * (1.0 / s.loc[ok, f'n_{role}_high_leverage'] + 1.0 / s.loc[ok, f'n_{role}_low_leverage'])).to_numpy()
        ha = half.loc[ok, f'{role}_clutch_a'].to_numpy()
        hb = half.loc[ok, f'{role}_clutch_b'].to_numpy()
        n = len(raw)

        def estimates(idx):
            tau2 = max(0.0, raw[idx].var(ddof=1) - var_i[idx].mean())
            cov = np.cov(ha[idx], hb[idx], ddof=1)[0, 1]
            return tau2, cov

        tau2, cov = estimates(np.arange(n))
        boot = np.array([estimates(rng.integers(0, n, n)) for _ in range(N_BOOT)])
        sd_var = np.sqrt(tau2)
        sd_cov = np.sqrt(cov) if cov > 0 else 0.0
        noise_sd = np.sqrt(var_i.mean())
        se_typical = np.sqrt(var_i).mean()
        snr = tau2 / var_i.mean()
        lo_v, hi_v = np.sqrt(np.percentile(boot[:, 0], [2.5, 97.5]))
        lo_c, hi_c = np.sqrt(np.clip(np.percentile(boot[:, 1], [2.5, 97.5]), 0, None))
        ratio = max(sd_var, sd_cov) / min(sd_var, sd_cov) if min(sd_var, sd_cov) > 0 else np.inf
        print(f"{role:7s} n={n}  true SD (variance decomposition) = {100 * sd_var:.2f} pts "
              f"[{100 * lo_v:.2f}, {100 * hi_v:.2f}]   true SD (half-split covariance) = {100 * sd_cov:.2f} pts "
              f"[{100 * lo_c:.2f}, {100 * hi_c:.2f}]")
        print(f"        noise SD {100 * noise_sd:.2f} pts; typical per-player SE {100 * se_typical:.2f} pts; "
              f"signal-to-noise {snr:.2f}; estimators differ by factor {ratio:.2f} "
              f"({'within' if ratio <= 2 else 'OUTSIDE'} the pre-registered factor of 2)")
        if lo_v <= 0.0 or lo_c <= 0.0:
            print("        a bootstrap interval reaches zero: 'no detectable stable difference' for this estimator")
        rows.append({'tour': tour, 'role': role, 'n': n, 'true_sd_var_pts': 100 * sd_var,
                     'true_sd_var_lo': 100 * lo_v, 'true_sd_var_hi': 100 * hi_v,
                     'true_sd_cov_pts': 100 * sd_cov, 'true_sd_cov_lo': 100 * lo_c, 'true_sd_cov_hi': 100 * hi_c,
                     'noise_sd_pts': 100 * noise_sd, 'typical_se_pts': 100 * se_typical,
                     'snr': snr, 'estimator_ratio': ratio})
    return pd.DataFrame(rows)


# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=N_SPLITS)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    res_a, res_b, res_b2, res_c = [], [], [], []
    for tour in ('atp', 'wta'):
        players, matches, half_map, summary, pts = aa.load_tour(tour, use_cache=True)
        frames = aa.role_frames(pts, players)
        res_a.append(analysis_a(tour, players, frames, half_map, args.splits))
        pts = pts.copy()
        pts['cat'] = load_categories(tour, pts)
        b1, b2 = analysis_b(tour, players, pts)
        res_b.append(b1)
        res_b2.append(b2)
        res_c.append(analysis_c(tour, players, summary))

    pd.concat(res_a).to_csv(os.path.join(OUT_DIR, 'ext_a_random_splits.csv'), index=False)
    pd.concat(res_b).to_csv(os.path.join(OUT_DIR, 'ext_b_breakpoint_reliability.csv'), index=False)
    pd.concat(res_b2).to_csv(os.path.join(OUT_DIR, 'ext_b_breakpoint_skill_overlap.csv'), index=False)
    pd.concat(res_c).to_csv(os.path.join(OUT_DIR, 'ext_c_true_spread.csv'), index=False)
    print(f"\nWrote outputs to {OUT_DIR}")


if __name__ == '__main__':
    main()
