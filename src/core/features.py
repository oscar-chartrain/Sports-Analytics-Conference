"""
features.py -- turns parsed points into per-player, regression-ready
features: leverage-weighted clutch scores, dropshot usage, and
pressure-ladder escalation deltas.

One of core/'s four modules (parsing, formulas, data_io, features),
consolidated from the old build_clutch_features.py and the
feature-reduction section of mcp_common.py.

--- build_clutch_features() provenance (from the original module docstring) ---
The original ATP build_clutch_features.py that produced
step3_clutch_features.csv was not recoverable. This function is a
reconstruction from the original Step 3 design notes (folded into
step3_README.md) and step3_README.md itself, cross-checked against
step3_h2h_check.py, which does survive as original, validated code (its
quartile_clutch() function is reused verbatim below, not reconstructed).

Verified-identical to the original pipeline: the formulas.py leverage
engine itself (unmodified, independently audited against the design notes
and tested against synthetic score states); quartile_clutch() (copied
verbatim from step3_h2h_check.py); MIN_OBS=30 gating, within-player
quartile split, serve/return computed separately; p=0.60/0.65/0.70
fixed-constant variants (unambiguous, just three scalar inputs to the
unmodified leverage engine).

One caveat (see docs/atp/03_leverage_clutch/empirical_p_variant.md):
rebuilding ATP's clutch features from scratch (via the pipeline/
rebuild_clutch_features.py tool) doesn't exactly reproduce the committed
step3_clutch_features.csv (clutch scores differ by up to ~0.005). Rebuilding
WTA's reproduces wta_clutch_features.csv exactly (max diff = 0), since that
file has always been this function's own output.

Reconstruction, not a verified match: the "tiered" pressure variant (the
original design notes didn't specify the exact mechanism -- this function's
interpretation is p=0.6425 on high-pressure points, else p=0.65 -- see
compute_all_leverages() below) and the BLR combined metric (matches
step3_README.md's stated definition, but wasn't checked against original
ATP BLR values, only the reported convergent-validity correlation).

Bottom line for the paper: report the primary p65 result and the p60/p70
fixed-constant robustness checks with full confidence in methodological
identity to the ATP pipeline. Report the tiered variant as a secondary,
reconstructed check, with a footnote on this provenance gap.

Fifth variant, added later: "empirical" -- p set to that tour's own
observed server point-win rate (data_io.compute_empirical_p()) rather than
a hand-picked constant, since p60/p65/p70/tiered are all ATP-calibrated and
were reused unchanged for WTA. Pre-registered before computing either
tour's value, see docs/atp/03_leverage_clutch/empirical_p_variant.md.
"""
import numpy as np
import pandas as pd

import parsing as pr
import formulas as f
import data_io as dio

MIN_OBS = 30  # see parsing.py-adjacent note: shared sufficiency floor for every feature below


def quartile_clutch(sub, leverage_col, min_obs=MIN_OBS):
    """Verbatim copy of the validated function from step3_h2h_check.py."""
    sub = sub.dropna(subset=[leverage_col, 'won'])
    n = len(sub)
    if n < min_obs * 4:
        return np.nan, 0, 0, False
    q_low = sub[leverage_col].quantile(0.25)
    q_high = sub[leverage_col].quantile(0.75)
    low = sub[sub[leverage_col] <= q_low]
    high = sub[sub[leverage_col] >= q_high]
    sufficient = len(low) >= min_obs and len(high) >= min_obs
    if not sufficient:
        return np.nan, len(high), len(low), False
    return high['won'].mean() - low['won'].mean(), len(high), len(low), True


def compute_all_leverages(row, match_format, p_empirical):
    if match_format is None or match_format.get('sets_to_win') is None:
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    lev_65 = f.compute_leverage(row, match_format, p=0.65)
    lev_60 = f.compute_leverage(row, match_format, p=0.60)
    lev_70 = f.compute_leverage(row, match_format, p=0.70)
    flags = pr.get_pressure_flags(row['Pts'], row['Svr'], row['Gm1'], row['Gm2'],
                                    row['Set1'], row['Set2'], match_format)
    is_hp = pr.is_high_pressure(flags['situation'], flags)
    # Reconstructed -- see module docstring. Use the exact literal 0.6425,
    # never "0.65 - 0.0075" computed inline. Leverage values are heavily
    # tied (many points share identical discrete score states), so a
    # quartile boundary can sit exactly on a tie cluster, and a 1e-16
    # floating-point difference between two equal-in-theory ways of
    # writing the same p can flip an entire tied cluster across the
    # boundary. That's how a bit-level rounding difference produced a
    # visible shift in one player's clutch score -- see wta_README.md's
    # bug-disclosure section.
    if is_hp:
        p_tiered = 0.6425
    else:
        p_tiered = 0.65
    lev_tiered = f.compute_leverage(row, match_format, p=p_tiered)
    # Tour-specific empirical p, see
    # docs/atp/03_leverage_clutch/empirical_p_variant.md. Same
    # unmodified engine and "one scalar for the whole tour" property as
    # p60/p65/p70/tiered above, just a data-derived scalar instead of a
    # hand-picked one.
    lev_empirical = f.compute_leverage(row, match_format, p=p_empirical)
    return (lev_65, lev_60, lev_70, lev_tiered, lev_empirical)


def build_clutch_features(matches_df, points_df, players, return_points=False):
    """Full pipeline: points -> leverage (5 variants) -> per-player clutch
    scores (serve/return, gated by MIN_OBS) -> BLR. Returns a DataFrame
    matching step3_clutch_features.csv's column structure.

    return_points=True additionally returns the point-level DataFrame
    (match_id, leverage columns, server, returner, server_won_point) this
    function already computes internally, as a second return value,
    instead of just the per-player summary. Added for
    continuous_slope_reliability.py so it can build an alternative
    (non-quartile) clutch construction from the same leverage values
    without duplicating any of the leverage/hitter-attribution logic
    above. Default False preserves every existing caller's single-
    DataFrame return unchanged."""
    match_format_lookup = f.build_match_format_lookup_ext(matches_df)
    match_players = matches_df.set_index('match_id')[['Player 1', 'Player 2']]

    p_empirical = dio.compute_empirical_p(points_df)
    print(f"Tour-specific empirical p (observed server point-win rate): {p_empirical:.4f}")

    records = points_df[['match_id', 'Svr', 'Pts', 'Gm1', 'Gm2', 'Set1', 'Set2', 'PtWinner']].to_dict('records')
    results = []
    for r in records:
        results.append(compute_all_leverages(r, match_format_lookup.get(r['match_id']), p_empirical))
    lev_df = pd.DataFrame(results, columns=['leverage_p65', 'leverage_p60', 'leverage_p70', 'leverage_tiered', 'leverage_empirical'])
    pts = pd.concat([points_df[['match_id', 'Svr', 'PtWinner']].reset_index(drop=True), lev_df], axis=1)
    pts = pts.join(match_players, on='match_id')
    pts['server'] = pts['Player 1'].where(pts['Svr'] == 1, pts['Player 2'])
    pts['returner'] = pts['Player 2'].where(pts['Svr'] == 1, pts['Player 1'])
    pts['server_won_point'] = (pts['PtWinner'] == pts['Svr']).astype(float)

    rows = []
    for player in players:
        serve_pts = pts[pts['server'] == player].copy()
        serve_pts['won'] = serve_pts['server_won_point']
        return_pts = pts[pts['returner'] == player].copy()
        return_pts['won'] = 1 - return_pts['server_won_point']

        row = {'player': player, 'p_empirical': p_empirical}
        for variant in ('p65', 'p60', 'p70', 'tiered', 'empirical'):
            lev_col = f'leverage_{variant}'
            s_score, s_nh, s_nl, s_suf = quartile_clutch(serve_pts, lev_col)
            r_score, r_nh, r_nl, r_suf = quartile_clutch(return_pts, lev_col)
            row[f'serve_clutch_{variant}'] = s_score
            row[f'serve_clutch_{variant}_sufficient'] = s_suf
            row[f'return_clutch_{variant}'] = r_score
            row[f'return_clutch_{variant}_sufficient'] = r_suf
            if variant == 'p65':
                row['n_serve_high_leverage'], row['n_serve_low_leverage'] = s_nh, s_nl
                row['n_return_high_leverage'], row['n_return_low_leverage'] = r_nh, r_nl

        all_pts = pd.concat([serve_pts[['leverage_p65', 'won']], return_pts[['leverage_p65', 'won']]])
        won_mean = all_pts.loc[all_pts['won'] == 1, 'leverage_p65'].mean()
        lost_mean = all_pts.loc[all_pts['won'] == 0, 'leverage_p65'].mean()
        if lost_mean:
            row['blr_combined'] = won_mean / lost_mean
        else:
            row['blr_combined'] = np.nan
        rows.append(row)

    summary = pd.DataFrame(rows)
    if return_points:
        return summary, pts
    return summary


# =============================================================================
# REGRESSION-READY FEATURE REDUCTION (dropshot, pressure-ladder deltas)
# =============================================================================
# Reduces each extension (dropshot usage, pressure-ladder deltas) to one
# regression-ready number per player, gated by MIN_OBS on each side of the
# comparison.

DEPTH_SCALE = {'7': 1, '8': 2, '9': 3}  # shallow/mid/deep -> ordinal, for a continuous mean-depth statistic


def compute_dropshot_features(shot_df_extended, player, min_obs=MIN_OBS):
    """
    Reduce dropshot usage to two regression-ready numbers:
      - dropshot_rate: total dropshots / total shots.
      - dropshot_direction_entropy: normalized Shannon entropy over the 3
        dropshot directions, computed only if all three direction cells
        individually clear MIN_OBS (dropshot volume runs 100-500x smaller
        than the core forehand/backhand grid, so this is NaN for most of
        the pool).
    Both come with an explicit '..._sufficient' boolean flag.
    """
    p_shots = shot_df_extended[shot_df_extended['hitter'] == player]
    total_shots = len(p_shots)
    cross = p_shots.groupby(['category', 'direction']).size()

    dropshot_cells = {}  # how many dropshots went in each of the 3 directions
    for d in ('1', '2', '3'):
        dropshot_cells[d] = cross.get(('dropshot', d), 0)
    total_dropshots = sum(dropshot_cells.values())

    rate_sufficient = total_shots >= min_obs

    entropy_sufficient = True
    for count in dropshot_cells.values():
        if count < min_obs:
            entropy_sufficient = False

    result = {
        'total_shots_extended': total_shots,
        'total_dropshots': total_dropshots,
        'dropshot_rate': np.nan,
        'dropshot_rate_sufficient': rate_sufficient,
        'dropshot_direction_entropy': np.nan,
        'dropshot_entropy_sufficient': entropy_sufficient,
    }
    if rate_sufficient:
        result['dropshot_rate'] = total_dropshots / total_shots
    if entropy_sufficient:
        counts = {}
        for d, n in dropshot_cells.items():
            counts[('dropshot', d)] = n
        _, norm_h = f.shannon_entropy(counts, pr.EXTENDED_CATEGORIES[6:9])  # the 3 dropshot cells
        result['dropshot_direction_entropy'] = norm_h
    return result


def reduce_pressure_features(pressure_df, player, min_obs=MIN_OBS):
    """Reduces the pressure-ladder extensions (serve zone, net-play, return
    depth) to one normal-vs-high-pressure delta each, only computed when
    both sides of the comparison clear MIN_OBS."""
    p_serve = pressure_df[(pressure_df['target_player'] == player) & (pressure_df['role'] == 'server')]
    p_return = pressure_df[(pressure_df['target_player'] == player) & (pressure_df['role'] == 'returner')]

    normal_serve = p_serve[p_serve['situation'] == 'normal']
    hp_serve = p_serve[p_serve['high_pressure']]
    n_normal_serve, n_hp_serve = len(normal_serve), len(hp_serve)
    serve_sufficient = n_normal_serve >= min_obs and n_hp_serve >= min_obs

    result = {
        'n_serve_normal': n_normal_serve, 'n_serve_high_pressure': n_hp_serve,
        'wide_serve_rate_normal': np.nan, 'wide_serve_rate_high_pressure': np.nan,
        'wide_serve_escalation_delta': np.nan, 'serve_zone_sufficient': serve_sufficient,
        'net_play_rate_normal': np.nan, 'net_play_rate_high_pressure': np.nan,
        'net_play_escalation_delta': np.nan, 'net_play_sufficient': serve_sufficient,
    }
    if serve_sufficient:
        wide_normal = (normal_serve['serve_direction'] == '4').mean()
        wide_hp = (hp_serve['serve_direction'] == '4').mean()
        result['wide_serve_rate_normal'] = wide_normal
        result['wide_serve_rate_high_pressure'] = wide_hp
        result['wide_serve_escalation_delta'] = wide_hp - wide_normal

        net_normal = normal_serve['went_to_net'].mean()
        net_hp = hp_serve['went_to_net'].mean()
        result['net_play_rate_normal'] = net_normal
        result['net_play_rate_high_pressure'] = net_hp
        result['net_play_escalation_delta'] = net_hp - net_normal

    normal_return = p_return[(p_return['situation'] == 'normal') & p_return['return_depth'].notna()]
    hp_return = p_return[p_return['high_pressure'] & p_return['return_depth'].notna()]
    n_normal_return, n_hp_return = len(normal_return), len(hp_return)
    return_sufficient = n_normal_return >= min_obs and n_hp_return >= min_obs

    result.update({
        'n_return_normal': n_normal_return, 'n_return_high_pressure': n_hp_return,
        'mean_return_depth_normal': np.nan, 'mean_return_depth_high_pressure': np.nan,
        'return_depth_shift_delta': np.nan, 'return_depth_sufficient': return_sufficient,
    })
    if return_sufficient:
        depth_normal = normal_return['return_depth'].map(DEPTH_SCALE).mean()
        depth_hp = hp_return['return_depth'].map(DEPTH_SCALE).mean()
        result['mean_return_depth_normal'] = depth_normal
        result['mean_return_depth_high_pressure'] = depth_hp
        result['return_depth_shift_delta'] = depth_hp - depth_normal

    return result
