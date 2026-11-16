"""
cluster_bootstrap_ranks.py -- match-level cluster bootstrap pre-registered in
docs/combined/cluster_bootstrap_preregistration.md (written 2026-11-16, before
this script existed).

Resamples the global list of matches (B = 2,000, seed 20261116) so that a match
between two pool players carries the same draw count for both, then recomputes
serve clutch, return clutch and BLR for every player with the same weighted
quartile code as the player-level bootstrap in applications_analyses.py, and
ranks players inside each replicate.

Outputs: results/applications/a3c_cluster_bootstrap_players.csv and
a3c_cluster_bootstrap_summary.csv. Usage: python src/robustness/cluster_bootstrap_ranks.py [--boot N]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse

import numpy as np
import pandas as pd

import applications_analyses as aa

SEED = 20261116


def run_tour(tour, n_boot):
    print(f"\n{'=' * 70}\n{tour.upper()}: match-level cluster bootstrap (B={n_boot}, seed {SEED})\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    frames = aa.role_frames(pts, players)
    s = summary.set_index('player')
    sorted_ids = sorted(half_map.keys())
    gindex = {m: i for i, m in enumerate(sorted_ids)}
    n_m = len(sorted_ids)

    sps, rps, gidx, point = [], [], [], {m: [] for m in ('serve', 'return', 'blr')}
    for p in players:
        ids, midx = aa.player_matches(frames[p])
        sp = aa.RolePoints(frames[p]['serve'], midx)
        rp = aa.RolePoints(frames[p]['return'], midx)
        ones = np.ones(len(ids))
        s0, lr_s0 = sp.stats(ones)
        r0, lr_r0 = rp.stats(ones)
        if abs(s0 - s.loc[p, 'serve_clutch_p65']) > 1e-12 or abs(r0 - s.loc[p, 'return_clutch_p65']) > 1e-12:
            raise SystemExit(f"Sanity check failed for {p}: unit weights do not reproduce the pipeline score.")
        sps.append(sp); rps.append(rp)
        gidx.append(np.array([gindex[m] for m in ids]))
        point['serve'].append(s0); point['return'].append(r0); point['blr'].append((lr_s0 + lr_r0) / 2)
    print("SANITY unit weights reproduce every pipeline score: PASS")

    rng = np.random.default_rng(SEED)
    boot = {m: np.full((n_boot, len(players)), np.nan) for m in point}
    for b in range(n_boot):
        counts = rng.multinomial(n_m, np.full(n_m, 1.0 / n_m))
        for j in range(len(players)):
            cb = counts[gidx[j]]
            if cb.sum() == 0:
                continue
            sb, lr_sb = sps[j].stats(cb)
            rb, lr_rb = rps[j].stats(cb)
            boot['serve'][b, j], boot['return'][b, j], boot['blr'][b, j] = sb, rb, (lr_sb + lr_rb) / 2
        if (b + 1) % 200 == 0:
            print(f"  ...{b + 1}/{n_boot} replicates")

    old = pd.read_csv(os.path.join(aa.OUT_DIR, 'a3_bootstrap_summary.csv'))
    old = old[old['tour'] == tour].set_index('measure')
    summaries, tables = [], []
    for m in ('serve', 'return', 'blr'):
        pt = np.array(point[m])
        mat = boot[m]
        lo, hi = np.nanpercentile(mat, [2.5, 97.5], axis=0)
        ranks = np.argsort(np.argsort(-np.nan_to_num(mat, nan=-np.inf), axis=1), axis=1) + 1
        rlo, rhi = np.percentile(ranks, [2.5, 97.5], axis=0)
        pt_rank = np.argsort(np.argsort(-pt)) + 1
        pool_mean = pt.mean()
        excl = int(((lo > pool_mean) | (hi < pool_mean)).sum())
        top10 = np.argsort(pt_rank)[:10]
        width = float(np.median(rhi - rlo))
        w_old = float(old.loc[m, 'median_rank_width'])
        summaries.append({'tour': tour, 'measure': m, 'median_rank_width_cluster': width,
                          'median_rank_width_player_level': w_old,
                          'relative_change': width / w_old - 1,
                          'n_excluding_pool_mean': excl, 'n_players': len(players),
                          'top10_within_top20': int((rhi[top10] <= 20).sum())})
        print(f"[{m}] median 95% rank width {width:.1f} (player-level {w_old:.1f}, change {width / w_old - 1:+.1%}); "
              f"score intervals excluding pool mean {excl}/{len(players)}")
        tables.append(pd.DataFrame({'tour': tour, 'measure': m, 'player': players, 'score': pt,
                                    'score_lo': lo, 'score_hi': hi, 'rank': pt_rank,
                                    'rank_lo': rlo, 'rank_hi': rhi}))
    players_df = pd.concat(tables, ignore_index=True)
    if tour == 'atp':
        for name in aa.NAMED_ATP:
            for m in ('serve', 'return', 'blr'):
                r = players_df[(players_df['measure'] == m) & (players_df['player'] == name)].iloc[0]
                print(f"  {name:16s} {m:7s} score {r['score']:+.4f} [{r['score_lo']:+.4f}, {r['score_hi']:+.4f}]  "
                      f"rank {int(r['rank']):2d} [{r['rank_lo']:.0f}, {r['rank_hi']:.0f}]")
    return pd.DataFrame(summaries), players_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boot', type=int, default=aa.N_BOOT)
    args = ap.parse_args()
    sums, plays = [], []
    for tour in ('atp', 'wta'):
        a, b = run_tour(tour, args.boot)
        sums.append(a); plays.append(b)
    pd.concat(sums).to_csv(os.path.join(aa.OUT_DIR, 'a3c_cluster_bootstrap_summary.csv'), index=False)
    pd.concat(plays).to_csv(os.path.join(aa.OUT_DIR, 'a3c_cluster_bootstrap_players.csv'), index=False)
    print(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
