"""
parsing.py -- Match Charting Project notation parsing, hitter attribution,
and score/pressure-situation classification.

One of core/'s four modules (parsing, formulas, data_io, features),
consolidated from the original flat mcp_common.py. See src/README.md for
the full migration map back to the original files.

The hitter-attribution bug (see HITTER PARITY below) used to be duplicated
in three places inside step2 and left unfixed in step1. Keeping this logic
in one place means a future fix only has to happen once.
"""


# =============================================================================
# SHOT-NOTATION PARSING
# =============================================================================
# Shot-type letters, from the MatchChart notation guide:
#   f=forehand, b=backhand groundstroke
#   r=forehand slice, s=backhand slice
#   v=forehand volley, z=backhand volley
#   o=forehand overhead, p=backhand overhead
#   u=forehand drop shot, y=backhand drop shot
#   l=forehand lob, m=backhand lob
#   h=forehand halfvolley, i=backhand halfvolley
#   j=forehand swinging volley, k=backhand swinging volley
#   t=trick shot, q=unknown shot type
# Bug history for this set: docs/atp/02_entropy_pipeline/step2_README.md
SHOT_TYPE_CHARS = set('fbrsvzoplymihjktq')
DIR_CHARS = set('123')


def extract_shot_dir_pairs(notation):
    """Reads a rally string like '6f27b1*' and returns each shot as a
    (letter, direction) pair, e.g. [('f', '2'), ('b', '1')]."""
    if not isinstance(notation, str) or notation == '':
        return []  # nothing to parse

    pairs = []
    i = 0
    n = len(notation)
    while i < n:
        ch = notation[i]
        if ch in SHOT_TYPE_CHARS:              # this character is a real shot letter
            direction = None
            if i + 1 < n and notation[i + 1] in DIR_CHARS:
                direction = notation[i + 1]    # digit right after the letter = direction
            pairs.append((ch, direction))
        i += 1                                  # move on, whether or not this char was a shot
    return pairs


# =============================================================================
# HITTER PARITY -- fix for the hitter-attribution bug.
# =============================================================================
# The serve is coded as a direction digit (4/5/6), not a shot-type letter, so
# extract_shot_dir_pairs() never captures it as a token: token 0 is always
# the return of serve (hit by the returner), not the server's shot. Bug
# history and verification: docs/atp/02_entropy_pipeline/step2_README.md
def hitter_is_p1_for_token(idx, server_is_p1):
    """Tokens alternate who hit them: 0 = return of serve, 1 = server's
    reply, 2 = returner's reply, and so on. Returns True if Player 1 hit
    the token at position idx."""
    returner_hit_this_shot = (idx % 2 == 0)  # even position = returner's turn
    if returner_hit_this_shot:
        return not server_is_p1  # it's whoever ISN'T the server
    else:
        return server_is_p1      # server's turn, so it's whoever IS the server


def verify_hitter_parity(matches_df, points_df, min_match_rate=0.85, sample_n=None):
    """Checks hitter_is_p1_for_token() against real data and raises an error
    if it's wrong too often -- catches the hitter-attribution bug coming
    back. Returns (match_rate, n_checked) if the check passes."""
    match_players = matches_df.set_index('match_id')[['Player 1', 'Player 2']]
    valid_ids = set(match_players.index)
    pts = points_df[points_df['match_id'].isin(valid_ids)]  # only points from real matches
    if sample_n is not None and len(pts) > sample_n:
        pts = pts.sample(sample_n, random_state=0)  # optional: check a random subset instead of everything

    correct = 0
    total = 0
    for row in pts[['match_id', 'Svr', '1st', '2nd', 'PtWinner']].to_dict('records'):  # loop one point at a time
        server_is_p1 = (row['Svr'] == 1)
        winner_is_p1 = (row['PtWinner'] == 1)
        for col in ('1st', '2nd'):  # a point can end on either the first or second serve
            val = row[col]
            if not isinstance(val, str) or not val.rstrip().endswith('*'):
                continue  # '*' marks the shot that won the point -- skip if this string doesn't have one
            tokens = extract_shot_dir_pairs(val)
            if not tokens:
                continue
            last_idx = len(tokens) - 1  # the winning shot is always the last token
            hitter_is_p1 = hitter_is_p1_for_token(last_idx, server_is_p1)
            total += 1
            if hitter_is_p1 == winner_is_p1:
                correct += 1

    if total > 0:
        match_rate = correct / total
    else:
        match_rate = float('nan')  # no data to check -- the assert below will catch this
    assert total > 0, "No winner-marked points found to validate against -- check input data."
    assert match_rate >= min_match_rate, (
        f"Hitter-parity check FAILED: only {match_rate:.1%} of {total} winner-marked points "
        f"matched PtWinner ground truth (expected >={min_match_rate:.0%}). "
        f"This may indicate the parity logic has been re-broken."
    )
    return match_rate, total


# =============================================================================
# CATEGORY MAPS (shot-type letter -> entropy-grid category)
# =============================================================================
# Forehand/backhand collapse every stroke variant (topspin, slice, volley,
# overhead) into the two wing categories. Lob, halfvolley, swinging volley,
# trick, and unknown shots are excluded (wing=None), so the core entropy
# grid is forehand/backhand x 3 directions (6 cells).
WING_MAP = {
    'f': 'forehand', 'r': 'forehand', 'u': 'forehand', 'o': 'forehand', 'v': 'forehand',
    'b': 'backhand', 's': 'backhand', 'y': 'backhand', 'p': 'backhand', 'z': 'backhand',
}
ENTROPY_CATEGORIES = [
    ('forehand', '1'), ('forehand', '2'), ('forehand', '3'),
    ('backhand', '1'), ('backhand', '2'), ('backhand', '3'),
]

# Same as WING_MAP but splits dropshot ('u'/'y') into its own category
# instead of folding it into forehand/backhand.
EXTENDED_CATEGORY_MAP = {
    'f': 'forehand', 'r': 'forehand', 'o': 'forehand', 'v': 'forehand',
    'b': 'backhand', 's': 'backhand', 'p': 'backhand', 'z': 'backhand',
    'u': 'dropshot', 'y': 'dropshot',
}
# Every (category, direction) combination, e.g. ('forehand', '1'), ('forehand', '2'), ...
EXTENDED_CATEGORIES = []
for cat in ('forehand', 'backhand', 'dropshot'):
    for d in ('1', '2', '3'):
        EXTENDED_CATEGORIES.append((cat, d))

# Shots that put the hitter at net (volley, swinging volley, overhead, both
# wings). Used for net-play detection.
NET_SHOT_TYPES = set('vzjkop')


# =============================================================================
# SERVE / RETURN NOTATION PARSING
# =============================================================================
# Serve direction: 4=wide, 5=body, 6=T (0=unknown), optionally preceded by
# 'c' (let) characters, optionally followed immediately by '+' (serve-and-
# volley attempt marker). Always the first character of '1st'; for '2nd',
# only present if a second serve was actually played.
SERVE_DIR_CHARS = set('456')


def _parse_serve_start(notation):
    """Finds where the serve-direction digit is, after skipping any leading
    let ('c') markers. Returns None if there's no valid serve marker there.
    Shared by parse_serve_prefix() and parse_return_depth()."""
    i = 0
    n = len(notation)
    while i < n and notation[i] == 'c':
        i += 1
    valid_serve_chars = SERVE_DIR_CHARS | {'0'}  # '0' also means "unknown direction"
    if i >= n or notation[i] not in valid_serve_chars:
        return None
    return i


def parse_serve_prefix(notation):
    """Reads the serve direction and whether it was a serve-and-volley
    attempt, e.g. '6+f1' -> ('6', True). Returns (None, False) if
    unparseable (e.g. a blank '2nd' field when the first serve went in)."""
    if not isinstance(notation, str) or notation == '':
        return None, False
    i = _parse_serve_start(notation)
    if i is None:
        return None, False
    ch = notation[i]
    is_snv = (i + 1 < len(notation) and notation[i + 1] == '+')  # '+' right after = serve-and-volley
    return ch, is_snv


# Return-of-serve depth: 7=shallow (service boxes), 8=mid, 9=deep (0=unknown).
# Recorded only on the service return; no other rally shot carries a depth
# code, so "length variability" as a general metric only exists for returns.
DEPTH_CHARS = set('789')


def parse_return_depth(notation):
    """Reads the return-of-serve shot right after the serve, e.g.
    '6f27' -> ('f', '2', '7'). Returns (None, None, None) if there's no
    return to read (ace, unreturnable, double fault)."""
    if not isinstance(notation, str) or notation == '':
        return None, None, None
    i = _parse_serve_start(notation)
    if i is None:
        return None, None, None
    n = len(notation)
    i += 1  # step past the serve-direction digit
    if i < n and notation[i] == '+':
        i += 1  # step past the serve-and-volley marker too, if present

    if i >= n or notation[i] not in SHOT_TYPE_CHARS:
        return None, None, None  # ace / unreturnable / fault -- no return shot to parse

    shot = notation[i]
    i += 1
    direction = None
    depth = None
    valid_dirs = DIR_CHARS | {'0'}  # '0' = unknown direction
    if i < n and notation[i] in valid_dirs:
        direction = notation[i]
        i += 1
        valid_depths = DEPTH_CHARS | {'0'}  # '0' = unknown depth
        if i < n and notation[i] in valid_depths:
            depth = notation[i]
    return shot, direction, depth


# =============================================================================
# SCORE / PRESSURE-SITUATION PARSING
# =============================================================================
# No break-point/set-point/match-point flag exists anywhere in the raw MCP
# points file (only match-level aggregate stats exist in the separate
# '-stats-' files). All of this is derived from 'Pts' (a string like '30-40'
# or, during a tiebreak, plain integers like '18-18'), 'Svr', the game score
# ('Gm1'/'Gm2'), the set score ('Set1'/'Set2'), and match format ('Best of',
# 'Final TB?' from the matches file).
SCORE_MAP = {'0': 0, '15': 1, '30': 2, '40': 3, 'AD': 4}


def parse_game_score(pts_str):
    """Parse a 'Pts' string into (p1_score, p2_score) on the 0/15/30/40/AD
    scale. Returns None if not a standard game score (e.g. tiebreak '18-18',
    or missing/malformed)."""
    if not isinstance(pts_str, str) or '-' not in pts_str:
        return None
    a, b = pts_str.split('-', 1)
    if a in SCORE_MAP and b in SCORE_MAP:
        return SCORE_MAP[a], SCORE_MAP[b]
    return None


def parse_tiebreak_score(pts_str):
    """Parse a 'Pts' string as a tiebreak score (two plain integers, e.g.
    '6-5'). Returns (p1_pts, p2_pts) or None if it doesn't fit that shape."""
    if not isinstance(pts_str, str) or '-' not in pts_str:
        return None
    a, b = pts_str.split('-', 1)
    try:
        return int(a), int(b)
    except ValueError:
        return None


def by_server(svr, p1_value, p2_value):
    """Reorders a (Player 1, Player 2) pair into (server, returner) order.
    svr is 1 if Player 1 is serving, anything else if Player 2 is."""
    if svr == 1:
        return p1_value, p2_value
    else:
        return p2_value, p1_value


# 'Best of' is mostly clean (3 or 5) with ~34 dirty rows out of ~7,567
# matches (NaN, '1', or garbage like 'Zindaras'). Matches with unparseable
# 'Best of' get sets_to_win=None and are excluded from set/match point
# detection rather than guessed at.
#
# 'Final TB?' format codes (from the official notation guide):
#   '1' = standard 7-pt tiebreak at 6-6 (vast majority of matches)
#   '0' = advantage final set, no tiebreak ever
#   'V' = no tiebreaks in ANY set (advantage sets throughout)
#   'W' = tiebreak at 8-all instead of 6-all (rare/historical)
#   'A' = 10-pt super-tiebreak at 6-6 in the final set (2019 Australian Open)
#   'S' = final set is JUST a 10-pt super-tiebreak, no games at all
#   'T' = tiebreak at 12-all in the final set (2019 Wimbledon)
#   'N' = NextGen Finals format
# Only 'A'/'S' change the tiebreak target score (10 instead of 7); every
# other code resolves to a standard 7-point breaker once triggered, or (for
# '0'/'V') no breaker at all, which check_clinches_set()'s game-margin logic
# already handles with no special-casing.
def build_match_format_lookup(matches_df):
    """For each match, works out how many sets are needed to win, and
    whether a final-set tiebreak (if any) goes to 7 or 10 points."""
    lookup = {}
    for row in matches_df[['match_id', 'Best of', 'Final TB?']].to_dict('records'):
        best_of_raw = row['Best of']
        try:
            best_of = int(best_of_raw)
            if best_of in (3, 5):
                sets_to_win = (best_of // 2) + 1  # best of 3 -> 2 sets to win, best of 5 -> 3 sets
            else:
                sets_to_win = None
        except (ValueError, TypeError):
            sets_to_win = None  # 'Best of' was missing or garbage -- see note above

        final_tb_raw = row['Final TB?']
        if isinstance(final_tb_raw, str):
            final_tb_code = final_tb_raw.strip()
        else:
            final_tb_code = None

        if final_tb_code in ('A', 'S'):
            super_tb_target = 10  # super-tiebreak formats
        else:
            super_tb_target = 7  # standard tiebreak (or no tiebreak at all)

        lookup[row['match_id']] = {'sets_to_win': sets_to_win, 'super_tb_target': super_tb_target}
    return lookup


def get_game_situation(pts_str, svr):
    """
    Classify the BASE (game-level, mutually-exclusive) situation for the
    point about to be played, from the server's perspective:
      'break_point'             -- returner is one point from breaking serve
      'game_point_server'       -- server is one point from holding
      'deuce'                   -- score is 40-40, no advantage yet
      'approaching_break_point' -- returner would create a break point by
                                    winning THIS point (e.g. 15-30, 30-30) --
                                    the "points to obtain the break point" case
      'normal'                  -- anything else in a normal game
      'tiebreak_or_other'       -- Pts wasn't a standard game score
    """
    parsed = parse_game_score(pts_str)
    if parsed is None:
        return 'tiebreak_or_other'
    p1_score, p2_score = parsed
    server_score, returner_score = by_server(svr, p1_score, p2_score)

    if returner_score == 4:
        return 'break_point'
    if server_score == 4:
        return 'game_point_server'
    if returner_score == 3 and server_score < 3:
        return 'break_point'
    if server_score == 3 and returner_score < 3:
        return 'game_point_server'
    if server_score == 3 and returner_score == 3:
        return 'deuce'
    sim_returner = returner_score + 1
    if sim_returner == 3 and server_score < 3:
        return 'approaching_break_point'
    return 'normal'


def check_clinches_set(games_after_win, opponent_games):
    """Standard tennis set-win condition: >=6 games with a >=2 game margin.
    No hardcoded upper bound, so advantage sets that run past 6-6 (e.g. 8-6,
    15-13) are handled without special-casing."""
    return games_after_win >= 6 and (games_after_win - opponent_games) >= 2


def get_pressure_flags(pts_str, svr, gm1, gm2, set1, set2, match_format):
    """
    Compute set_point/match_point boolean flags layered on top of the base
    get_game_situation() category (a point can be a break point AND a set
    point AND a match point simultaneously). Returns:
      {'situation': <base category>, 'set_point_server': bool,
       'set_point_returner': bool, 'match_point_server': bool,
       'match_point_returner': bool}

    Requires sets_to_win from match_format; if unavailable (dirty 'Best of'),
    all four flags are False -- excluded, not guessed.
    """
    situation = get_game_situation(pts_str, svr)
    flags = {'situation': situation, 'set_point_server': False, 'set_point_returner': False,
              'match_point_server': False, 'match_point_returner': False}

    if match_format:
        sets_to_win = match_format.get('sets_to_win')
    else:
        sets_to_win = None
    if sets_to_win is None:
        return flags

    server_games, returner_games = by_server(svr, gm1, gm2)
    server_sets, returner_sets = by_server(svr, set1, set2)

    if situation == 'tiebreak_or_other':
        tb = parse_tiebreak_score(pts_str)
        if tb is None:
            return flags
        p1_tb, p2_tb = tb
        server_tb, returner_tb = by_server(svr, p1_tb, p2_tb)
        target = match_format.get('super_tb_target', 7)
        if server_tb + 1 >= target and (server_tb + 1 - returner_tb) >= 2:
            flags['set_point_server'] = True
            if server_sets + 1 == sets_to_win:
                flags['match_point_server'] = True
        if returner_tb + 1 >= target and (returner_tb + 1 - server_tb) >= 2:
            flags['set_point_returner'] = True
            if returner_sets + 1 == sets_to_win:
                flags['match_point_returner'] = True
        return flags

    if situation == 'game_point_server' and check_clinches_set(server_games + 1, returner_games):
        flags['set_point_server'] = True
        if server_sets + 1 == sets_to_win:
            flags['match_point_server'] = True
    if situation == 'break_point' and check_clinches_set(returner_games + 1, server_games):
        flags['set_point_returner'] = True
        if returner_sets + 1 == sets_to_win:
            flags['match_point_returner'] = True

    return flags


# High-pressure composite: any point where the score has tightened enough
# for the game, set, or match to turn.
HIGH_PRESSURE_SITUATIONS = {'break_point', 'game_point_server', 'deuce', 'approaching_break_point'}


def is_high_pressure(situation, flags):
    """True if the point is tense: a break/game/deuce/approaching-BP
    situation, or a set-point/match-point flag is set. This also catches
    tiebreak set/match points, which don't get a game-level category but
    are clearly high-pressure."""
    if situation in HIGH_PRESSURE_SITUATIONS:
        return True
    if flags['set_point_server'] or flags['set_point_returner']:
        return True
    if flags['match_point_server'] or flags['match_point_returner']:
        return True
    return False
