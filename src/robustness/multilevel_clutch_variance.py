"""
multilevel_clutch_variance.py -- the direct estimate of true clutch variance
pre-registered in docs/combined/multilevel_clutch_variance_preregistration.md.

For each tour and role (serve, return), on points in each player's own top or
bottom p = 0.65 leverage quartile:
  M1  multilevel linear model, won ~ high with a random intercept and random
      slope on `high` per player; tau = SD of the slope (percentage points),
      95% interval from 200 player-bootstrap refits.
  M2  cluster-robust two-stage estimator: each player's top-minus-bottom
      difference with a match-clustered standard error; tau-squared = variance
      of the differences minus the mean squared standard error (floored at 0),
      95% interval from 2,000 player-bootstrap resamples. Also the implied
      reliability of a career-length score, tau^2 / (tau^2 + mean SE^2).
  LR  likelihood-ratio test of the random slope (ML fits, 50:50 mixture of
      chi-squared with 1 and 2 df).

Writes results/applications/multilevel_clutch_variance.csv.
Usage: python src/robustness/multilevel_clutch_variance.py [--boot-m1 N]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse
import warnings

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

import applications_analyses as aa

SEED = 20261116
LEV = aa.LEV
warnings.filterwarnings('ignore')


def build_long(frames, players, role):
    rows = []
    for p in players:
        d = frames[p][role].dropna(subset=[LEV, 'won'])
        q25, q75 = d[LEV].quantile([0.25, 0.75])
        for flag, sub in ((1, d[d[LEV] >= q75]), (0, d[d[LEV] <= q25])):
            rows.append(pd.DataFrame({'player': p, 'match': sub['match_id'].values,
                                      'high': flag, 'won': sub['won'].values.astype(float)}))
    return pd.concat(rows, ignore_index=True)


def player_stats(df):
    """Per player: top-minus-bottom difference and its binomial and match-clustered SEs."""
    out = []
    for p, d in df.groupby('player', sort=False):
        hi, lo = d[d['high'] == 1], d[d['high'] == 0]
        n_h, n_l = len(hi), len(lo)
        if n_h < 30 or n_l < 30:
            continue
        m_h, m_l = hi['won'].mean(), lo['won'].mean()
        diff = m_h - m_l
        se_bin = np.sqrt(m_h * (1 - m_h) / n_h + m_l * (1 - m_l) / n_l)
        # sandwich over matches: score_m = sum_top(y - m_h)/n_h - sum_bottom(y - m_l)/n_l
        sh = (hi['won'] - m_h).groupby(hi['match'].values).sum() / n_h
        sl = (lo['won'] - m_l).groupby(lo['match'].values).sum() / n_l
        idx = sh.index.union(sl.index)
        s = sh.reindex(idx, fill_value=0.0) - sl.reindex(idx, fill_value=0.0)
        M = len(s)
        se_cl = np.sqrt(M / (M - 1) * (s ** 2).sum()) if M > 1 else np.nan
        out.append((p, diff, se_bin, se_cl))
    return pd.DataFrame(out, columns=['player', 'diff', 'se_bin', 'se_cl'])


def tau_moment(diff, se):
    v = np.var(diff, ddof=1) - np.mean(se ** 2)
    return np.sqrt(max(v, 0.0)), max(v, 0.0)


def fit_m1(df, ml=False):
    m = smf.mixedlm('won ~ high', df, groups='player', re_formula='~high')
    return m.fit(method='lbfgs', reml=not ml)


def tau_m1(res):
    return np.sqrt(max(res.cov_re.loc['high', 'high'], 0.0))


def run(tour, boot_m1):
    print(f"\n{'=' * 70}\n{tour.upper()}\n{'=' * 70}")
    players, matches, half_map, summary, pts = aa.load_tour(tour)
    frames = aa.role_frames(pts, players)
    rows = []
    rng = np.random.default_rng(SEED)
    for role in ('serve', 'return'):
        df = build_long(frames, players, role)
        ps = player_stats(df)
        n_p = len(ps)

        # ---- M2: moment estimator, binomial and match-clustered SEs ----
        diff = ps['diff'].to_numpy()
        tau_b, _ = tau_moment(diff, ps['se_bin'].to_numpy())
        tau_c, v_c = tau_moment(diff, ps['se_cl'].to_numpy())
        mean_se2_c = float(np.mean(ps['se_cl'].to_numpy() ** 2))
        rel_c = v_c / (v_c + mean_se2_c)
        boots = np.zeros(2000)
        rels = np.zeros(2000)
        for b in range(2000):
            idx = rng.integers(0, n_p, n_p)
            t, vv = tau_moment(diff[idx], ps['se_cl'].to_numpy()[idx])
            boots[b] = t
            rels[b] = vv / (vv + np.mean(ps['se_cl'].to_numpy()[idx] ** 2))
        lo2, hi2 = np.percentile(boots, [2.5, 97.5])
        rlo, rhi = np.percentile(rels, [2.5, 97.5])

        # ---- M1: multilevel model ----
        r1 = fit_m1(df)
        t1 = tau_m1(r1)
        # ML fits for the likelihood-ratio test: take the best log-likelihood over optimisers
        # (a single L-BFGS run can stop early on the boundary and give a spuriously low value)
        def best_ml(formula_re):
            best = None
            for method in ('lbfgs', 'powell', 'nm'):
                try:
                    f = smf.mixedlm('won ~ high', df, groups='player', re_formula=formula_re).fit(
                        method=method, reml=False, maxiter=2000)
                    if np.isfinite(f.llf) and (best is None or f.llf > best.llf):
                        best = f
                except Exception:
                    continue
            return best
        ml1 = best_ml('~high')
        ml0 = best_ml('~1')
        lr = max(2 * (ml1.llf - ml0.llf), 0.0)
        p_lr = 0.5 * stats.chi2.sf(lr, 1) + 0.5 * stats.chi2.sf(lr, 2)
        b1 = []
        players_in = ps['player'].tolist()
        grouped = {p: g for p, g in df.groupby('player', sort=False)}
        for b in range(boot_m1):
            pick = rng.integers(0, len(players_in), len(players_in))
            parts = []
            for k, j in enumerate(pick):
                g = grouped[players_in[j]].copy()
                g['player'] = f'{players_in[j]}__{k}'
                parts.append(g)
            try:
                b1.append(tau_m1(fit_m1(pd.concat(parts, ignore_index=True))))
            except Exception:
                continue
            if (b + 1) % 50 == 0:
                print(f"  {role}: ...{b + 1}/{boot_m1} M1 refits")
        lo1, hi1 = (np.percentile(b1, [2.5, 97.5]) if len(b1) > 20 else (np.nan, np.nan))

        row = {'tour': tour, 'role': role, 'n_players': n_p,
               'tau_m1_pp': t1 * 100, 'tau_m1_lo': lo1 * 100, 'tau_m1_hi': hi1 * 100, 'm1_boot_ok': len(b1),
               'tau_m2_binomial_pp': tau_b * 100,
               'tau_m2_cluster_pp': tau_c * 100, 'tau_m2_lo': lo2 * 100, 'tau_m2_hi': hi2 * 100,
               'mean_se_binomial_pp': float(np.sqrt(np.mean(ps['se_bin'] ** 2))) * 100,
               'mean_se_cluster_pp': float(np.sqrt(mean_se2_c)) * 100,
               'implied_reliability': rel_c, 'implied_rel_lo': rlo, 'implied_rel_hi': rhi,
               'lr_stat': lr, 'lr_p': p_lr}
        rows.append(row)
        print(f"{role:6s} M1 tau {t1 * 100:.2f} [{lo1 * 100:.2f}, {hi1 * 100:.2f}]  M2 cluster {tau_c * 100:.2f} "
              f"[{lo2 * 100:.2f}, {hi2 * 100:.2f}] (binomial-SE version {tau_b * 100:.2f})  "
              f"SE bin {row['mean_se_binomial_pp']:.2f} vs cluster {row['mean_se_cluster_pp']:.2f}  "
              f"implied rel {rel_c:.2f} [{rlo:.2f}, {rhi:.2f}]  LR p {p_lr:.4f}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boot-m1', type=int, default=200)
    args = ap.parse_args()
    rows = []
    for tour in ('atp', 'wta'):
        rows += run(tour, args.boot_m1)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(aa.OUT_DIR, 'multilevel_clutch_variance.csv'), index=False)
    print(out.round(3).to_string(index=False))
    print(f"\nWrote outputs to {aa.OUT_DIR}")


if __name__ == '__main__':
    main()
