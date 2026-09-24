"""
formulas.py -- pure computation: entropy math, reliability corrections, the
leverage/win-probability engine, and general-purpose statistical utilities.

One of core/'s four modules (parsing, formulas, data_io, features),
consolidated from the old mcp_common.py (entropy math), leverage.py (the
whole leverage engine), and stats_helpers.py (the general stats
corrections). spearman_brown() is consolidated here -- it used to be
copy-pasted independently in four different analysis scripts; this is now
the one canonical version.

The leverage engine builds on parsing.py's score-state parsers
(parse_game_score, parse_tiebreak_score, build_match_format_lookup,
get_game_situation, by_server) to compute, for any point, the Morris (1977)
leverage weight:

    leverage = P(win match | win this point) - P(win match | lose this point)

using ONE fixed point-win probability p for every point (not a separate p
per player), so leverage doesn't end up partly measuring a player's own
serving quality. Because both players share the same p, any fresh or tied
state (0-0 games, a set that hasn't started yet) is exactly a 50/50 coin
flip by symmetry, not an approximation -- this is what lets match-level
probability reduce to plain binomial reasoning over remaining sets. Full
rationale and citations: docs/atp/03_leverage_clutch/step3_README.md
"""

from functools import lru_cache
from math import comb
import numpy as np
from scipy import stats

import parsing as pr


# =============================================================================
# ENTROPY MATH
# =============================================================================

def shannon_entropy(counts, categories, base=2):
    """Computes Shannon entropy: how spread out (unpredictable) the counts
    are across categories. Returns (raw_entropy, normalized_entropy), where
    normalized 1.0 = totally random/uniform, 0.0 = always the same category."""
    total = 0
    for cat in categories:
        total += counts.get(cat, 0)
    if total == 0:
        return np.nan, np.nan
    h = 0.0
    for cat in categories:
        n = counts.get(cat, 0)
        if n == 0:
            continue
        p = n / total
        h -= p * np.log(p) / np.log(base)
    max_h = np.log(len(categories)) / np.log(base)
    return h, h / max_h


# =============================================================================
# RELIABILITY CORRECTIONS
# =============================================================================

def spearman_brown(r_half):
    """Spearman-Brown correction: converts a half-test reliability
    correlation (r_half, from correlating one half of the data against the
    other) into the estimated reliability of the FULL-length test."""
    return (2 * r_half) / (1 + r_half)


# =============================================================================
# LEVERAGE / WIN-PROBABILITY ENGINE (Morris 1977)
# =============================================================================

def build_match_format_lookup_ext(matches_df):
    """Same as parsing.build_match_format_lookup(), but also keeps the raw
    'Final TB?' code -- compute_leverage() needs to know directly whether
    it's '0' or 'V' (no tiebreak at all in an advantage-set format)."""
    base = pr.build_match_format_lookup(matches_df)
    for row in matches_df[['match_id', 'Final TB?']].to_dict('records'):
        code = row['Final TB?']
        if isinstance(code, str):
            code = code.strip()
        else:
            code = None
        if row['match_id'] in base:
            base[row['match_id']]['final_tb_code'] = code
    return base

# =============================================================================
# 1. GAME-LEVEL WIN PROBABILITY (Section 4a)
# =============================================================================

@lru_cache(maxsize=None)  # @lru_cache remembers past results, so a repeated score state is never recomputed
def prob_win_game(a, b, p):
    """P(server wins the game | current raw point score a-b for server-returner),
    for a standard advantage-scoring game. a, b are raw points won in this game
    (0,1,2,3,4... not capped at the 40/AD display scale). Closed form at deuce,
    recursive elsewhere. Memoized (score space is tiny)."""
    if a >= 4 and a - b >= 2:
        return 1.0
    if b >= 4 and b - a >= 2:
        return 0.0
    if a >= 3 and b >= 3:
        diff = a - b
        if diff == 0:  # deuce
            return (p ** 2) / (p ** 2 + (1 - p) ** 2)
        elif diff == 1:  # server at advantage
            return p + (1 - p) * prob_win_game(3, 3, p)
        elif diff == -1:  # returner at advantage
            return p * prob_win_game(3, 3, p)
    return p * prob_win_game(a + 1, b, p) + (1 - p) * prob_win_game(a, b + 1, p)


# =============================================================================
# 2. TIEBREAK WIN PROBABILITY (Section 4b)
# =============================================================================
# Server alternates: player X serves point 1, then each player serves 2 points
# in a row, alternating, from point 2 onward. seq[i] = server (bool, True/False
# for the two players) of point i+1 (0-indexed), given seq[0] = first server.

@lru_cache(maxsize=None)
def prob_win_tiebreak(a, b, p, i_served_point_one, target=7):
    """P(the player of interest wins the tiebreak | current score a-b), where
    i_served_point_one indicates whether that player served the tiebreak's
    very first point (determines the whole server sequence).

    Closed-form escape, mirroring the exact symmetry result in
    prob_win_set: once tied at n-n with n >= target-1, every subsequent
    "round" of 2 points consists of exactly one point each player serves.
    P(+2 net for me in a round) = p*(1-p) = P(-2 net) always, regardless of
    p, so from any such tied state the probability of eventually winning
    by 2 is exactly 0.5, independent of p and of whose serve starts the
    round. Without this, the naive recursion has no depth bound (a
    tiebreak can in principle run arbitrarily long) and blows the stack;
    with it, every non-terminal state is at most one point from either a
    terminal state or this closed form, so recursion stays shallow.

    Module-level lru_cache (not a local memo dict) so score states are
    shared across the entire point-level computation loop: most points
    share common score states (30-15, deuce, etc.) across different
    matches, and each unique state only gets computed once, total."""
    if a >= target and a - b >= 2:
        return 1.0
    if b >= target and b - a >= 2:
        return 0.0
    if a == b and a >= target - 1:
        return 0.5  # exact closed form, not an approximation -- see docstring
    server_is_me = _tb_server_is_me(a + b, i_served_point_one)
    if server_is_me:
        win_next = prob_win_tiebreak(a + 1, b, p, i_served_point_one, target)
        lose_next = prob_win_tiebreak(a, b + 1, p, i_served_point_one, target)
        return p * win_next + (1 - p) * lose_next
    else:
        win_next = prob_win_tiebreak(a, b + 1, p, i_served_point_one, target)
        lose_next = prob_win_tiebreak(a + 1, b, p, i_served_point_one, target)
        return p * win_next + (1 - p) * lose_next


@lru_cache(maxsize=None)
def _tb_server_is_me(m, i_served_point_one):
    """Server (relative to 'me') of tiebreak point number m+1 (0-indexed m
    points already played), given whether 'I' served point 1."""
    if m == 0:
        return i_served_point_one
    prev = _tb_server_is_me(m - 1, i_served_point_one)
    if (m - 1) % 2 == 1:
        return prev
    return not prev


# =============================================================================
# 3. SET WIN PROBABILITY (Section 4c)
# =============================================================================
# Games alternate server by hard rule (exact, not approximate) within a set.
# p_hold = prob_win_game(0,0,p) is IDENTICAL for both players (shared p), so
# "my win prob for a game" is p_hold if I serve it, (1-p_hold) if they do.

@lru_cache(maxsize=None)
def prob_win_set(games_a, games_b, p, i_serve_next_game, final_tb_code, super_tb_target=7):
    """P(player of interest wins the set | current game score games_a-games_b,
    i_serve_next_game = whether that player serves the next game to be played).
    Hands off to prob_win_tiebreak at 6-6 for standard formats. For advantage
    (no-tiebreak) formats, uses the exact symmetry result: from ANY tied game
    score (6-6, 7-7, ...) the set is exactly 0.5, since both players share p.
    Module-level lru_cache: shared across the whole point-level computation
    loop, same rationale as prob_win_tiebreak."""
    p_hold = prob_win_game(0, 0, p)
    has_tb = final_tb_code not in ('0', 'V')

    if games_a >= 6 and games_a - games_b >= 2:
        return 1.0
    if games_b >= 6 and games_b - games_a >= 2:
        return 0.0
    if games_a > 100 or games_b > 100:
        # defensive safety net: should be unreachable given valid tennis score
        # data (even the Isner-Mahut 70-68 marathon stays well under this),
        # but guards against any other unforeseen dirty-data case reaching
        # this recursion with a state that never resolves.
        return np.nan
    if games_a == 6 and games_b == 6:
        if has_tb:
            return prob_win_tiebreak(0, 0, p, i_serve_next_game, target=super_tb_target)
        else:
            return 0.5  # exact symmetry result, not an approximation
    if games_a >= 6 and games_b >= 6 and games_a == games_b:
        return 0.5  # tied beyond 6-6 in an advantage set: exact symmetry
    next_serve = not i_serve_next_game
    # Either way, the set continues from one of these two next states -- only
    # how likely each one is (below) depends on who's serving this game.
    prob_if_i_win_game = prob_win_set(games_a + 1, games_b, p, next_serve, final_tb_code, super_tb_target)
    prob_if_i_lose_game = prob_win_set(games_a, games_b + 1, p, next_serve, final_tb_code, super_tb_target)
    if i_serve_next_game:
        return p_hold * prob_if_i_win_game + (1 - p_hold) * prob_if_i_lose_game
    else:
        return (1 - p_hold) * prob_if_i_win_game + p_hold * prob_if_i_lose_game


# =============================================================================
# 4. MATCH WIN PROBABILITY -- simplified via the exact symmetry result: any
# future, not-yet-started set is worth exactly 0.5 (both players share p, so
# a fresh set is a fair coin flip). Only the current set needs the full
# prob_win_set() recursion; remaining sets reduce to ordinary binomial
# reasoning over a sequence of fair coins.
# =============================================================================

def _remaining_sets_win_prob(sets_needed, sets_available, p_current_set):
    """P(win >= sets_needed more sets out of a race where the CURRENT set (in
    progress) has probability p_current_set, and every set AFTER that is an
    exact 0.5 coin flip). sets_available = max additional sets that could be
    played after (and including) the current one before the match format caps
    it -- i.e. sets_to_win - min(server_sets, returner_sets) - 1, capped by the
    actual match length. Recursive: win the current set now (prob
    p_current_set), needing sets_needed-1 more from sets_available-1 remaining
    (all fair coins) -- or lose the current set (prob 1-p_current_set),
    needing sets_needed still from sets_available-1 remaining (fair coins)."""

    @lru_cache(maxsize=None)
    def fair_binom_at_least(k, n):
        """P(>=k successes in n fair coin flips). n can be 0."""
        if k <= 0:
            return 1.0
        if k > n:
            return 0.0
        ways_to_get_at_least_k = 0
        for i in range(k, n + 1):
            ways_to_get_at_least_k += comb(n, i)
        return ways_to_get_at_least_k / (2 ** n)

    if sets_needed <= 0:
        return 1.0
    if sets_needed > sets_available:
        return 0.0
    remaining_after_current = sets_available - 1
    win_now = p_current_set * fair_binom_at_least(sets_needed - 1, remaining_after_current)
    lose_now = (1 - p_current_set) * fair_binom_at_least(sets_needed, remaining_after_current)
    return win_now + lose_now


def prob_win_match(server_sets, returner_sets, p_current_set, sets_to_win):
    """P(server wins the match | current set score, and p_current_set = the
    EXACT probability server wins the set currently in progress, from
    prob_win_set()). Every set after the current one is treated as a fair
    coin (see module docstring)."""
    sets_needed = sets_to_win - server_sets
    # max sets that could still be played (current + any after), respecting
    # that the match ends the instant either side reaches sets_to_win
    max_total_more_sets = (sets_to_win - server_sets) + (sets_to_win - returner_sets) - 1
    return _remaining_sets_win_prob(sets_needed, max_total_more_sets, p_current_set)


# =============================================================================
# 5. WIRING: leverage for one point (Section 5)
# =============================================================================

def compute_leverage(row, match_format, p):
    """row: dict-like with Pts, Svr, Gm1, Gm2, Set1, Set2 for the point BEFORE
    it is played. match_format: {'sets_to_win', 'super_tb_target'} from
    build_match_format_lookup, or None if unparseable (-> NaN leverage).
    Returns leverage (float) or np.nan."""
    if match_format is None or match_format.get('sets_to_win') is None:
        return np.nan

    # Guard against NaN/malformed score fields (rare gaps in the raw data):
    # NaN comparisons are always False in Python, so a NaN Gm1/Gm2/Set1/Set2
    # would silently defeat every termination check in prob_win_set/_game and
    # cause unbounded recursion instead of a clean failure. Flag, don't guess.
    for field in ('Gm1', 'Gm2', 'Set1', 'Set2'):
        val = row.get(field)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return np.nan

    svr = row['Svr']
    sets_to_win = match_format['sets_to_win']
    super_tb_target = match_format.get('super_tb_target', 7)
    final_tb_code = str(match_format.get('final_tb_code'))

    server_sets, returner_sets = pr.by_server(svr, row['Set1'], row['Set2'])
    server_games, returner_games = pr.by_server(svr, row['Gm1'], row['Gm2'])

    situation = pr.get_game_situation(row['Pts'], svr)

    if situation == 'tiebreak_or_other':
        tb = pr.parse_tiebreak_score(row['Pts'])
        if tb is None:
            return np.nan
        server_tb, returner_tb = pr.by_server(svr, tb[0], tb[1])
        # Tiebreak point index m = server_tb + returner_tb (0-indexed).
        # _tb_server_is_me(m, anchor) needs to know whether "me" served
        # point 0 -- that's derived here from who serves the CURRENT point
        # (Svr), not assumed. Bug history for getting this anchor wrong:
        # docs/atp/03_leverage_clutch/step3_README.md
        m = server_tb + returner_tb
        anchor = _tb_server_is_me(m, True)
        p_win_set_if_win_pt = prob_win_tiebreak(server_tb + 1, returner_tb, p, anchor, target=super_tb_target)
        p_win_set_if_lose_pt = prob_win_tiebreak(server_tb, returner_tb + 1, p, anchor, target=super_tb_target)
    else:
        parsed = pr.parse_game_score(row['Pts'])
        if parsed is None:
            return np.nan
        server_pts, returner_pts = pr.by_server(svr, parsed[0], parsed[1])
        p_hold_win_pt = prob_win_game(server_pts + 1, returner_pts, p)
        p_hold_lose_pt = prob_win_game(server_pts, returner_pts + 1, p)
        # translate "win/lose THIS POINT" into "win/lose THE GAME" win prob,
        # then into "win the SET currently in progress" via prob_win_set,
        # evaluated at the CURRENT game score with the server serving next.
        p_win_set_if_win_pt = _set_prob_given_game_outcome(
            server_games, returner_games, p, final_tb_code, super_tb_target, p_hold_win_pt)
        p_win_set_if_lose_pt = _set_prob_given_game_outcome(
            server_games, returner_games, p, final_tb_code, super_tb_target, p_hold_lose_pt)

    p_match_if_win_pt = prob_win_match(server_sets, returner_sets, p_win_set_if_win_pt, sets_to_win)
    p_match_if_lose_pt = prob_win_match(server_sets, returner_sets, p_win_set_if_lose_pt, sets_to_win)
    return p_match_if_win_pt - p_match_if_lose_pt


def _set_prob_given_game_outcome(server_games, returner_games, p, final_tb_code, super_tb_target, p_win_current_game):
    """Blend: with prob p_win_current_game the server wins the game in
    progress (score becomes server_games+1), else loses it (returner_games+1);
    either way the SET recursion continues from there, with the OTHER player
    serving the next game (service alternates every game, exact rule)."""
    win_path = prob_win_set(server_games + 1, returner_games, p, False, final_tb_code, super_tb_target)
    lose_path = prob_win_set(server_games, returner_games + 1, p, False, final_tb_code, super_tb_target)
    return p_win_current_game * win_path + (1 - p_win_current_game) * lose_path


# =============================================================================
# GENERAL-PURPOSE STATISTICAL UTILITIES
# =============================================================================
# Extracted because these corrections were being recomputed by hand at each
# robustness-check step -- a shared function means the same correction is
# applied the same way every time. Nothing below depends on parsing.py or
# any tennis-specific logic; these are general-purpose.

def bonferroni_correction(p_values, alpha=0.05):
    """
    Simple Bonferroni correction for a family of p-values tested together
    (e.g. the 8 robustness comparisons across p60/p65/p70/tiered x
    serve/return). Conservative by design, appropriate when the family
    consists of related robustness checks on the same underlying
    hypothesis, not independent discoveries.

    Returns a dict: corrected_alpha (the per-test threshold), and for each
    input p-value, whether it clears the corrected threshold.
    """
    p_values = np.asarray(p_values, dtype=float)
    n = len(p_values)
    corrected_alpha = alpha / n
    return {
        'n_comparisons': n,
        'original_alpha': alpha,
        'corrected_alpha': corrected_alpha,
        'significant': (p_values < corrected_alpha).tolist(),
        'p_values': p_values.tolist(),
    }


def benjamini_hochberg(p_values, alpha=0.05):
    """
    Benjamini-Hochberg false discovery rate correction: less conservative
    than Bonferroni, more appropriate when scanning many candidate
    predictors for any real signal (e.g. Step 2's exploratory variable
    sweep: net_play_escalation_delta, wide_serve_escalation_delta,
    return_depth_shift_delta, dropshot_rate). Bonferroni controls the
    chance of any false positive; BH controls the expected proportion of
    false positives among what's flagged significant, which is usually the
    more appropriate frame for an exploratory sweep rather than a
    robustness check on one fixed hypothesis.

    Returns which of the original p-values are significant after BH
    correction, preserving the original order.
    """
    p_values = np.asarray(p_values, dtype=float)
    n = len(p_values)
    order = np.argsort(p_values)
    ranked = p_values[order]
    thresholds = (np.arange(1, n + 1) / n) * alpha
    below = ranked <= thresholds
    if below.any():
        max_rank = np.max(np.where(below)[0])
        cutoff_p = ranked[max_rank]
    else:
        cutoff_p = -1  # nothing survives
    significant = p_values <= cutoff_p
    return {
        'n_comparisons': n,
        'alpha': alpha,
        'cutoff_p': cutoff_p,
        'significant': significant.tolist(),
        'p_values': p_values.tolist(),
    }


def tost_equivalence(x, y, low_bound, high_bound, alpha=0.05):
    """
    Two-one-sided-tests (TOST) equivalence test for a Pearson correlation:
    tests whether the true correlation likely lies within (low_bound,
    high_bound), typically a small band around zero, rather than merely
    failing to reject "r=0". This is a stronger, more precise way to
    report a null than standard NHST: "we can rule out an effect larger
    than X" instead of "we failed to find an effect."

    Returns the correlation, its p-value, and whether equivalence
    (r is significantly within the bounds) was established at the given
    alpha.
    """
    r, p_standard = stats.pearsonr(x, y)
    n = len(x)
    se = 1 / np.sqrt(n - 3)  # Fisher z standard error
    z = np.arctanh(r)
    z_low = np.arctanh(low_bound)
    z_high = np.arctanh(high_bound)

    # TOST: two one-sided tests against each bound
    t_low = (z - z_low) / se
    t_high = (z_high - z) / se
    p_low = 1 - stats.norm.cdf(t_low)
    p_high = 1 - stats.norm.cdf(t_high)
    p_tost = max(p_low, p_high)  # the weaker of the two one-sided tests governs

    return {
        'r': r,
        'p_standard_nhst': p_standard,
        'low_bound': low_bound,
        'high_bound': high_bound,
        'p_tost': p_tost,
        'equivalent_at_alpha': p_tost < alpha,
        'n': n,
    }


def fisher_z_meta_analysis(rs_and_ns, alpha=0.05):
    """
    Fixed-effect meta-analytic pooling of independent Pearson correlations
    (e.g. the same pre-registered ATP and WTA tests) via the Fisher
    z-transform, inverse-variance weighted by (n-3). This is an
    assumption-light complement to a pooled regression with an interaction
    term (see docs/combined/pooled_regression.md): it doesn't require the
    two samples to share a design matrix, just that each r estimates the
    same underlying population correlation.

    rs_and_ns: iterable of (r, n) pairs, one per independent study/tour.

    Returns the pooled r, its 95%-style CI, a z-test p-value against r=0,
    and Cochran's Q (a heterogeneity check -- large Q relative to its
    degrees of freedom suggests the studies aren't estimating the same
    true correlation, which would undercut treating the pooled number as
    meaningful).
    """
    rs_and_ns = list(rs_and_ns)

    z_list = []       # Fisher z-transform of each study's r
    weight_list = []  # inverse-variance weight for each study (n-3)
    total_n = 0
    for r, n in rs_and_ns:
        z_list.append(np.arctanh(r))
        weight_list.append(n - 3)
        total_n += n
    zs = np.array(z_list)
    weights = np.array(weight_list, dtype=float)

    z_pooled = np.sum(weights * zs) / np.sum(weights)
    se_pooled = 1 / np.sqrt(np.sum(weights))
    z_stat = z_pooled / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    z_ci = stats.norm.ppf(1 - alpha / 2) * se_pooled
    r_pooled = np.tanh(z_pooled)
    ci_low = np.tanh(z_pooled - z_ci)
    ci_high = np.tanh(z_pooled + z_ci)

    q = np.sum(weights * (zs - z_pooled) ** 2)
    df = len(rs_and_ns) - 1
    if df > 0:
        q_p_value = 1 - stats.chi2.cdf(q, df)
    else:
        q_p_value = float('nan')

    return {
        'r_pooled': r_pooled,
        'ci_low': ci_low,
        'ci_high': ci_high,
        'p_value': p_value,
        'k_studies': len(rs_and_ns),
        'total_n': int(total_n),
        'cochrans_q': q,
        'q_df': df,
        'q_p_value': q_p_value,
    }


def power_for_correlation(n, r, alpha=0.05):
    """
    Power to detect a true Pearson correlation of magnitude r at sample
    size n, two-sided test at the given alpha, via the Fisher z
    approximation (z = arctanh(r_hat)*sqrt(n-3) is approximately
    N(arctanh(r)*sqrt(n-3), 1) under the true correlation r). Standard
    closed-form approach (matches e.g. R's pwr.r.test), used here instead
    of a simulation since the normal approximation is accurate for n>=10.
    """
    z_alpha2 = stats.norm.ppf(1 - alpha / 2)
    z_stat = np.arctanh(r) * np.sqrt(n - 3)
    return (1 - stats.norm.cdf(z_alpha2 - z_stat)) + stats.norm.cdf(-z_alpha2 - z_stat)


def mdes_correlation(n, alpha=0.05, power=0.80):
    """
    Minimum detectable effect size: the smallest true |r| this sample size
    could detect at the given power and two-sided alpha, via the same
    Fisher z approximation as power_for_correlation(). Answers "what could
    this study actually have found," a more precise complement to a TOST
    equivalence bound (which asks "what can we rule out given what we
    actually observed").
    """
    z_alpha2 = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    z_stat = z_alpha2 + z_power
    return np.tanh(z_stat / np.sqrt(n - 3))
