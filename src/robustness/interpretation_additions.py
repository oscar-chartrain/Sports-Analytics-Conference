"""
interpretation_additions.py -- descriptive additions that translate the committed results into tennis terms
(plan: docs/combined/interpretation_additions_plan.md, written 2026-11-20 before this script existed).

  A. empirical repeat check: share of players in the top quartile on half A who are again in the top quartile on half B,
     over 1,000 random balanced splits, next to the normal-model projection for records of the same (half) length
  B. serve and return points per match in the top leverage quartile, and what one true SD of clutch is worth in points
  C. the spread of ordinary ability (overall serve- and return-point win rate) next to the true clutch spread
  D. top-quartile points per player over the charted record and the binomial standard error of a rate on that many

Validation first (aborts before writing): hitter parity and the paper's serve and return original-split reliabilities
reproduced within 0.001 (as in all_shots_analyses.py).

    python src/robustness/interpretation_additions.py [--splits N]
Writes results/applications/interpretation_repeat_check.csv and interpretation_context.csv
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

import applications_analyses as aa
import all_shots_analyses as asa
from label_accuracy import accuracy

SEED = 20261124
N_SPLITS = 1000
OUTS = ['serve_clutch', 'return_clutch', 'R2_error_all', 'R3_winner_all', 'R4_error_forehand']
OUT_NAMES = {'serve_clutch': 'Serve quartile clutch', 'return_clutch': 'Return quartile clutch',
             'R2_error_all': 'Unforced-error clutch, all shots', 'R3_winner_all': 'Winner clutch, all shots',
             'R4_error_forehand': 'Error clutch, forehand'}


def top_share(va, vb):
    ok = ~np.isnan(va) & ~np.isnan(vb)
    a, b = va[ok], vb[ok]
    if len(a) < 20:
        return np.nan, np.nan
    ta = a >= np.quantile(a, 0.75)
    tb = b >= np.quantile(b, 0.75)
    r = np.corrcoef(a, b)[0, 1]
    return tb[ta].mean(), r


def player_counts(arrs, players):
    rows = []
    for p in players:
        d = arrs[p]
        keep = ~np.isnan(d['lev'])
        v = {k: x[keep] for k, x in d.items()}
        n_matches = len(np.unique(v['gm']))
        rec = {'player': p, 'matches': n_matches}
        for role, sel in (('serve', v['is_serve']), ('return', ~v['is_serve'])):
            lev = v['lev'][sel]
            won = v['won'][sel]
            q75 = np.quantile(lev, 0.75)
            n_top = int((lev >= q75).sum())
            pwin = float(won.mean())
            rec[f'{role}_points'] = int(sel.sum())
            rec[f'{role}_top_points'] = n_top
            rec[f'{role}_top_per_match'] = n_top / n_matches
            rec[f'{role}_win_rate'] = pwin
            rec[f'{role}_binom_var'] = pwin * (1 - pwin) / sel.sum()
        rows.append(rec)
    return pd.DataFrame(rows)


def run_tour(tour, n_splits, spread):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    tab = asa.build_point_table(tour, matches, half_map, pts)
    asa.parity_check(tab)
    sorted_ids = np.array(sorted(half_map.keys()))
    gm = np.searchsorted(sorted_ids, tab['match_id'].values)
    arrs = asa.player_arrays(tab, players, gm)
    orig_assign = np.array([half_map[m] == 'A' for m in sorted_ids])

    # ---- validation (as in all_shots_analyses.py) ----
    va, vb = asa.half_values(arrs, players, [orig_assign[arrs[p]['gm']] for p in players])
    orig = asa.split_rel(va, vb)
    for k, ref in (('serve_clutch', aa.DOC_RELIABILITY[(tour, 'serve')]), ('return_clutch', aa.DOC_RELIABILITY[(tour, 'return')])):
        d = abs(orig[asa.OUTCOMES.index(k)] - ref)
        print(f"VALIDATION {k}: new {orig[asa.OUTCOMES.index(k)]:+.4f} reported {ref:+.4f} diff {d:.5f}")
        if d > 0.001:
            raise SystemExit(f"{tour.upper()}: validation failed for {k}; stop and investigate.")
    print("VALIDATION PASS")

    # ---- A. empirical repeat check ----
    idx = [asa.OUTCOMES.index(k) for k in OUTS]
    rng = np.random.default_rng(SEED)
    n_m = len(sorted_ids)
    emp = np.full((n_splits, len(OUTS)), np.nan)
    mod = np.full((n_splits, len(OUTS)), np.nan)
    for s in range(n_splits):
        order = rng.permutation(n_m)
        assign = np.zeros(n_m, dtype=int)
        assign[order[1::2]] = 1
        in_a_all = assign == 0
        va, vb = asa.half_values(arrs, players, [in_a_all[arrs[p]['gm']] for p in players])
        for j, k in enumerate(idx):
            share, r = top_share(va[:, k], vb[:, k])
            emp[s, j] = share
            if not np.isnan(r):
                mod[s, j] = accuracy(max(r, 0.0))[2]
        if (s + 1) % 100 == 0:
            print(f"  ...{s + 1}/{n_splits} splits")
    rep_rows = []
    for j, k in enumerate(OUTS):
        e, m = emp[:, j][~np.isnan(emp[:, j])], mod[:, j][~np.isnan(mod[:, j])]
        row = {'tour': tour, 'outcome': k, 'label': OUT_NAMES[k], 'n_splits_valid': len(e),
               'empirical_median': np.median(e), 'empirical_p2_5': np.percentile(e, 2.5), 'empirical_p97_5': np.percentile(e, 97.5),
               'model_median': np.median(m), 'model_p2_5': np.percentile(m, 2.5), 'model_p97_5': np.percentile(m, 97.5),
               'empirical_within_model_range': bool(np.percentile(m, 2.5) <= np.median(e) <= np.percentile(m, 97.5))}
        rep_rows.append(row)
        print(f"{OUT_NAMES[k]:36s} empirical {row['empirical_median']:.3f} [{row['empirical_p2_5']:.3f}, {row['empirical_p97_5']:.3f}]"
              f"   model {row['model_median']:.3f} [{row['model_p2_5']:.3f}, {row['model_p97_5']:.3f}]")

    # ---- B, C, D. points per match, ability spread, noise ----
    pc = player_counts(arrs, players)
    ctx = []
    for role in ('serve', 'return'):
        sd_true = float(spread.loc[(tour, role), 'true_sd_var_pts'])
        top_pm = float(pc[f'{role}_top_per_match'].median())
        raw_sd = float(pc[f'{role}_win_rate'].std(ddof=1) * 100)
        noise_var = float(pc[f'{role}_binom_var'].mean())
        corr_var = pc[f'{role}_win_rate'].var(ddof=1) - noise_var
        corr_sd = float(np.sqrt(max(corr_var, 0)) * 100)
        n_top_med = float(pc[f'{role}_top_points'].median())
        p_med = float(pc[f'{role}_win_rate'].median())
        se_top = float(np.sqrt(p_med * (1 - p_med) / n_top_med) * 100)
        ctx.append({'tour': tour, 'role': role, 'n_players': len(pc), 'median_matches': float(pc['matches'].median()),
                    'top_quartile_points_per_match_median': top_pm,
                    'top_quartile_points_per_player_median': n_top_med,
                    'true_clutch_sd_pp': sd_true,
                    'points_per_match_per_true_sd': sd_true / 100.0 * top_pm,
                    'ability_sd_raw_pp': raw_sd, 'ability_sd_noise_corrected_pp': corr_sd,
                    'binomial_se_one_quartile_rate_pp': se_top,
                    'planted_spread_pp': 4.0})
    print(pd.DataFrame(ctx).round(3).to_string(index=False))
    return pd.DataFrame(rep_rows), pd.DataFrame(ctx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--splits', type=int, default=N_SPLITS)
    n_splits = ap.parse_args().splits
    spread = pd.read_csv(os.path.join(aa.OUT_DIR, 'ext_c_true_spread.csv')).set_index(['tour', 'role'])
    reps, ctxs = [], []
    for tour in ('atp', 'wta'):
        r, c = run_tour(tour, n_splits, spread)
        reps.append(r)
        ctxs.append(c)
    pd.concat(reps).to_csv(os.path.join(aa.OUT_DIR, 'interpretation_repeat_check.csv'), index=False)
    pd.concat(ctxs).to_csv(os.path.join(aa.OUT_DIR, 'interpretation_context.csv'), index=False)
    print('=== RUN END')


if __name__ == '__main__':
    main()
