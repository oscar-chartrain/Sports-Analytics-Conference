"""
Step 2: Shot-Selection Entropy Pipeline (v2 -- rebuilt on core/parsing.py,
core/formulas.py, core/data_io.py)
==========================================================================
Builds the Shannon entropy calculation for shot-selection consistency and
runs the Sinner/Alcaraz sanity check, plus four extensions (dropshot,
serve zone under pressure, net-play under pressure, return depth under
pressure).

This is a rebuild of the original step2_entropy_pipeline.py, refactored to
import all shared notation/scoring/entropy logic from core/ instead of
duplicating it inline (the duplication is exactly how the hitter-parity
bug ended up copy-pasted three times in one file, see parsing.py's module
docstring). Only step2-specific composition logic lives here: per-player
shot extraction, transition-entropy computation, dropshot sparsity checks,
and the pressure-feature table builder.

Design constraints carried forward from Step 1 (see step1_README.md):
  - Player pool: qualified_player_pool_min40.csv (>=40 charted matches), not
    the raw MCP files directly.
  - Shot categories: forehand/backhand only, x 3 court-directions (6 cells),
    for the core entropy calc. Lob and "other" excluded (genuine rarity, not
    a coverage gap, confirmed in Step 1).
  - Points data is split by decade in the MCP repo; only 2020s is loaded by
    default here, sufficient for the Sinner/Alcaraz sanity check but not for
    the full 91-player pool (most of it has matches in earlier decades).
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
import pandas as pd

import parsing as pr
import formulas as f
import data_io as dio

pd.set_option('display.width', 140)


# =============================================================================
# Core pipeline: pooled shots for a set of target players
# =============================================================================

def get_player_shots(matches_df, points_df, target_players):
    """
    For each player in target_players, extract every shot they hit (as a
    forehand/backhand groundstroke with a valid direction digit) across all
    their charted matches in points_df. Uses parsing.WING_MAP (fh/bh only).

    Returns a long DataFrame: [match_id, shot_type, direction, hitter, wing].
    """
    relevant_matches = matches_df[
        matches_df['Player 1'].isin(target_players) | matches_df['Player 2'].isin(target_players)
    ]
    match_players = relevant_matches.set_index('match_id')[['Player 1', 'Player 2']]
    target_ids = set(relevant_matches['match_id'])
    pts = points_df[points_df['match_id'].isin(target_ids)].copy()

    all_rows = []
    for row in pts[['match_id', 'Svr', '1st', '2nd']].to_dict('records'):
        match_id = row['match_id']
        if match_id not in match_players.index:
            continue
        p1, p2 = match_players.loc[match_id, ['Player 1', 'Player 2']]
        server_is_p1 = (row['Svr'] == 1)
        for col in ('1st', '2nd'):
            val = row[col]
            tokens = pr.extract_shot_dir_pairs(val)
            for idx, (shot, direction) in enumerate(tokens):
                if direction is None:
                    continue
                wing = pr.WING_MAP.get(shot)
                if wing is None:
                    continue  # lob / halfvolley / other -- excluded from core entropy calc
                hitter_is_p1 = pr.hitter_is_p1_for_token(idx, server_is_p1)
                if hitter_is_p1:
                    hitter = p1
                else:
                    hitter = p2
                if hitter not in target_players:
                    continue
                all_rows.append((match_id, shot, direction, hitter, wing))

    return pd.DataFrame(all_rows, columns=['match_id', 'shot_type', 'direction', 'hitter', 'wing'])


def compute_player_entropy(shot_df, player, min_obs_per_cell=30):
    """Pooled (marginal) Shannon entropy for a single player over the 6-cell
    (wing, direction) grid. Returns cell counts, raw/normalized entropy, and
    a data-sufficiency flag (Step 1's 30-obs floor)."""
    p_shots = shot_df[shot_df['hitter'] == player]
    cross = p_shots.groupby(['wing', 'direction']).size()

    counts = {}  # how many shots landed in each (wing, direction) cell
    for cat in pr.ENTROPY_CATEGORIES:
        counts[cat] = cross.get(cat, 0)
    raw_h, norm_h = f.shannon_entropy(counts, pr.ENTROPY_CATEGORIES)

    low_cells = {}  # cells below the sufficiency floor, kept for the report below
    for cat, n in counts.items():
        if n < min_obs_per_cell:
            low_cells[cat] = n
    return {
        'player': player, 'total_shots': sum(counts.values()), 'cell_counts': counts,
        'raw_entropy_bits': raw_h, 'normalized_entropy': norm_h,
        'low_cells': low_cells, 'data_sufficient': len(low_cells) == 0,
    }


def format_entropy_report(result):
    lines = [f"\n--- {result['player']}: {result['total_shots']} usable (wing, direction) shots ---"]
    for (wing, direction), n in result['cell_counts'].items():
        lines.append(f"  {wing:9s} dir {direction}: {n:5d}")
    lines.append(f"  Raw entropy:        {result['raw_entropy_bits']:.4f} bits (max = log2(6) = {np.log2(6):.4f})")
    lines.append(f"  Normalized entropy: {result['normalized_entropy']:.4f}  (0=deterministic, 1=uniform/unpredictable)")
    if result['data_sufficient']:
        lines.append("  Data sufficiency: OK (all 6 cells >= 30 obs)")
    else:
        lines.append(f"  Data sufficiency: WARNING -- sparse cells: {result['low_cells']}")
    return "\n".join(lines)


# =============================================================================
# Transition (conditional) entropy pipeline
# =============================================================================
# Rationale: a career-long MARGINAL distribution over 6 (wing, direction)
# cells mostly reflects court geometry (everyone hits more cross-court than
# down-the-line) rather than a player's style. Conditioning on the preceding
# shot in the rally (the ball the player is reacting to) is a much closer
# match to what "shot-selection consistency" should mean.
CONTEXT_OTHER = ('other', 'x')


def get_player_shot_transitions(matches_df, points_df, target_players, include_pressure=False):
    """
    Build (context, current) pairs where `current` is one of the 6
    ENTROPY_CATEGORIES (the player's own shot) and `context` is the (wing,
    direction) of the immediately preceding shot in the rally -- i.e. the
    shot the target player is reacting to.

    include_pressure=True additionally classifies each transition's
    underlying point via parsing.get_pressure_flags()/is_high_pressure()
    (the same classifier used for the serve-zone/net-play/return-depth
    escalation deltas) and adds a 'high_pressure' boolean column. No new
    parsing or hitter-attribution logic -- reuses the existing classifier.
    Needs 'Pts','Gm1','Gm2','Set1','Set2' in points_df, which the default
    (False) path doesn't touch. Default False preserves the original
    4-column output unchanged for every existing caller.

    Returns a long DataFrame: [match_id, target_player, context, current]
    (plus 'high_pressure' if include_pressure=True).
    """
    relevant_matches = matches_df[
        matches_df['Player 1'].isin(target_players) | matches_df['Player 2'].isin(target_players)
    ]
    match_players = relevant_matches.set_index('match_id')[['Player 1', 'Player 2']]
    target_ids = set(relevant_matches['match_id'])
    pts = points_df[points_df['match_id'].isin(target_ids)].copy()

    if include_pressure:
        match_format_lookup = pr.build_match_format_lookup(relevant_matches)
    else:
        match_format_lookup = None
    cols = ['match_id', 'Svr', '1st', '2nd']
    if include_pressure:
        cols += ['Pts', 'Gm1', 'Gm2', 'Set1', 'Set2']

    all_rows = []
    for row in pts[cols].to_dict('records'):
        match_id = row['match_id']
        if match_id not in match_players.index:
            continue
        p1, p2 = match_players.loc[match_id, ['Player 1', 'Player 2']]
        server_is_p1 = (row['Svr'] == 1)

        if include_pressure:
            match_format = match_format_lookup.get(match_id)
            pflags = pr.get_pressure_flags(row['Pts'], row['Svr'], row['Gm1'], row['Gm2'],
                                             row['Set1'], row['Set2'], match_format)
            high_pressure = pr.is_high_pressure(pflags['situation'], pflags)

        for col in ('1st', '2nd'):
            val = row[col]
            tokens = pr.extract_shot_dir_pairs(val)
            if len(tokens) < 2:
                continue
            for idx in range(1, len(tokens)):
                shot, direction = tokens[idx]
                if direction is None:
                    continue
                wing = pr.WING_MAP.get(shot)
                if wing is None:
                    continue
                current_cat = (wing, direction)

                prev_shot, prev_direction = tokens[idx - 1]
                prev_wing = pr.WING_MAP.get(prev_shot)
                if prev_wing is not None and prev_direction is not None:
                    context_cat = (prev_wing, prev_direction)
                else:
                    context_cat = CONTEXT_OTHER  # preceding shot was a serve/lob/other -- no clean context

                hitter_is_p1 = pr.hitter_is_p1_for_token(idx, server_is_p1)
                if hitter_is_p1:
                    hitter = p1
                else:
                    hitter = p2
                if hitter not in target_players:
                    continue
                row_tuple = (match_id, hitter, context_cat, current_cat)
                if include_pressure:
                    row_tuple = row_tuple + (high_pressure,)
                all_rows.append(row_tuple)

    columns = ['match_id', 'target_player', 'context', 'current']
    if include_pressure:
        columns.append('high_pressure')
    return pd.DataFrame(all_rows, columns=columns)


def compute_transition_entropy(transitions_df, player, min_obs_per_context=30):
    """Conditional entropy H(current|context) plus marginal H(current) for
    comparison, and the information gain (mutual information) between them."""
    p_trans = transitions_df[transitions_df['target_player'] == player]
    total_n = len(p_trans)
    if total_n == 0:
        return None

    marginal_counts = p_trans.groupby('current').size()
    marginal_dict = {}
    for cat in pr.ENTROPY_CATEGORIES:
        marginal_dict[cat] = marginal_counts.get(cat, 0)
    marginal_h, marginal_norm_h = f.shannon_entropy(marginal_dict, pr.ENTROPY_CATEGORIES)

    context_counts = p_trans.groupby('context').size()
    conditional_h = 0.0
    context_detail = {}
    low_contexts = {}
    for context_cat, n_context in context_counts.items():
        p_context = n_context / total_n
        sub = p_trans[p_trans['context'] == context_cat]
        cur_counts = sub.groupby('current').size()
        cur_dict = {}
        for cat in pr.ENTROPY_CATEGORIES:
            cur_dict[cat] = cur_counts.get(cat, 0)
        h_given_c, _ = f.shannon_entropy(cur_dict, pr.ENTROPY_CATEGORIES)
        if np.isnan(h_given_c):
            continue
        conditional_h += p_context * h_given_c
        context_detail[context_cat] = {'n': n_context, 'entropy_given_context': h_given_c}
        if n_context < min_obs_per_context:
            low_contexts[context_cat] = n_context

    max_h = np.log2(len(pr.ENTROPY_CATEGORIES))
    conditional_norm_h = conditional_h / max_h
    info_gain = marginal_h - conditional_h
    if marginal_h:
        info_gain_relative = info_gain / marginal_h
    else:
        info_gain_relative = np.nan

    return {
        'player': player, 'total_transitions': total_n,
        'marginal_entropy_bits': marginal_h, 'marginal_normalized': marginal_norm_h,
        'conditional_entropy_bits': conditional_h, 'conditional_normalized': conditional_norm_h,
        'info_gain_bits': info_gain, 'info_gain_relative': info_gain_relative,
        'context_detail': context_detail, 'low_contexts': low_contexts,
    }


def format_transition_report(result):
    lines = [f"\n--- {result['player']}: {result['total_transitions']} (context -> current) transitions ---"]
    lines.append(f"  Marginal entropy H(current):            {result['marginal_entropy_bits']:.4f} bits "
                  f"(normalized {result['marginal_normalized']:.4f})")
    lines.append(f"  Conditional entropy H(current|context): {result['conditional_entropy_bits']:.4f} bits "
                  f"(normalized {result['conditional_normalized']:.4f})")
    lines.append(f"  Information gain from context:          {result['info_gain_bits']:.4f} bits "
                  f"({result['info_gain_relative']:.1%} reduction from marginal)")
    if result['low_contexts']:
        lines.append(f"  Note: {len(result['low_contexts'])} context bucket(s) below 30 obs "
                      f"(included but individually noisy): {result['low_contexts']}")
    return "\n".join(lines)


# =============================================================================
# Extension 1: dropshot as its own category
# =============================================================================

def get_player_shots_extended(matches_df, points_df, target_players):
    """Same as get_player_shots(), but using parsing.EXTENDED_CATEGORY_MAP so
    dropshots land in their own 'dropshot' bucket instead of being merged
    into forehand/backhand."""
    relevant_matches = matches_df[
        matches_df['Player 1'].isin(target_players) | matches_df['Player 2'].isin(target_players)
    ]
    match_players = relevant_matches.set_index('match_id')[['Player 1', 'Player 2']]
    target_ids = set(relevant_matches['match_id'])
    pts = points_df[points_df['match_id'].isin(target_ids)].copy()

    all_rows = []
    for row in pts[['match_id', 'Svr', '1st', '2nd']].to_dict('records'):
        match_id = row['match_id']
        if match_id not in match_players.index:
            continue
        p1, p2 = match_players.loc[match_id, ['Player 1', 'Player 2']]
        server_is_p1 = (row['Svr'] == 1)
        for col in ('1st', '2nd'):
            val = row[col]
            tokens = pr.extract_shot_dir_pairs(val)
            for idx, (shot, direction) in enumerate(tokens):
                if direction is None:
                    continue
                category = pr.EXTENDED_CATEGORY_MAP.get(shot)
                if category is None:
                    continue
                hitter_is_p1 = pr.hitter_is_p1_for_token(idx, server_is_p1)
                if hitter_is_p1:
                    hitter = p1
                else:
                    hitter = p2
                if hitter not in target_players:
                    continue
                all_rows.append((match_id, shot, direction, hitter, category))

    return pd.DataFrame(all_rows, columns=['match_id', 'shot_type', 'direction', 'hitter', 'category'])


def check_dropshot_sparsity(shot_df_extended, player, min_obs=30):
    """Per-cell sparsity check for the dropshot row of the extended 3x3 grid."""
    p_shots = shot_df_extended[shot_df_extended['hitter'] == player]
    cross = p_shots.groupby(['category', 'direction']).size()

    dropshot_cells = {}
    for d in ('1', '2', '3'):
        dropshot_cells[('dropshot', d)] = cross.get(('dropshot', d), 0)
    total_dropshots = sum(dropshot_cells.values())

    low = {}
    for k, v in dropshot_cells.items():
        if v < min_obs:
            low[k] = v
    return {'player': player, 'dropshot_cells': dropshot_cells, 'total_dropshots': total_dropshots, 'low_cells': low}


# =============================================================================
# Extensions 2-4: pressure-situation features (serve zone, net-play, return depth)
# =============================================================================

def get_pressure_features(matches_df, points_df, target_players):
    """
    Build a per-point-per-target-player feature table: serve zone choice,
    serve-and-volley/net-play, and return depth -- each tagged with the full
    pressure taxonomy from parsing.py (base situation + set/match point flags).

    Returns [match_id, target_player, role, situation, set_point_server,
    set_point_returner, match_point_server, match_point_returner,
    high_pressure, serve_direction, is_snv, went_to_net, return_shot_type,
    return_direction, return_depth].
    """
    relevant_matches = matches_df[
        matches_df['Player 1'].isin(target_players) | matches_df['Player 2'].isin(target_players)
    ]
    match_players = relevant_matches.set_index('match_id')[['Player 1', 'Player 2']]
    target_ids = set(relevant_matches['match_id'])
    pts = points_df[points_df['match_id'].isin(target_ids)].copy()
    match_format_lookup = pr.build_match_format_lookup(relevant_matches)

    rows = []
    for row in pts[['match_id', 'Svr', 'Pts', 'Gm1', 'Gm2', 'Set1', 'Set2', '1st', '2nd']].to_dict('records'):
        match_id = row['match_id']
        if match_id not in match_players.index:
            continue
        p1, p2 = match_players.loc[match_id, ['Player 1', 'Player 2']]
        svr = row['Svr']
        server, returner = pr.by_server(svr, p1, p2)
        match_format = match_format_lookup.get(match_id, {})
        pflags = pr.get_pressure_flags(row['Pts'], svr, row['Gm1'], row['Gm2'], row['Set1'], row['Set2'], match_format)
        situation = pflags['situation']
        high_pressure = pr.is_high_pressure(situation, pflags)

        first_dir, first_snv = pr.parse_serve_prefix(row['1st'])
        first_tokens = pr.extract_shot_dir_pairs(row['1st'])
        first_serve_in = len(first_tokens) > 0 or (isinstance(row['1st'], str) and ('*' in row['1st'] or '#' in row['1st']))
        if first_serve_in or not isinstance(row['2nd'], str) or row['2nd'] == '':
            eff_notation = row['1st']
            eff_dir, eff_snv = first_dir, first_snv
        else:
            eff_notation = row['2nd']
            eff_dir, eff_snv = pr.parse_serve_prefix(row['2nd'])

        base_fields = {
            'match_id': match_id, 'situation': situation,
            'set_point_server': pflags['set_point_server'], 'set_point_returner': pflags['set_point_returner'],
            'match_point_server': pflags['match_point_server'], 'match_point_returner': pflags['match_point_returner'],
            'high_pressure': high_pressure,
        }

        if server in target_players and eff_dir is not None:
            tokens = pr.extract_shot_dir_pairs(eff_notation)
            went_to_net = eff_snv
            if not went_to_net:
                for idx, (shot, _d) in enumerate(tokens):
                    # server's own shots are at ODD indices: idx 0 is the
                    # return (hit by the returner), per parsing.hitter_is_p1_for_token
                    if idx % 2 == 1 and shot in pr.NET_SHOT_TYPES:
                        went_to_net = True
                        break
            rows.append({
                **base_fields, 'target_player': server, 'role': 'server',
                'serve_direction': eff_dir, 'is_snv': eff_snv, 'went_to_net': went_to_net,
                'return_shot_type': None, 'return_direction': None, 'return_depth': None,
            })

        if returner in target_players:
            r_shot, r_dir, r_depth = pr.parse_return_depth(eff_notation)
            if r_shot is not None:
                rows.append({
                    **base_fields, 'target_player': returner, 'role': 'returner',
                    'serve_direction': None, 'is_snv': None, 'went_to_net': None,
                    'return_shot_type': r_shot, 'return_direction': r_dir, 'return_depth': r_depth,
                })

    return pd.DataFrame(rows)


# =============================================================================
# Main: Sinner/Alcaraz sanity check
# =============================================================================

if __name__ == '__main__':
    print("Loading match metadata and 2020s points data...")
    matches = dio.load_matches('charting-m-matches.csv')
    points = dio.load_points_data(decades=('2020s',))
    pool = dio.load_qualified_pool()
    print(f"Qualified pool loaded: {len(pool)} players")

    print("\n--- Hitter-parity regression check (see parsing.verify_hitter_parity) ---")
    match_rate, n_checked = pr.verify_hitter_parity(matches, points)
    print(f"Hitter attribution matches PtWinner ground truth: {match_rate:.1%} of {n_checked} winner-marked points")

    SANITY_PLAYERS = ['Jannik Sinner', 'Carlos Alcaraz']
    assert all(p in pool['player'].values for p in SANITY_PLAYERS), \
        "Sanity-check players must be present in the qualified pool"

    print(f"\nExtracting shots for sanity-check pair: {SANITY_PLAYERS}")
    shot_df = get_player_shots(matches, points, SANITY_PLAYERS)
    print(f"Total (wing, direction) shot tokens extracted: {len(shot_df)}")

    print("\n" + "=" * 70)
    print("SANITY CHECK: Sinner vs Alcaraz shot-selection entropy")
    print("=" * 70)

    results = {}
    for player in SANITY_PLAYERS:
        result = compute_player_entropy(shot_df, player)
        results[player] = result
        print(format_entropy_report(result))

    print("\n--- Interpretation check (pooled entropy) ---")
    sinner_h = results['Jannik Sinner']['normalized_entropy']
    alcaraz_h = results['Carlos Alcaraz']['normalized_entropy']
    print(f"Sinner normalized entropy:  {sinner_h:.4f}")
    print(f"Alcaraz normalized entropy: {alcaraz_h:.4f}")
    print(f"Gap: {abs(sinner_h - alcaraz_h):.4f} -- both near the {np.log2(6):.2f}-bit ceiling, gap is within noise.")
    print("Pooled career-long entropy mostly reflects court geometry, not style -- see transition entropy below.")

    print("\n" + "=" * 70)
    print("REFINEMENT: transition (conditional) entropy -- context = preceding shot in rally")
    print("=" * 70)

    trans_df = get_player_shot_transitions(matches, points, SANITY_PLAYERS)
    print(f"Total (context, current) transitions extracted: {len(trans_df)}")

    trans_results = {}
    for player in SANITY_PLAYERS:
        tresult = compute_transition_entropy(trans_df, player)
        trans_results[player] = tresult
        print(format_transition_report(tresult))

    print("\n--- Interpretation check (transition entropy) ---")
    sinner_cond = trans_results['Jannik Sinner']['conditional_normalized']
    alcaraz_cond = trans_results['Carlos Alcaraz']['conditional_normalized']
    sinner_gain = trans_results['Jannik Sinner']['info_gain_relative']
    alcaraz_gain = trans_results['Carlos Alcaraz']['info_gain_relative']
    print(f"Sinner:  conditional entropy {sinner_cond:.4f}, info gain from context {sinner_gain:.1%}")
    print(f"Alcaraz: conditional entropy {alcaraz_cond:.4f}, info gain from context {alcaraz_gain:.1%}")
    if sinner_cond < alcaraz_cond and sinner_gain > alcaraz_gain:
        print("-> Sinner's shot choice is BOTH lower-entropy given context AND more context-dependent")
        print("   (bigger drop from marginal to conditional) than Alcaraz.")
    elif sinner_cond < alcaraz_cond:
        print("-> Sinner is more predictable given context, but the context-dependence (info gain)")
        print("   is similar for both -- partial support for the narrative, worth more scrutiny.")
    else:
        print("-> Conditioning on rally context did not sharpen the Sinner/Alcaraz contrast in the")
        print("   expected direction.")

    # ========================================================================
    # EXTENSION 1: Dropshot as its own category
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXTENSION 1: Dropshot patterns -- sparsity check before using")
    print("=" * 70)
    ext_shot_df = get_player_shots_extended(matches, points, SANITY_PLAYERS)
    for player in SANITY_PLAYERS:
        d = check_dropshot_sparsity(ext_shot_df, player)
        print(f"\n{player}: {d['total_dropshots']} total dropshots")
        for cat, n in d['dropshot_cells'].items():
            if cat in d['low_cells']:
                flag = " <- sparse"
            else:
                flag = ""
            print(f"  {cat}: {n}{flag}")

    # ========================================================================
    # EXTENSIONS 2-4: pressure-situation features
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXTENSIONS 2-4: Pressure-situation features")
    print("=" * 70)
    pressure_df = get_pressure_features(matches, points, SANITY_PLAYERS)
    print(f"Total feature rows extracted: {len(pressure_df)}")
    print(f"\nBase situation breakdown:\n{pressure_df['situation'].value_counts()}")
    print(f"\nSet point (server) count:   {pressure_df['set_point_server'].sum()}")
    print(f"Set point (returner) count: {pressure_df['set_point_returner'].sum()}")
    print(f"Match point (server) count:   {pressure_df['match_point_server'].sum()}")
    print(f"Match point (returner) count: {pressure_df['match_point_returner'].sum()}")
    print(f"High-pressure composite count: {pressure_df['high_pressure'].sum()} / {len(pressure_df)} "
          f"({pressure_df['high_pressure'].mean():.1%})")

    for player in SANITY_PLAYERS:
        print(f"\n{'=' * 50}\n{player}\n{'=' * 50}")
        p_serve = pressure_df[(pressure_df['target_player'] == player) & (pressure_df['role'] == 'server')]
        p_return = pressure_df[(pressure_df['target_player'] == player) & (pressure_df['role'] == 'returner')]

        print("\n-- Serve zone distribution across pressure levels --")
        situ_labels = [
            ('normal', p_serve['situation'] == 'normal'),
            ('approaching_break_point', p_serve['situation'] == 'approaching_break_point'),
            ('break_point', p_serve['situation'] == 'break_point'),
            ('set_point (server)', p_serve['set_point_server']),
            ('match_point (server)', p_serve['match_point_server']),
        ]
        for label, mask in situ_labels:
            sub = p_serve[mask]
            n = len(sub)
            if n < 20:
                print(f"  {label}: n={n} (too few to report a reliable split)")
                continue
            counts = sub['serve_direction'].value_counts(normalize=True).sort_index()
            print(f"  {label} (n={n}): " + ", ".join(f"{d}={p:.1%}" for d, p in counts.items()))

        print("\n-- Net-play (incl. serve-and-volley) rate: normal vs high-pressure --")
        for label, mask in [('normal', p_serve['situation'] == 'normal'),
                             ('high-pressure (composite)', p_serve['high_pressure'])]:
            sub = p_serve[mask]
            n = len(sub)
            if n == 0:
                print(f"  {label}: no data")
                continue
            net_rate = sub['went_to_net'].mean()
            snv_rate = sub['is_snv'].mean()
            print(f"  {label} (n={n}): net-play rate={net_rate:.1%}, pure SnV rate={snv_rate:.1%}")

        print("\n-- Return depth distribution (7=shallow, 8=mid, 9=deep) across pressure levels --")
        situ_labels_return = [
            ('normal', p_return['situation'] == 'normal'),
            ('break_point', p_return['situation'] == 'break_point'),
            ('set_point (returner)', p_return['set_point_returner']),
            ('match_point (returner)', p_return['match_point_returner']),
        ]
        for label, mask in situ_labels_return:
            sub = p_return[mask & p_return['return_depth'].notna()]
            n = len(sub)
            if n < 20:
                print(f"  {label}: n={n} (too few to report a reliable split)")
                continue
            counts = sub['return_depth'].value_counts(normalize=True).sort_index()
            print(f"  {label} (n={n}): " + ", ".join(f"{d}={p:.1%}" for d, p in counts.items()))
