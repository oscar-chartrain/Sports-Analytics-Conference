"""
applications_analyses.py -- the three Applications analyses pre-registered in
docs/combined/applications_preregistration.md (written 2026-11-03, before
this script existed):

  1. Split-half reliability of Tennis Abstract's faithful Balanced Leverage
     Ratio (BLR = mean of serve LR and return LR), p65 leverage.
  2. How much data a reliable clutch score needs (Spearman-Brown prophecy,
     plus a per-player shrinkage-model projection). A derived projection,
     not a hypothesis test.
  3. Player-cluster bootstrap intervals on named players' clutch scores and
     ranks (B = 2,000, NumPy seed 20261103).

Reuses, unchanged: split_half_reliability.split_matches() (same A/B halves as
every reliability already reported), features.build_clutch_features(...,
return_points=True) (leverage engine + point table), features.quartile_clutch(),
formulas.spearman_brown(). Needs the raw MCP files in results/{tour}/ (see the
root README's Reproduce section). The leverage pass is slow, so the point
table is cached to results/{tour}/cache_applications_{tour}.pkl (gitignored).

Sanity checks from the pre-registration run first and abort the script
(nothing is written) if any fails.

Usage: python3 applications_analyses.py [--no-cache] [--boot N]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import argparse
import pickle

import numpy as np
import pandas as pd
from scipy import stats

import features as feat
import formulas as f
import split_half_reliability as shr

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(REPO_ROOT, 'results', 'applications')
FIG_DIR = os.path.join(REPO_ROOT, 'results', 'figures')

MIN_OBS = feat.MIN_OBS
LEV = 'leverage_p65'
SEED = 20261103
N_BOOT = 2000

# Documented values (split_half_reliability.md, shrinkage_reliability.md).
DOC_RELIABILITY = {
    ('atp', 'entropy'): 0.925, ('atp', 'serve'): 0.572, ('atp', 'return'): 0.231,
    ('wta', 'entropy'): 0.897, ('wta', 'serve'): 0.578, ('wta', 'return'): 0.055,
}
DOC_SHRINKAGE = {
    ('atp', 'serve'): 0.594, ('atp', 'return'): 0.371,
    ('wta', 'serve'): 0.624, ('wta', 'return'): 0.132,
}
NAMED_ATP = ['Jannik Sinner', 'Carlos Alcaraz', 'Novak Djokovic', 'Roger Federer']


# =============================================================================
# DATA
# =============================================================================

def load_tour(tour, use_cache=True):
    """Returns (players, matches, half_map, summary, pts): the point table
    (match_id, leverage_*, server, returner, server_won_point) plus the
    pipeline's own per-player summary for the full relevant sample."""
    cache_path = os.path.join(REPO_ROOT, 'results', tour, f'cache_applications_{tour}.pkl')
    players = shr.load_pool(tour)
    matches, points = shr.load_raw(tour)
    half_map, relevant_matches = shr.split_matches(matches, players)
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, 'rb') as fh:
            summary, pts = pickle.load(fh)
        print(f"{tour.upper()}: loaded cached point table ({len(pts):,} points)")
    else:
        relevant_points = points[points['match_id'].isin(set(half_map.keys()))]
        print(f"{tour.upper()}: computing leverage on {len(relevant_points):,} points (slow)...")
        summary, pts = feat.build_clutch_features(relevant_matches, relevant_points, players,
                                                  return_points=True)
        with open(cache_path, 'wb') as fh:
            pickle.dump((summary, pts), fh)
    pts = pts.copy()
    pts['half'] = pts['match_id'].map(half_map)
    return players, matches, half_map, summary, pts


def role_frames(pts, players):
    """{player: {'serve': df, 'return': df}} with a 'won' column from the
    player's point of view (same construction as build_clutch_features)."""
    out = {}
    serve_groups = dict(tuple(pts.groupby('server')))
    return_groups = dict(tuple(pts.groupby('returner')))
    for p in players:
        s = serve_groups[p].copy()
        s['won'] = s['server_won_point']
        r = return_groups[p].copy()
        r['won'] = 1 - r['server_won_point']
        out[p] = {'serve': s, 'return': r}
    return out


# =============================================================================
# ANALYSIS 1: BLR RELIABILITY
# =============================================================================

def leverage_ratio(sub, min_obs=MIN_OBS):
    """Mean leverage of points won / mean leverage of points lost. Needs at
    least min_obs of each (pre-registered sufficiency rule)."""
    sub = sub.dropna(subset=[LEV, 'won'])
    won = sub.loc[sub['won'] == 1, LEV]
    lost = sub.loc[sub['won'] == 0, LEV]
    if len(won) < min_obs or len(lost) < min_obs:
        return np.nan
    lost_mean = lost.mean()
    if lost_mean == 0:
        return np.nan
    return won.mean() / lost_mean


def half_measures(frames, players, half_label):
    """Per-player measures on one half, all computed independently of the
    other half."""
    rows = {}
    for p in players:
        s = frames[p]['serve']
        r = frames[p]['return']
        s = s[s['half'] == half_label]
        r = r[r['half'] == half_label]
        lr_s = leverage_ratio(s)
        lr_r = leverage_ratio(r)
        blr = (lr_s + lr_r) / 2 if not (np.isnan(lr_s) or np.isnan(lr_r)) else np.nan
        pooled = leverage_ratio(pd.concat([s, r]))
        q_s = feat.quartile_clutch(s, LEV)
        q_r = feat.quartile_clutch(r, LEV)
        rows[p] = {
            'lr_serve': lr_s, 'lr_return': lr_r, 'blr': blr, 'pooled_lr': pooled,
            'serve_clutch': q_s[0] if q_s[3] else np.nan,
            'return_clutch': q_r[0] if q_r[3] else np.nan,
        }
    return pd.DataFrame.from_dict(rows, orient='index')


def split_half_with_ci(a, b):
    """Split-half r, Spearman-Brown full-length reliability, and a 95% CI
    (Fisher z on r, endpoints then Spearman-Brown transformed)."""
    both = pd.concat([a, b], axis=1, keys=['a', 'b']).dropna()
    n = len(both)
    r, _ = stats.pearsonr(both['a'], both['b'])
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return {'n': n, 'r_half': r, 'r_full': f.spearman_brown(r),
            'ci_lo': f.spearman_brown(lo), 'ci_hi': f.spearman_brown(hi)}


def analysis1(tour, players, summary, frames):
    print(f"\n{'=' * 70}\nANALYSIS 1 -- {tour.upper()}: reliability of BLR\n{'=' * 70}")
    ma = half_measures(frames, players, 'A')
    mb = half_measures(frames, players, 'B')
    n_excl = {}
    for col in ['lr_serve', 'lr_return', 'blr', 'pooled_lr']:
        n_excl[col] = int((ma[col].isna() | mb[col].isna()).sum())
    print(f"players excluded by the per-half 30-won/30-lost floor: {n_excl}")

    rel = {}
    for name, col in [('BLR (faithful, primary)', 'blr'), ('Pooled LR', 'pooled_lr'),
                      ('LR serve', 'lr_serve'), ('LR return', 'lr_return'),
                      ('Serve quartile clutch', 'serve_clutch'),
                      ('Return quartile clutch', 'return_clutch')]:
        rel[name] = split_half_with_ci(ma[col], mb[col])
        r = rel[name]
        print(f"{name:26s} n={r['n']:3d}  r_half={r['r_half']:+.4f}  "
              f"SB={r['r_full']:.4f}  95% CI [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]")

    # entropy: taken from the committed split-half CSV (see deviations log)
    raw = pd.read_csv(os.path.join(FIG_DIR, f'split_half_raw_{tour}.csv'))
    r_ent, _ = stats.pearsonr(raw['entropy_a'], raw['entropy_b'])
    ent_sb = f.spearman_brown(r_ent)

    # ---- pre-registered sanity checks -------------------------------------
    ok = True
    checks = [('entropy', ent_sb), ('serve', rel['Serve quartile clutch']['r_full']),
              ('return', rel['Return quartile clutch']['r_full'])]
    for key, val in checks:
        doc = DOC_RELIABILITY[(tour, key)]
        passed = abs(val - doc) <= 0.005
        ok = ok and passed
        print(f"SANITY {key:8s} reproduced={val:.4f} documented={doc:.3f} -> {'PASS' if passed else 'FAIL'}")

    full_pooled = {}
    for p in players:
        full_pooled[p] = leverage_ratio(pd.concat([frames[p]['serve'], frames[p]['return']]))
    full_pooled = pd.Series(full_pooled)
    s_idx = summary.set_index('player')
    diff = (full_pooled - s_idx['blr_combined']).abs().max()
    passed = diff < 1e-12
    ok = ok and passed
    print(f"SANITY full-sample pooled LR vs blr_combined: max abs diff={diff:.2e} -> {'PASS' if passed else 'FAIL'}")
    if not ok:
        raise SystemExit(f"{tour.upper()}: Analysis 1 sanity check failed; stop and investigate (pre-registered).")

    # ---- full-sample relationships between the BLR definitions ------------
    full = pd.DataFrame({
        'lr_serve': {p: leverage_ratio(frames[p]['serve']) for p in players},
        'lr_return': {p: leverage_ratio(frames[p]['return']) for p in players},
    })
    full['blr'] = (full['lr_serve'] + full['lr_return']) / 2
    full['pooled_lr'] = full_pooled
    full['combined_quartile'] = (s_idx['serve_clutch_p65'] + s_idx['return_clutch_p65']) / 2
    r_bp = stats.pearsonr(full['blr'], full['pooled_lr'])[0]
    r_bq = stats.pearsonr(full['blr'], full['combined_quartile'])[0]
    r_pq = stats.pearsonr(full['pooled_lr'], full['combined_quartile'])[0]
    print(f"full-sample r: faithful BLR vs pooled LR = {r_bp:.3f}; faithful BLR vs combined quartile = "
          f"{r_bq:.3f}; pooled LR vs combined quartile = {r_pq:.3f}")

    out = []
    for name, r in rel.items():
        out.append({'tour': tour, 'measure': name, **r})
    return pd.DataFrame(out), {'ent_sb': ent_sb, 'r_blr_pooled': r_bp, 'r_blr_quartile': r_bq,
                               'r_pooled_quartile': r_pq, 'excluded': n_excl}, full


# =============================================================================
# ANALYSIS 2: DATA REQUIREMENTS
# =============================================================================

def prophecy_k(rho, target):
    """Spearman-Brown prophecy: factor by which data must be multiplied to
    reach `target` reliability. None if rho <= 0 (not attainable)."""
    if rho <= 0:
        return None
    return target * (1 - rho) / (rho * (1 - target))


def analysis2(tour, matches, players, summary, a1_rel):
    print(f"\n{'=' * 70}\nANALYSIS 2 -- {tour.upper()}: data requirements (derived projection)\n{'=' * 70}")
    counts = pd.concat([matches['Player 1'], matches['Player 2']]).value_counts()
    pool_counts = counts.reindex(players)
    median_matches = float(pool_counts.median())
    print(f"median charted matches across the pool: {median_matches:.1f}")

    inputs = {
        'Quartile clutch, serve': DOC_RELIABILITY[(tour, 'serve')],
        'Quartile clutch, return': DOC_RELIABILITY[(tour, 'return')],
        'Shrunk clutch, serve': DOC_SHRINKAGE[(tour, 'serve')],
        'Shrunk clutch, return': DOC_SHRINKAGE[(tour, 'return')],
        'BLR (faithful)': a1_rel.loc[a1_rel['measure'] == 'BLR (faithful, primary)', 'r_full'].iloc[0],
    }
    rows = []
    for label, rho in inputs.items():
        row = {'tour': tour, 'measure': label, 'rho': rho}
        for target in (0.70, 0.80):
            k = prophecy_k(rho, target)
            row[f'k_{int(target * 100)}'] = k
            row[f'matches_{int(target * 100)}'] = None if k is None else k * median_matches
        rows.append(row)
        k70, k80 = row['k_70'], row['k_80']
        if k70 is None:
            print(f"{label:26s} rho={rho:+.3f}  NOT ATTAINABLE by adding data (rho <= 0)")
        else:
            print(f"{label:26s} rho={rho:+.3f}  k(0.70)={k70:6.2f} -> {row['matches_70']:7.0f} matches;  "
                  f"k(0.80)={k80:6.2f} -> {row['matches_80']:7.0f} matches")
    primary = pd.DataFrame(rows)

    # ---- secondary: per-player reliability under the shrinkage model ------
    s = summary.set_index('player').reindex(players)
    sec_rows = []
    for role in ('serve', 'return'):
        ok = s[f'{role}_clutch_p65_sufficient'].astype(bool)
        sub = s[ok]
        raw = sub[f'{role}_clutch_p65']
        n_high = sub[f'n_{role}_high_leverage']
        n_low = sub[f'n_{role}_low_leverage']
        var_i = 0.25 * (1.0 / n_high + 1.0 / n_low)
        tau2 = max(0.0, raw.var(ddof=1) - var_i.mean())
        rel_i = tau2 / (tau2 + var_i)
        share_ok = float((rel_i >= 0.70).mean())
        high_per_match = (n_high / pool_counts.reindex(sub.index)).median()
        if tau2 > 0:
            n_star = 0.5 * 0.70 / (0.30 * tau2)
            matches_star = n_star / high_per_match
        else:
            n_star, matches_star = None, None
        print(f"{role:7s} tau2={tau2:.6f}  mean var_i={var_i.mean():.6f}  mean rel_i={rel_i.mean():.3f}  "
              f"share rel_i>=0.70: {share_ok:.1%}  median high-lev pts/match={high_per_match:.1f}")
        if n_star is None:
            print("        no detectable between-player variance (tau2 = 0)")
        else:
            print(f"        n* = {n_star:,.0f} high-leverage points -> {matches_star:,.0f} matches for rel = 0.70")
        sec_rows.append({'tour': tour, 'role': role, 'tau2': tau2, 'mean_var_i': var_i.mean(),
                         'mean_rel_i': rel_i.mean(), 'share_rel_ge_70': share_ok,
                         'high_lev_pts_per_match': high_per_match, 'n_star_high_pts': n_star,
                         'matches_star': matches_star})
        # consistency check, pre-registered: within a factor of 3
        prim = primary[primary['measure'] == f'Quartile clutch, {role}'].iloc[0]['matches_70']
        if prim is not None and matches_star is not None:
            ratio = max(prim, matches_star) / min(prim, matches_star)
            print(f"        consistency: primary {prim:,.0f} vs secondary {matches_star:,.0f} matches "
                  f"(ratio {ratio:.2f}; {'within' if ratio <= 3 else 'OUTSIDE'} the pre-registered factor of 3)")
            sec_rows[-1]['ratio_primary_secondary'] = ratio
    return primary, pd.DataFrame(sec_rows), median_matches


# =============================================================================
# ANALYSIS 3: PLAYER-CLUSTER BOOTSTRAP
# =============================================================================

class RolePoints:
    """One player's points in one role, sorted by leverage, with the index of
    the player-match each point belongs to. Lets a bootstrap replicate be
    expressed as integer weights (how often each match was drawn)."""
    def __init__(self, df, match_index):
        df = df.dropna(subset=[LEV, 'won']).sort_values(LEV, kind='stable')
        self.lev = df[LEV].to_numpy(dtype=float)
        self.won = df['won'].to_numpy(dtype=float)
        self.mi = df['match_id'].map(match_index).to_numpy()
        self.lev_won = self.lev * self.won
        self.lev_lost = self.lev * (1.0 - self.won)

    def stats(self, match_counts):
        """(quartile clutch score, leverage ratio) for a match-count vector.
        Quartile thresholds are recomputed on the weighted sample with the
        same linear interpolation pandas uses."""
        w = match_counts[self.mi].astype(float)
        cum = np.cumsum(w)
        total = cum[-1]

        def quantile(q):
            pos = q * (total - 1)
            lo = int(np.floor(pos))
            hi = int(np.ceil(pos))
            v_lo = self.lev[np.searchsorted(cum, lo, side='right')]
            v_hi = self.lev[np.searchsorted(cum, hi, side='right')]
            return v_lo + (v_hi - v_lo) * (pos - lo)

        q_low, q_high = quantile(0.25), quantile(0.75)
        i_low = np.searchsorted(self.lev, q_low, side='right')   # points with lev <= q_low
        i_high = np.searchsorted(self.lev, q_high, side='left')  # points with lev >= q_high
        cum_won = np.cumsum(w * self.won)

        n_low = cum[i_low - 1] if i_low > 0 else 0.0
        won_low = cum_won[i_low - 1] if i_low > 0 else 0.0
        before_high = cum[i_high - 1] if i_high > 0 else 0.0
        won_before_high = cum_won[i_high - 1] if i_high > 0 else 0.0
        n_high = total - before_high
        won_high = cum_won[-1] - won_before_high
        score = won_high / n_high - won_low / n_low

        n_won = np.dot(w, self.won)
        n_lost = total - n_won
        lr = (np.dot(w, self.lev_won) / n_won) / (np.dot(w, self.lev_lost) / n_lost)
        return score, lr


def player_matches(frames_p):
    ids = sorted(set(frames_p['serve']['match_id']) | set(frames_p['return']['match_id']))
    return ids, {m: i for i, m in enumerate(ids)}


def analysis3(tour, players, summary, frames, n_boot):
    print(f"\n{'=' * 70}\nANALYSIS 3 -- {tour.upper()}: player-cluster bootstrap (B={n_boot}, seed {SEED})\n{'=' * 70}")
    rng = np.random.default_rng(SEED)
    s = summary.set_index('player')
    measures = ['serve', 'return', 'blr']

    point = {m: {} for m in measures}
    boot = {m: np.full((n_boot, len(players)), np.nan) for m in measures}
    ident_ok = True
    for j, p in enumerate(players):
        ids, midx = player_matches(frames[p])
        sp = RolePoints(frames[p]['serve'], midx)
        rp = RolePoints(frames[p]['return'], midx)
        ones = np.ones(len(ids))
        s0, lr_s0 = sp.stats(ones)
        r0, lr_r0 = rp.stats(ones)
        point['serve'][p], point['return'][p] = s0, r0
        point['blr'][p] = (lr_s0 + lr_r0) / 2
        # pre-registered identity-weights sanity check
        ds = abs(s0 - s.loc[p, 'serve_clutch_p65'])
        dr = abs(r0 - s.loc[p, 'return_clutch_p65'])
        if ds > 1e-12 or dr > 1e-12:
            ident_ok = False
            print(f"SANITY identity-weights FAIL for {p}: serve diff {ds:.2e}, return diff {dr:.2e}")
        draws = rng.multinomial(len(ids), np.full(len(ids), 1.0 / len(ids)), size=n_boot)
        for b in range(n_boot):
            sb, lr_sb = sp.stats(draws[b])
            rb, lr_rb = rp.stats(draws[b])
            boot['serve'][b, j] = sb
            boot['return'][b, j] = rb
            boot['blr'][b, j] = (lr_sb + lr_rb) / 2
        if (j + 1) % 10 == 0:
            print(f"  ...{j + 1}/{len(players)} players")
    if not ident_ok:
        raise SystemExit("Analysis 3: identity-weights sanity check failed; stop and investigate.")
    print("SANITY identity weights reproduce pipeline clutch scores for every player: PASS")

    summaries = []
    player_tables = []
    for m in measures:
        pt = np.array([point[m][p] for p in players])
        mat = boot[m]
        bias = np.abs(mat.mean(axis=0) - pt).max()
        mean_bias = (mat.mean(axis=0) - pt)
        lo, hi = np.percentile(mat, [2.5, 97.5], axis=0)
        ranks = np.argsort(np.argsort(-mat, axis=1), axis=1) + 1
        rlo, rhi = np.percentile(ranks, [2.5, 97.5], axis=0)
        pt_rank = np.argsort(np.argsort(-pt)) + 1
        pool_mean = pt.mean()
        excl = int(((lo > pool_mean) | (hi < pool_mean)).sum())
        top10 = np.argsort(pt_rank)[:10]
        top10_in_20 = int((rhi[top10] <= 20).sum())
        width = rhi - rlo
        if m == 'blr':
            tol_note = 'ratio scale; the +/-0.002 tolerance is for clutch scores only'
        else:
            tol_note = f"{'within' if bias <= 0.002 else 'OUTSIDE'} the +/-0.002 clutch-score tolerance"
        print(f"\n[{m}] pool mean {pool_mean:+.4f}; max |mean boot - point| = {bias:.5f} ({tol_note})")
        print(f"  median 95% rank-interval width: {np.median(width):.1f} ranks (of {len(players)})")
        print(f"  players whose 95% score interval excludes the pool mean: {excl}/{len(players)}")
        print(f"  of the top 10 by point estimate, rank interval entirely within top 20: {top10_in_20}/10")
        summaries.append({'tour': tour, 'measure': m, 'pool_mean': pool_mean,
                          'median_rank_width': float(np.median(width)),
                          'n_excluding_pool_mean': excl, 'n_players': len(players),
                          'top10_within_top20': top10_in_20,
                          'max_abs_boot_bias': bias, 'mean_abs_boot_bias': float(np.abs(mean_bias).mean())})
        tbl = pd.DataFrame({'tour': tour, 'measure': m, 'player': players, 'score': pt,
                            'score_lo': lo, 'score_hi': hi, 'rank': pt_rank,
                            'rank_lo': rlo, 'rank_hi': rhi})
        player_tables.append(tbl)
    players_df = pd.concat(player_tables, ignore_index=True)

    if tour == 'atp':
        print("\nNamed players (ATP):")
        for name in NAMED_ATP:
            for m in measures:
                row = players_df[(players_df['measure'] == m) & (players_df['player'] == name)]
                if row.empty:
                    print(f"  {name}: not in pool")
                    break
                r = row.iloc[0]
                print(f"  {name:16s} {m:7s} score {r['score']:+.4f} [{r['score_lo']:+.4f}, {r['score_hi']:+.4f}]  "
                      f"rank {int(r['rank']):2d} [{r['rank_lo']:.0f}, {r['rank_hi']:.0f}]")
    return pd.DataFrame(summaries), players_df


# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--boot', type=int, default=N_BOOT)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    a1_all, a2_prim, a2_sec, a3_sum, a3_players, extras = [], [], [], [], [], {}
    for tour in ('atp', 'wta'):
        players, matches, half_map, summary, pts = load_tour(tour, use_cache=not args.no_cache)
        frames = role_frames(pts, players)
        a1, ex, _ = analysis1(tour, players, summary, frames)
        extras[tour] = ex
        a1_all.append(a1)
        prim, sec, _ = analysis2(tour, matches, players, summary, a1)
        a2_prim.append(prim)
        a2_sec.append(sec)
        s3, p3 = analysis3(tour, players, summary, frames, args.boot)
        a3_sum.append(s3)
        a3_players.append(p3)

    pd.concat(a1_all).to_csv(os.path.join(OUT_DIR, 'a1_blr_reliability.csv'), index=False)
    pd.concat(a2_prim).to_csv(os.path.join(OUT_DIR, 'a2_projection_primary.csv'), index=False)
    pd.concat(a2_sec).to_csv(os.path.join(OUT_DIR, 'a2_projection_secondary.csv'), index=False)
    pd.concat(a3_sum).to_csv(os.path.join(OUT_DIR, 'a3_bootstrap_summary.csv'), index=False)
    pd.concat(a3_players).to_csv(os.path.join(OUT_DIR, 'a3_bootstrap_players.csv'), index=False)
    pd.DataFrame(extras).T.to_csv(os.path.join(OUT_DIR, 'a1_sanity_extras.csv'))
    print(f"\nWrote outputs to {OUT_DIR}")


if __name__ == '__main__':
    main()
