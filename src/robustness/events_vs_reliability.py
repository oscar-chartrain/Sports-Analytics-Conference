"""Descriptive check: is an outcome's reliability related to how many events per player it rests on?

For each outcome, the median over players of the number of events in the top and bottom leverage quartiles (serve
points, return points, rally-decided points, or shots of the relevant kind), next to the committed median random-split
reliability (allshots_reliability.csv). Not a pre-registered test; it is a description that qualifies Section 4.4.

    python src/robustness/events_vs_reliability.py
Writes results/applications/events_vs_reliability.csv
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

import applications_analyses as aa
import all_shots_analyses as asa

OUTS = ['serve_clutch', 'return_clutch', 'R1_rally_point', 'R2_error_all', 'R4_error_forehand',
        'R5_error_backhand', 'R6_error_slice', 'R7_error_net', 'R9_ace']


def main():
    ref = pd.read_csv(os.path.join(aa.OUT_DIR, 'allshots_reliability.csv'))
    out = []
    for tour in ('atp', 'wta'):
        players, matches, half_map, summary, pts = aa.load_tour(tour)
        tab = asa.build_point_table(tour, matches, half_map, pts)
        asa.parity_check(tab)
        sorted_ids = np.array(sorted(half_map.keys()))
        gm = np.searchsorted(sorted_ids, tab['match_id'].values)
        arrs = asa.player_arrays(tab, players, gm)
        rows = {k: [] for k in OUTS}
        for p in players:
            d = arrs[p]
            keep = ~np.isnan(d['lev'])
            v = {k: x[keep] for k, x in d.items()}
            q25, q75 = np.quantile(v['lev'], [0.25, 0.75])
            tb = (v['lev'] >= q75) | (v['lev'] <= q25)
            sv = v['is_serve']
            rows['serve_clutch'].append((tb & sv).sum())
            rows['return_clutch'].append((tb & ~sv).sum())
            rows['R1_rally_point'].append((tb & v['rally']).sum())
            rows['R2_error_all'].append(v['shots'][tb].sum())
            rows['R4_error_forehand'].append(v['sh_forehand'][tb].sum())
            rows['R5_error_backhand'].append(v['sh_backhand'][tb].sum())
            rows['R6_error_slice'].append(v['sh_slice'][tb].sum())
            rows['R7_error_net'].append(v['sh_net'][tb].sum())
            rows['R9_ace'].append((tb & sv).sum())
        r = ref[ref.tour == tour].set_index('outcome')['median']
        df = pd.DataFrame({'tour': tour, 'outcome': OUTS,
                           'median_events_top_bottom': [float(np.median(rows[k])) for k in OUTS],
                           'median_reliability': [r.get(k, np.nan) for k in OUTS]})
        c = df.dropna()
        rho = c['median_events_top_bottom'].corr(c['median_reliability'], method='spearman')
        df['spearman_events_reliability'] = rho
        out.append(df)
        print(f"{tour}: Spearman correlation of events with reliability across {len(c)} outcomes {rho:+.2f}")
        print(df.round(2).to_string(index=False))
    pd.concat(out).to_csv(os.path.join(aa.OUT_DIR, 'events_vs_reliability.csv'), index=False)
    print('=== RUN END')


if __name__ == '__main__':
    main()
