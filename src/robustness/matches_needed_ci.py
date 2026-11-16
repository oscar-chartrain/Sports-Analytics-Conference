"""Confidence intervals for the Table 3 'matches needed' figures.

Propagates the 95% CI on the original-split reliability (a1_blr_reliability.csv)
and the 95% range over random splits (ext_a_random_splits.csv) through the
Spearman-Brown prophecy. Read-only on committed outputs; no new data analysis.
A reliability <= 0 means the target is unattainable ('unbounded').
"""
import pandas as pd

MEDIAN_MATCHES = {'atp': 74, 'wta': 64}
TARGET = 0.70
A1 = pd.read_csv('results/applications/a1_blr_reliability.csv')
EXT = pd.read_csv('results/applications/ext_a_random_splits.csv')
MAP = {  # table label -> (a1 measure, ext measure)
    'Serve clutch': ('Serve quartile clutch', 'Serve quartile clutch'),
    'Return clutch': ('Return quartile clutch', 'Return quartile clutch'),
    'BLR': ('BLR (faithful, primary)', None),
}

def need(rho, tour):
    if rho <= 0:
        return None
    k = TARGET * (1 - rho) / (rho * (1 - TARGET))
    return k * MEDIAN_MATCHES[tour]

def fmt(x):
    return 'unbounded' if x is None else f'{x:,.0f}'

ext_names = set(EXT['measure'])
rows = []
for tour in ('atp', 'wta'):
    for label, (a1m, em) in MAP.items():
        a = A1[(A1.tour == tour) & (A1.measure == a1m)].iloc[0]
        r = {'tour': tour, 'measure': label,
             'orig_rho': a.r_full,
             'orig_matches': need(a.r_full, tour),
             'orig_ci_matches_lo': need(a.ci_hi, tour),   # high reliability -> fewer matches
             'orig_ci_matches_hi': need(a.ci_lo, tour)}
        if em is None:
            cand = [n for n in ext_names if 'BLR' in n]
            em = cand[0] if cand else None
        if em is not None:
            e = EXT[(EXT.tour == tour) & (EXT.measure == em)].iloc[0]
            r.update(rs_rho=e['median'], rs_matches=need(e['median'], tour),
                     rs_lo=need(e['p97_5'], tour), rs_hi=need(e['p2_5'], tour))
        rows.append(r)

out = pd.DataFrame(rows)
out.to_csv('results/applications/matches_needed_ci.csv', index=False)
for r in rows:
    print(f"{r['tour'].upper()} {r['measure']:14s} orig rho={r['orig_rho']:.3f} -> {fmt(r['orig_matches'])} "
          f"[{fmt(r['orig_ci_matches_lo'])}, {fmt(r['orig_ci_matches_hi'])}] | "
          f"random-split median rho={r.get('rs_rho', float('nan')):.3f} -> {fmt(r.get('rs_matches'))} "
          f"[{fmt(r.get('rs_lo'))}, {fmt(r.get('rs_hi'))}]")
